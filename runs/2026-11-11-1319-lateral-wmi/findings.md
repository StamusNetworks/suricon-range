# findings — 2026-11-11-1319-lateral-wmi

## Run

| Field | Value |
|---|---|
| run_id | `2026-11-11-1319-lateral-wmi` |
| op_slug | `lateral-wmi` |
| start_time | `2026-11-11T13:19:25+00:00` |
| end_time | `2026-11-11T13:21:04+00:00` |
| status | `completed` |
| techniques | `T1021.002, T1047` |
| targets | `suricon-ws1.lab.local, suricon-dc.lab.local` |

---

## Flow index

169 events across 40 flows in window.

| # | First seen | Source | Destination | Port | Proto | Events | Traffic | Alert SIDs | Key metadata |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 13:19:27.317 | 10.137.2.33 | 10.137.2.62 | 135 | dcerpc | 3 | 718 B↑ 562 B↓ | — | DCOM activation e1af8308, opnum 3 |
| 2 | 13:19:27.326 | 10.137.2.33 | 10.137.2.62 | 49682 | dcerpc | 7 | 3.9 KB↑ 1.8 KB↓ | — | iface 12345778… v0.0, opnum 77 ×4 |
| 3 | 13:19:27.961 | 10.137.2.33 | 10.137.2.62 | 135 | dcerpc | 4 | 940 B↑ 680 B↓ | — | DCOM activation e1af8308, opnum 3 ×2 |
| 4 | 13:19:27.975 | 10.137.2.33 | 10.137.2.62 | 49682 | dcerpc | 9 | 4.2 KB↑ 2.2 KB↓ | — | svcctl e3514235: op12 (OpenSCManager) ×3, op0/op1 ×3 each |
| 5 | 13:19:28.068 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 454 B↑ 505 B↓ | — | AS-REQ lab.user → KRB_ERROR |
| 6 | 13:19:28.075 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 1.9 KB↑ 1.9 KB↓ | — | TGS-REQ lab.user → suricon-ws1$ |
| 7 | 13:19:28.468 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 457 B↑ 505 B↓ | — | AS-REQ lab.user → KRB_ERROR |
| 8 | 13:19:28.471 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 457 B↑ 505 B↓ | — | AS-REQ lab.user → KRB_ERROR |
| 9 | 13:19:28.501 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 591 B↑ 1.8 KB↓ | — | AS-REQ lab.user → AS-REP (TGT) |
| 10 | 13:19:28.503 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 1.8 KB↑ 1.8 KB↓ | — | TGS-REQ lab.user → host/suricon-ws1.lab.local |
| 11 | 13:19:29.349 | 10.137.2.33 | 10.137.2.62 | 53 | dns | 4 | 156 B↑ 201 B↓ | — | A wdcp.microsoft.com |
| 12 | 13:20:00.977 | 10.137.2.33 | 10.137.2.62 | 135 | dcerpc | 3 | 718 B↑ 562 B↓ | — | DCOM activation e1af8308, opnum 3 |
| 13 | 13:20:00.985 | 10.137.2.33 | 10.137.2.62 | 49682 | dcerpc | 6 | 3.6 KB↑ 1.5 KB↓ | — | iface 12345778… v0.0, opnum 77 ×3 |
| 14 | 13:20:01.490 | 10.137.2.33 | 10.137.2.62 | 135 | dcerpc | 4 | 940 B↑ 680 B↓ | — | DCOM activation e1af8308, opnum 3 ×2 |
| 15 | 13:20:01.503 | 10.137.2.33 | 10.137.2.62 | 49682 | dcerpc | 9 | 4.2 KB↑ 2.2 KB↓ | — | svcctl e3514235: op12 ×2, op0/op1 ×2 each |
| 16 | 13:20:01.534 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 454 B↑ 505 B↓ | — | AS-REQ lab.user → KRB_ERROR |
| 17 | 13:20:01.820 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 457 B↑ 505 B↓ | — | AS-REQ lab.user → KRB_ERROR |
| 18 | 13:20:01.823 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 457 B↑ 505 B↓ | — | AS-REQ lab.user → KRB_ERROR |
| 19 | 13:20:01.862 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 591 B↑ 1.8 KB↓ | — | AS-REQ lab.user → AS-REP (TGT) |
| 20 | 13:20:01.865 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 1.8 KB↑ 1.8 KB↓ | — | TGS-REQ lab.user → host/suricon-ws1.lab.local |
| 21 | 13:20:21.759 | 10.137.2.33 | 10.137.2.62 | 445 | smb | 24 | — | 2025701, 2025699 | lab.admin; \\suricon-dc.lab.local\C$; CREATE+WRITE Windows\Tasks\DiskOptimizationV2_5537.exe (800768 B, sha256 3373e3ab…) |
| 22 | 13:20:21.767 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 436 B↑ 494 B↓ | — | AS-REQ lab.admin → KRB_ERROR |
| 23 | 13:20:21.798 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 570 B↑ 1.8 KB↓ | — | AS-REQ lab.admin → AS-REP (TGT) |
| 24 | 13:20:21.800 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 1.9 KB↑ 1.9 KB↓ | — | TGS-REQ lab.admin → cifs/suricon-dc.lab.local |
| 25 | 13:20:21.807 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 1.7 KB↑ 1.8 KB↓ | — | TGS-REQ lab.admin → krbtgt/LAB.LOCAL |
| 26 | 13:20:25.172 | 10.137.2.33 | 10.137.2.62 | 53 | dns | 3 | 80 B↑ 96 B↓ | — | A suricon-dc.lab.local |
| 27 | 13:20:25.282 | 10.137.2.33 | 10.137.2.62 | 135 | TCP | 1 | — | — | BIND 99fcfec4 (MSS) |
| 28 | 13:20:25.294 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 436 B↑ 494 B↓ | — | AS-REQ lab.admin → KRB_ERROR |
| 29 | 13:20:25.330 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 570 B↑ 1.8 KB↓ | — | AS-REQ lab.admin → AS-REP (TGT) |
| 30 | 13:20:25.333 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 1.9 KB↑ 2.0 KB↓ | — | TGS-REQ lab.admin → RPCSS/suricon-dc.lab.local |
| 31 | 13:20:25.345 | 10.137.2.33 | 10.137.2.62 | 135 | TCP | 3 | — | — | endpoint mapper 000001a0, opnum 4 |
| 32 | 13:20:25.407 | 10.137.2.33 | 10.137.2.62 | 135 | TCP | 1 | — | — | BIND 99fcfec4 (MSS) |
| 33 | 13:20:25.465 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 436 B↑ 494 B↓ | — | AS-REQ lab.admin → KRB_ERROR |
| 34 | 13:20:25.527 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 570 B↑ 1.8 KB↓ | — | AS-REQ lab.admin → AS-REP (TGT) |
| 35 | 13:20:25.529 | 10.137.2.33 | 10.137.2.62 | 88 | krb5 | 3 | 1.9 KB↑ 2.0 KB↓ | — | TGS-REQ lab.admin → host/suricon-dc.lab.local |
| 36 | 13:20:25.538 | 10.137.2.33 | 10.137.2.62 | 50718 | TCP | 14 | — | — | DCOM→CIMOM: 00000143, IWbemService d4781cd6, IWbemLocator 9f6c78ef, f309ad18, 9556dc99 op6 |
| 37 | 13:20:34.236 | 10.137.2.33 | 10.137.2.62 | 123 | ntp | 1 | 162 B↑ 162 B↓ | — | — |
| 38 | 13:20:39.346 | 10.137.2.62 | 10.137.2.7 | 443 | TCP | 1 | — | — | TLS 1.2, CN=localhost, no SNI; JA3 43016d7f7f93…, JA4 t12i180600_4b22cbed5bed_2dae41c691ec |
| 39 | 13:21:00.037 | 10.137.2.33 | 10.137.2.62 | 53 | dns | 4 | 148 B↑ 352 B↓ | — | A login.live.com |
| 40 | 13:21:01.602 | 10.137.2.33 | 10.137.2.62 | 53 | TCP | 5 | — | — | A watson.events.data.microsoft.com; A settings-win.data.microsoft.com |

---

## Timeline

Relevant flows: 1–10, 12–36 (33 flows). Background: 11, 37–40 (7 flows). All activity originates from 10.137.2.33 against 10.137.2.62, which acts as KDC (88), DNS (53), NTP (123), RPC (135) and SMB (445) server — i.e. the DC in this capture.

### Phase 1 — RPC service control / DCOM activation against 10.137.2.62 (13:19:27–13:20:02)

Flows 1, 2, 3, 4 (wave 1, 13:19:27.3–13:19:28.5) and 12, 13, 14, 15 (wave 2, 13:20:00.9–13:20:02.1), side effects 5–10, 16–20.

Two near-identical waves ~33 s apart. Each wave opens a DCOM activation session on RPC 135 via the IActivation interface (e1af8308, opnum 3 — flows 1, 3, 12, 14) and then talks to dynamic RPC port 49682 with two interfaces: the service control manager (svcctl, e3514235) issuing OpenSCManager (opnum 12) plus opnums 0/1 (flows 4, 15), and an unlabeled interface 12345778-1234-abcd-ef00-0123456789ab v0.0 with repeated opnum 77 requests (flows 2, 13). The repeated OpenSCManager pattern across two waves reads as a tool probing/controlling remote services. No alerts fired on any of these flows — the svcctl and activation steps are anchored solely by NSM, and the opnum 77 interface is opaque (gap).

Kerberos side effect: lab.user obtains a TGT (AS-REP on flows 9, 19 after KRB_ERRORs — the client first used the short realm `LAB` before `LAB.LOCAL`), then requests service tickets for `suricon-ws1$` and `host/suricon-ws1.lab.local` (flows 6, 10, 20) — ws1 principals while the RPC traffic targets .62 (see Notes).

### Phase 2 — SMB staging to C$ as lab.admin (13:20:21–13:20:37)

Flow 21, auth side effects 22–25.

NSM records the full admin-share session on 10.137.2.62:445: lab.admin authenticates via Kerberos (TGT on flow 23, TGS for `cifs/suricon-dc.lab.local` on flow 24), SMB1→SMB2 negotiate, SESSION_SETUP, TREE_CONNECT to `\\suricon-dc.lab.local\C$`, IOCTL capability queries, then CREATE of the `Windows\Tasks` directory and CREATE + WRITE of `Windows\Tasks\DiskOptimizationV2_5537.exe` (800,768 bytes; the `fileinfo` event on the same flow carries sha256 `3373e3ab99bf29b65ee41ffd1a89685ac439638b6839e38e6bc4e49c4cb2e952`). Three further CREATE/CLOSE cycles on the exe at 13:20:25 (open-for-execution/verification pattern), then two TREE_DISCONNECTs at 13:20:32.5 and 13:20:37.9.

Alerts 2025701 (ET INFO SMB2 NT Create AndX Request For an Executable File) ×3 and 2025699 (ET INFO SMB Executable File Transfer) ×2 fired on flow 21 — low-tier labels for what the SMB/fileinfo dissection already records; they corroborate but do not drive the detection. No `flow` record for this session exists in the window, so canonical byte counts/state are unavailable (the alerts' partial snapshots show ~811 KB to-server).

### Phase 3 — Remote WMI/DCOM session on 10.137.2.62 (13:20:25.2–13:20:25.7)

Flows 27, 31, 32, 36; side effects 26, 28–30, 33–35.

Immediately after the file write, .33 resolves `A suricon-dc.lab.local` (flow 26), then: two BINDs to 135 with the MSS interface 99fcfec4 (flows 27, 32), an endpoint-mapper lookup (000001a0, opnum 4) on 135 (flow 31) that yields dynamic port 50718, and a direct DCOM session to .62:50718 (flow 36) using the standard RPC interface 00000143 (opnums 3/5/6) together with the WMI provider interfaces IWbemLocator (9f6c78ef-fce5-42fa-abea-3e7df91921dc, opnum 3), IWbemService (d4781cd6-e5d3-44df-ad94-930efe48a887, opnum 3), f309ad18 (opnums 3/6) and 9556dc99 (opnum 6). This endpoint-mapper-then-dynamic-port interface set is the remote WMI (CIMOM) session-establishment pattern. Kerberos side effect: lab.admin TGTs (flows 29, 34) plus TGS for `RPCSS/suricon-dc.lab.local` (flow 30) and `host/suricon-dc.lab.local` (flow 35) — RPC-over-Kerberos authentication for the RPCSS/DCOM leg. No alerts fired on any of flows 27–36.

### Background

- Row 11 (A `wdcp.microsoft.com`, 13:19:29): client-side lookup during phase 1; no kill-chain tie.
- Row 37 (NTP .33→.62:123, exchange at flow start 13:20:02.8, record emitted 13:20:34.2): routine clock sync to the DC; no step tie.
- Row 38 (TLS .62→.7:443, 13:20:39.3, CN=localhost, no SNI, JA3 `43016d7f7f9336b17c884650d0d2545d`): the only in-scope flow on the .62→.7 pair; 13 s after the WMI phase. Could be target-side post-activity, but CN=localhost points at a local/lab service and no observable tie to the kill chain exists in this window — background, flagged for follow-up in Notes.
- Row 39 (A `login.live.com`, 13:21:00) and row 40 (A `watson.events.data.microsoft.com`, `settings-win.data.microsoft.com`, 13:21:01–13:21:19): Windows account/telemetry lookups; routine.

---

## Verdict

### T1021.002 — Remote Services: SMB/Windows admin shares

- **NSM evidence**: flow 21 — SMB2 session to .62:445 as lab.admin (TGS `cifs/suricon-dc.lab.local`, flow 24): TREE_CONNECT `\\suricon-dc.lab.local\C$`, CREATE of `Windows\Tasks`, CREATE+WRITE of `Windows\Tasks\DiskOptimizationV2_5537.exe`, `fileinfo` with sha256 `3373e3ab…` / 800,768 B, follow-on open/close cycles, TREE_DISCONNECT. Preceding `A suricon-dc.lab.local` lookup (flow 26).
- **Alert enrichment**: 2025701 ×3 and 2025699 ×2 (ET INFO, low tier) on flow 21 label the executable create/transfer; corroborative only.
- **Gaps**: no `flow` record for the SMB session in the window (canonical bytes/state unavailable); no SMB-side execution of the staged file (the phase-1 svcctl activity on .62:49682 stops at OpenSCManager and is not tied to this file).
- **Verdict**: `covered`

### T1047 — WMI

- **NSM evidence**: flow 31 — endpoint-mapper lookup (000001a0, opnum 4) on 135 resolving dynamic port 50718; flow 36 — DCOM session to .62:50718 binding IWbemLocator (9f6c78ef), IWbemService (d4781cd6), f309ad18, 9556dc99 (op6) plus standard RPC 00000143; flows 27/32 — MSS (99fcfec4) binds on 135; auth side effects flows 28–30, 33–35 (lab.admin TGT + TGS for `RPCSS/suricon-dc.lab.local` and `host/suricon-dc.lab.local`).
- **Alert enrichment**: none — no alerts fired on any DCOM/WMI flow; NSM protocol records are the sole anchor.
- **Gaps**: the WMI method invocation (e.g. Win32_Process Create) is opaque — dcerpc dissection yields only UUID/opnum; the repeated opnum 77 on unlabeled interface 12345778 (flows 2, 13) cannot be attributed to WMI or any known interface; no target-side process/file activity observed on .62 after the session to confirm execution.
- **Verdict**: `partial`

---

## Notes

**IoCs**
- `DiskOptimizationV2_5537.exe` staged at `C:\Windows\Tasks\` on 10.137.2.62 — sha256 `3373e3ab99bf29b65ee41ffd1a89685ac439638b6839e38e6bc4e49c4cb2e952`, 800,768 B.
- RPC dynamic ports reused by the tool: 49682 (svcctl + 12345778 interface, both waves) and 50718 (WMI DCOM).
- DCERPC interface `12345778-1234-abcd-ef00-0123456789ab` v0.0, opnum 77 — not a known/standard interface; treat as tool signature.
- TLS .62→.7:443: JA3 `43016d7f7f9336b17c884650d0d2545d`, JA4 `t12i180600_4b22cbed5bed_2dae41c691ec`, CN=localhost.

**Anomalies**
- Principal/IP mismatch: during phase 1 the client requests service tickets for `suricon-ws1$` / `host/suricon-ws1.lab.local` while targeting .62; phases 2–3 use `suricon-dc.lab.local` service principals against the same .62, which also serves KDC/DNS/NTP. If .62 = suricon-dc, the ws1 tickets are out of scope for the target and warrant verification; if .62 = suricon-ws1, the SMB share name is mislabeled. Either way, scope-check which host .62/.7 actually are before acting.
- `KRB_ERROR` on short-realm AS-REQs (`krbtgt/LAB`) preceding success on `LAB.LOCAL` — scripted client with a hardcoded short realm.
- Dataset extends to 13:21:32, past the recorded end_time (13:21:04); post-cutoff events are flow terminations and routine DNS only — no verdict impact.

**Recommendations**
- Highlight rule: RPCSS/DCOM activation involving `9f6c78ef-fce5-42fa-abea-3e7df91921dc` (IWbemLocator) or `d4781cd6-e5d3-44df-ad94-930efe48a887` (IWbemService) from a remote host — would have labeled the T1047 session-establishment step (flows 31/36) that currently has zero alert coverage.
- Label or investigate the `12345778` interface / opnum 77 to close the phase-1 gap.
- Alert on svcctl CreateService/StartService opnums (26/31) to non-local hosts; observed traffic stops at OpenSCManager (op12), so no service creation was visible over SCM in this window.
- Follow up flow 38: pull target-side process/audit data on .62 around 13:20:39 to determine whether the WMI payload produced the outbound TLS to .7.
- Re-query for `flow` records of 1561827336736660 (SMB), 404021396347639 (WMI DCOM), 400572950246494 (endpoint mapper), 2160156539477089 (TLS) once the capture closes, to confirm byte totals and session state.