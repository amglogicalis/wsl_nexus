import sys
import os
import json
import subprocess
import threading
import uuid
import urllib.request
import webview
from winpty import PTY, Backend

# ── Subprocess helpers: suppress all console-window flashes ──────────────────
def _make_si():
    """Returns a STARTUPINFO that hides any spawned console window."""
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    return si

_NO_WIN = subprocess.CREATE_NO_WINDOW


def get_app_version():
    """Lee la versión actual desde el archivo VERSION (junto al exe o al .py)."""
    for base in [
        os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None,
        os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd(),
    ]:
        if base is None:
            continue
        vpath = os.path.join(base, 'VERSION')
        if os.path.exists(vpath):
            try:
                return open(vpath).read().strip()
            except Exception:
                pass
    return '1.0.0'


APP_VERSION = get_app_version()
GITHUB_REPO = 'amglogicalis/wsl_nexus'

def find_wsl_path():
    paths = [
        r"C:\Windows\System32\wsl.exe",
        os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32\\wsl.exe"),
        "wsl.exe"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "wsl.exe"

# Fallback installation info per distro.
# wsl_url  = modern .wsl tarball  → installed via "wsl --import" (fastest, no Store needed)
# appx_url = legacy .appx/.AppxBundle → installed via Add-AppxPackage (second choice)
# pkg_name = Get-AppxPackage -Name pattern (for appx path detection)
# exe_hint = prefix of the launcher .exe inside the appx package
# winget_id = winget package id (tried first)
DISTRO_FALLBACK_INFO = {
    "ubuntu": {
        "wsl_url":  "https://releases.ubuntu.com/24.04.4/ubuntu-24.04.4-wsl-amd64.wsl",
        "appx_url": "https://publicwsldistros.blob.core.windows.net/wsldistrostorage/Ubuntu2204-220117.appx",
        "pkg_name": "CanonicalGroupLimited.Ubuntu*",
        "exe_hint": "ubuntu",
        "winget_id": "Canonical.Ubuntu"
    },
    "ubuntu-24.04": {
        "wsl_url":  "https://releases.ubuntu.com/24.04.4/ubuntu-24.04.4-wsl-amd64.wsl",
        "appx_url": "https://publicwsldistros.blob.core.windows.net/wsldistrostorage/Ubuntu2204-220117.appx",
        "pkg_name": "CanonicalGroupLimited.Ubuntu24.04LTS*",
        "exe_hint": "ubuntu2404",
        "winget_id": "Canonical.Ubuntu.2404"
    },
    "ubuntu-22.04": {
        "wsl_url":  "https://releases.ubuntu.com/jammy/ubuntu-22.04.5-wsl-amd64.wsl",
        "appx_url": "https://publicwsldistros.blob.core.windows.net/wsldistrostorage/Ubuntu2204-220117.appx",
        "pkg_name": "CanonicalGroupLimited.Ubuntu22.04LTS*",
        "exe_hint": "ubuntu2204",
        "winget_id": "Canonical.Ubuntu.2204"
    },
    "ubuntu-20.04": {
        "wsl_url":  "https://releases.ubuntu.com/focal/ubuntu-20.04.6-wsl-amd64.wsl",
        "appx_url": "https://publicwsldistros.blob.core.windows.net/wsldistrostorage/Ubuntu2204-220117.appx",
        "pkg_name": "CanonicalGroupLimited.Ubuntu20.04LTS*",
        "exe_hint": "ubuntu2004",
        "winget_id": "Canonical.Ubuntu.2004"
    },
    "ubuntu-18.04": {
        "wsl_url":  "https://releases.ubuntu.com/focal/ubuntu-20.04.6-wsl-amd64.wsl",
        "appx_url": "https://publicwsldistros.blob.core.windows.net/wsldistrostorage/Ubuntu2204-220117.appx",
        "pkg_name": "CanonicalGroupLimited.Ubuntu18.04onWindows*",
        "exe_hint": "ubuntu1804",
        "winget_id": "Canonical.Ubuntu.1804"
    },
    "debian": {
        "wsl_url":  None,
        "appx_url": "https://publicwsldistros.blob.core.windows.net/wsldistrostorage/TheDebianProject.DebianGNULinux_1.12.2.0_neutral___76v4gfsz19hv4.AppxBundle",
        "pkg_name": "TheDebianProject.DebianGNULinux*",
        "exe_hint": "debian",
        "winget_id": "TheDebianProject.DebianGNULinux"
    },
    "kali-linux": {
        "wsl_url":  None,
        "appx_url": "https://publicwsldistros.blob.core.windows.net/wsldistrostorage/KaliLinux_1.13.1.0.AppxBundle",
        "pkg_name": "KaliLinux.54290C8133FEE*",
        "exe_hint": "kali",
        "winget_id": "KaliLinux.KaliLinux"
    },
    "opensuse-tumbleweed": {
        "wsl_url":  None,
        "appx_url": "https://github.com/openSUSE/WSL-instarball/releases/download/v20260423.0/openSUSE-Tumbleweed-20260422-WSL.x86_64-26112.10.203.0-Build10.203.appx",
        "pkg_name": "46932SUSE.openSUSETumbleweed*",
        "exe_hint": "openSUSE",
        "winget_id": "openSUSE.openSUSETumbleweed"
    },
    "opensuse-leap-15.5": {
        "wsl_url":  None,
        "appx_url": "https://github.com/openSUSE/WSL-instarball/releases/download/v20260423.0/openSUSE-Tumbleweed-20260422-WSL.x86_64-26112.10.203.0-Build10.203.appx",
        "pkg_name": "46932SUSE.openSUSELeap*",
        "exe_hint": "openSUSE",
        "winget_id": "openSUSE.openSUSELeap15.5"
    },
    "sles-15": {
        "wsl_url":  None,
        "appx_url": "https://github.com/SUSE/WSL-instarball/releases/download/v20250618.0/SUSE-Linux-Enterprise-15-SP6-15.6-WSL.x86_64-156.3.148.0-Build3.148.appx",
        "pkg_name": "46932SUSE.SUSELinuxEnterprise*",
        "exe_hint": "SLES",
        "winget_id": "SUSE.SUSELinuxEnterpriseServer15SP6"
    },
    "suse-linux-enterprise-15-sp6": {
        "wsl_url":  None,
        "appx_url": "https://github.com/SUSE/WSL-instarball/releases/download/v20250618.0/SUSE-Linux-Enterprise-15-SP6-15.6-WSL.x86_64-156.3.148.0-Build3.148.appx",
        "pkg_name": "46932SUSE.SUSELinuxEnterprise*",
        "exe_hint": "SLES",
        "winget_id": "SUSE.SUSELinuxEnterpriseServer15SP6"
    },
    "fedoralinux-44": {
        "wsl_url":  "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Container/x86_64/images/Fedora-WSL-Base-44-1.7.x86_64.wsl",
        "appx_url": None,
        "pkg_name": "*Fedora*",
        "exe_hint": "fedora",
        "winget_id": "FedoraProject.Fedora"
    }
}

def get_fallback_info(distro_name):
    name_lower = distro_name.lower()
    if name_lower in DISTRO_FALLBACK_INFO:
        return DISTRO_FALLBACK_INFO[name_lower]
    for key, val in DISTRO_FALLBACK_INFO.items():
        if key in name_lower:
            return val
    if "debian" in name_lower:
        return DISTRO_FALLBACK_INFO["debian"]
    if "kali" in name_lower:
        return DISTRO_FALLBACK_INFO["kali-linux"]
    if "suse" in name_lower or "sles" in name_lower:
        return DISTRO_FALLBACK_INFO["sles-15"]
    return DISTRO_FALLBACK_INFO["ubuntu"]

class Api:
    def __init__(self):
        self._window = None
        self._sessions = {}  # session_id -> pty
        self._wsl_path = find_wsl_path()

    def get_system_info(self):
        wsl_ver = "Unknown"
        try:
            out = subprocess.check_output(
                [self._wsl_path, '--version'],
                startupinfo=_make_si(), creationflags=_NO_WIN
            )
            try:
                text = out.decode('utf-16')
            except Exception:
                text = out.decode('utf-8', errors='replace')
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if 'wsl' in line.lower() and ':' in line:
                    wsl_ver = line.split(':', 1)[1].strip()
                    break
        except Exception:
            pass

        return {
            "python_version": sys.version.split()[0],
            "wsl_version": wsl_ver
        }

    def get_wsl_distros(self):
        installed = []
        try:
            out = subprocess.check_output(
                [self._wsl_path, '--list', '--verbose'],
                startupinfo=_make_si(), creationflags=_NO_WIN
            )
            try:
                text = out.decode('utf-16')
            except Exception:
                text = out.decode('utf-8', errors='replace')
            
            lines = text.strip().split('\n')
            if lines and 'name' in lines[0].lower():
                import re
                for line in lines[1:]:
                    line = line.strip()
                    if not line:
                        continue
                    is_default = line.startswith('*')
                    if is_default:
                        line = line[1:].strip()
                    parts = re.split(r'\s{2,}', line)
                    if len(parts) >= 2:
                        name = parts[0]
                        state = parts[1]
                        version = parts[2] if len(parts) > 2 else "2"
                        installed.append({
                            'name': name,
                            'friendly_name': name,
                            'state': state,
                            'version': version,
                            'is_default': is_default,
                            'installed': True
                        })
        except subprocess.CalledProcessError:
            pass
        except Exception:
            pass

        online = []
        try:
            out = subprocess.check_output(
                [self._wsl_path, '--list', '--online'],
                startupinfo=_make_si(), creationflags=_NO_WIN
            )
            try:
                text = out.decode('utf-16')
            except Exception:
                text = out.decode('utf-8', errors='replace')
            
            lines = text.strip().split('\n')
            header_idx = -1
            for idx, line in enumerate(lines):
                if 'name' in line.lower() and 'friendly' in line.lower():
                    header_idx = idx
                    break
            
            if header_idx != -1:
                import re
                for line in lines[header_idx + 1:]:
                    line = line.strip()
                    if not line:
                        continue
                    parts = re.split(r'\s{2,}', line)
                    if len(parts) >= 1:
                        name = parts[0]
                        friendly = parts[1] if len(parts) > 1 else name
                        online.append({
                            'name': name,
                            'friendly_name': friendly,
                            'installed': False,
                            'state': 'Stopped',
                            'version': '',
                            'is_default': False
                        })
        except Exception:
            pass

        installed_names = {d['name'].lower() for d in installed}
        merged = list(installed)
        for dist in online:
            if dist['name'].lower() not in installed_names:
                merged.append(dist)
                
        return merged

    def start_distro_silent(self, distro_name):
        try:
            subprocess.run(
                [self._wsl_path, '-d', distro_name, '--', 'true'],
                startupinfo=_make_si(), creationflags=_NO_WIN,
                check=True
            )
            return True
        except Exception:
            return False

    def stop_distro(self, distro_name):
        try:
            subprocess.run(
                [self._wsl_path, '--terminate', distro_name],
                startupinfo=_make_si(), creationflags=_NO_WIN,
                check=True
            )
            return True
        except Exception:
            return False

    def create_terminal_session(self, distro_name, cols, rows, backend_type='conpty'):
        """Spawn an embedded PTY terminal for distro_name.
        backend_type: 'conpty' (default – same engine as Windows Terminal)
                      'winpty' (legacy fallback)
        """
        session_id = str(uuid.uuid4())
        try:
            backend = Backend.ConPTY if backend_type != 'winpty' else Backend.WinPTY
            pty = PTY(cols, rows, backend=backend)
            success = pty.spawn(self._wsl_path, cmdline=f"wsl.exe -d {distro_name}")
            if not success:
                return {"success": False, "message": "winpty failed to spawn wsl process"}
            
            self._sessions[session_id] = pty
            
            def read_loop():
                while True:
                    try:
                        if not pty.isalive():
                            break
                        data = pty.read(blocking=True)
                        if not data:
                            break
                        if self._window:
                            self._window.evaluate_js(f"window.onTerminalData('{session_id}', {json.dumps(data)});")
                    except Exception:
                        break
                
                try:
                    pty.close()
                except Exception:
                    pass
                if session_id in self._sessions:
                    del self._sessions[session_id]
                
                if self._window:
                    self._window.evaluate_js(f"window.onTerminalExit('{session_id}');")

            t = threading.Thread(target=read_loop, daemon=True)
            t.start()
            
            return {"success": True, "session_id": session_id}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def is_windows_terminal_available(self):
        """Check if Windows Terminal (wt.exe) is installed on this machine."""
        localappdata = os.environ.get("LOCALAPPDATA", "")
        local_wt = os.path.join(localappdata, "Microsoft", "WindowsApps", "wt.exe")
        if os.path.exists(local_wt):
            return True
        try:
            subprocess.run(
                ["where", "wt.exe"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                startupinfo=_make_si(), creationflags=_NO_WIN,
                check=True
            )
            return True
        except Exception:
            return False

    # NOTE: We no longer open an external wt.exe window.
    # Both 'ConPTY' and 'WinPTY' modes are embedded inside the app via xterm.js.
    # This stub is kept for API compat so old JS callers don't crash.
    def launch_external_terminal(self, distro_name):
        return False

    def write_terminal_data(self, session_id, data):
        pty = self._sessions.get(session_id)
        if pty:
            try:
                pty.write(data)
                return True
            except Exception:
                pass
        return False

    def resize_terminal(self, session_id, cols, rows):
        pty = self._sessions.get(session_id)
        if pty:
            try:
                pty.set_size(cols, rows)
                return True
            except Exception:
                pass
        return False

    def close_terminal_session(self, session_id):
        pty = self._sessions.get(session_id)
        if pty:
            try:
                pty.close(force=True)
            except Exception:
                pass
            if session_id in self._sessions:
                del self._sessions[session_id]
            return True
        return False

    def install_distro(self, distro_name):
        # IMPORTANT: Do NOT use WinPTY/PTY here.
        # WinPTY spawns child processes on a non-interactive window station.
        # The WSL installer (LxssManager / WSLService) internally makes COM/DCOM
        # calls that require the process to run in the proper interactive user session.
        # Using subprocess.Popen with PIPE keeps the correct session token while still letting
        # us read and stream output to the UI.
        # We also attempt to use '--web-download' first, as this downloads directly from Microsoft
        # instead of the Windows Store, avoiding the E_ACCESSDENIED error in restricted environments.
        session_id = f"install_{distro_name}"
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            def run_installation():
                cmd = [self._wsl_path, '--install', '-d', distro_name, '--web-download', '--no-launch']
                invalid_option_detected = False
                exit_code = -1
                standard_failed = False
                error_msg = ""
                
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        encoding='utf-8',
                        errors='replace',
                    )
                    self._sessions[session_id] = proc
                    
                    try:
                        for line in proc.stdout:
                            if self._window:
                                self._window.evaluate_js(
                                    f"window.onInstallData('{distro_name}', {json.dumps(line)});"
                                )
                            lower_line = line.lower()
                            if any(term in lower_line for term in ["invalid option", "unrecognized option", "unknown option", "opción no válida", "parámetro no válido", "invalid command line option", "error: 0x"]):
                                if any(opt in lower_line for opt in ["--web-download", "option", "parameter", "argument", "opción", "parámetro"]):
                                    invalid_option_detected = True
                    except Exception as e:
                        pass
                    finally:
                        try:
                            proc.stdout.close()
                        except Exception:
                            pass
                    
                    exit_code = proc.wait()
                    if exit_code != 0:
                        standard_failed = True
                        error_msg = f"Standard installation failed with exit code: {exit_code}"
                except Exception as e:
                    standard_failed = True
                    error_msg = str(e)
                    if self._window:
                        self._window.evaluate_js(
                            f"window.onInstallData('{distro_name}', '[Nexus] Standard installation could not start: {json.dumps(str(e))}\\n');"
                        )

                # If standard install failed due to invalid option, try without --web-download
                if standard_failed and invalid_option_detected:
                    if self._window:
                        self._window.evaluate_js(
                            f"window.onInstallData('{distro_name}', '\\n[Nexus] --web-download option not supported by this WSL version. Retrying without it...\\n\\n');"
                        )
                    
                    cmd_fallback = [self._wsl_path, '--install', '-d', distro_name, '--no-launch']
                    try:
                        proc = subprocess.Popen(
                            cmd_fallback,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL,
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            encoding='utf-8',
                            errors='replace',
                        )
                        self._sessions[session_id] = proc
                        
                        try:
                            for line in proc.stdout:
                                if self._window:
                                    self._window.evaluate_js(
                                        f"window.onInstallData('{distro_name}', {json.dumps(line)});"
                                    )
                        except Exception:
                            pass
                        finally:
                            try:
                                proc.stdout.close()
                            except Exception:
                                pass
                        
                        exit_code = proc.wait()
                        if exit_code == 0:
                            standard_failed = False
                        else:
                            error_msg = f"Retry standard installation failed with exit code: {exit_code}"
                    except Exception as e:
                        error_msg = str(e)

                # If standard installation failed (after retry or immediately), run the PowerShell fallback
                if standard_failed:
                    if self._window:
                        self._window.evaluate_js(
                            f"window.onInstallData('{distro_name}', '\\n[Nexus] Instalación estándar fallida. Iniciando instalación de fallback vía PowerShell (Start-BitsTransfer & Add-AppxPackage)...\\n\\n');"
                        )
                    fallback_success, reg_name = self._run_powershell_fallback_install(distro_name, session_id)
                    if fallback_success:
                        success_status = True
                        installed_name = reg_name
                        msg = "Finished successfully (via fallback)"
                    else:
                        success_status = False
                        installed_name = distro_name
                        msg = f"Standard installation and PowerShell fallback both failed. Reason: {error_msg}"
                else:
                    success_status = True
                    installed_name = distro_name
                    msg = "Finished successfully"

                if session_id in self._sessions:
                    del self._sessions[session_id]

                if self._window:
                    self._window.evaluate_js(
                        f"window.onInstallComplete('{installed_name}', {json.dumps(success_status)}, {json.dumps(msg)});"
                    )

            threading.Thread(target=run_installation, daemon=True).start()
            return {"started": True, "session_id": session_id}
        except Exception as e:
            return {"started": False, "message": str(e)}

    def _run_powershell_fallback_install(self, distro_name, session_id):
        """
        3-tier PowerShell fallback WSL distro installation.

        Tier A (preferred, modern): Download .wsl tarball → wsl --import
            Uses direct official URLs (Ubuntu releases.ubuntu.com, etc.)
            No Store required, works without AppxPackage permissions.

        Tier B (legacy appx): Download .appx/.AppxBundle → Add-AppxPackage
            Then locate & run the launcher exe with 'install --root'.

        All download attempts use Start-BitsTransfer first, then
        Invoke-WebRequest as a secondary download method.
        No interactive console window is opened.
        """
        info = get_fallback_info(distro_name)
        wsl_url   = info.get("wsl_url")   or ""
        appx_url  = info.get("appx_url")  or ""
        pkg_name  = info["pkg_name"]
        exe_hint  = info["exe_hint"]
        winget_id = info["winget_id"]

        # Build a PowerShell here-string with the 3-tier logic
        ps_script = f"""
$ErrorActionPreference = 'Continue'
$distroName = '{distro_name}'
$wingetId   = '{winget_id}'
$wslUrl     = '{wsl_url}'
$appxUrl    = '{appx_url}'
$pkgName    = '{pkg_name}'
$exeHint    = '{exe_hint}'
$wslExe     = 'C:\\Windows\\System32\\wsl.exe'

New-Item -ItemType Directory -Force -Path 'C:\\WSL' | Out-Null

function Download-File($url, $dest) {{
    if (Test-Path $dest) {{ Remove-Item $dest -Force -ErrorAction SilentlyContinue }}
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

    Write-Host "[Nexus] Descargando: $url"
    Write-Host '[Nexus] Método 1: Start-BitsTransfer...'
    try {{
        Start-BitsTransfer -Source $url -Destination $dest -ErrorAction Stop
        Write-Host '[Nexus] Descarga completada con BitsTransfer.'
        return $true
    }} catch {{
        Write-Host "[Nexus] BitsTransfer falló: $($_.Exception.Message)"
    }}

    Write-Host '[Nexus] Método 2: Invoke-WebRequest...'
    try {{
        $oldPref = $ProgressPreference
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -ErrorAction Stop
        $ProgressPreference = $oldPref
        Write-Host '[Nexus] Descarga completada con Invoke-WebRequest.'
        return $true
    }} catch {{
        Write-Host "[Nexus] Invoke-WebRequest falló: $($_.Exception.Message)"
    }}
    return $false
}}

$registered = $false

# ══════════════════════════════════════════════════════════
# TIER 1 (Modern): .wsl tarball → wsl --import
# Works without Store/AppxPackage permissions
# ══════════════════════════════════════════════════════════
if ($wslUrl -and $wslUrl -ne '') {{
    Write-Host ''
    Write-Host '[Nexus] ═══ MÉTODO 1: wsl --import con archivo .wsl (moderno) ═══'
    $wslDest = "C:\\WSL\\$distroName.wsl"
    $wslInstallDir = "C:\\WSL\\$distroName"
    New-Item -ItemType Directory -Force -Path $wslInstallDir | Out-Null

    $dlOk = Download-File $wslUrl $wslDest
    if ($dlOk -and (Test-Path $wslDest)) {{
        Write-Host "[Nexus] Importando distribución con 'wsl --import'..."
        try {{
            $importOut = & $wslExe --import $distroName $wslInstallDir $wslDest --version 2 2>&1
            Write-Host $importOut
            Start-Sleep -Seconds 3

            $list = (& $wslExe --list --quiet) | ForEach-Object {{ $_.Replace("`0","").Trim() }} | Where-Object {{ $_ }}
            if ($list -like "*$distroName*") {{
                $registered = $true
                Write-Host "[Nexus] Distribución '$distroName' registrada con éxito (método .wsl)."
            }} else {{
                Write-Host '[Nexus] wsl --import completó pero la distribución no aparece en la lista. Continuando con método 2...'
            }}
        }} catch {{
            Write-Host "[Nexus] wsl --import falló: $($_.Exception.Message)"
        }}
        Remove-Item $wslDest -Force -ErrorAction SilentlyContinue
    }} else {{
        Write-Host '[Nexus] No se pudo descargar el archivo .wsl. Continuando con método 2...'
    }}
}}

# ══════════════════════════════════════════════════════════
# TIER 2 (Winget): intento silencioso con winget
# ══════════════════════════════════════════════════════════
if (-not $registered) {{
    Write-Host ''
    Write-Host '[Nexus] ═══ MÉTODO 2: winget ═══'
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    $wingetExe = if ($wingetCmd) {{ $wingetCmd.Source }} else {{ $null }}
    if ($wingetExe) {{
        $wg = Start-Process -FilePath $wingetExe `
            -ArgumentList "install --id $wingetId --source winget --accept-source-agreements --accept-package-agreements --silent --disable-interactivity" `
            -Wait -PassThru -NoNewWindow
        if ($wg.ExitCode -eq 0) {{
            Write-Host '[Nexus] winget instaló el paquete correctamente.'
            Start-Sleep -Seconds 3
            $list = (& $wslExe --list --quiet) | ForEach-Object {{ $_.Replace("`0","").Trim() }} | Where-Object {{ $_ }}
            if ($list -like "*$distroName*") {{ $registered = $true }}
        }} else {{
            Write-Host "[Nexus] winget falló (código $($wg.ExitCode)). Continuando con método 3..."
        }}
    }} else {{
        Write-Host '[Nexus] winget no está disponible. Continuando con método 3...'
    }}
}}

# ══════════════════════════════════════════════════════════
# TIER 3 (AppxPackage): .appx/.AppxBundle → Add-AppxPackage
# Then run the launcher exe to register the WSL distro
# ══════════════════════════════════════════════════════════
if (-not $registered -and $appxUrl -and $appxUrl -ne '') {{
    Write-Host ''
    Write-Host '[Nexus] ═══ MÉTODO 3: AppxPackage (.appx) ═══'
    $appxDest = "C:\\WSL\\$distroName.appx"

    $pkg = Get-AppxPackage -Name $pkgName -ErrorAction SilentlyContinue
    if (-not $pkg) {{
        $dlOk = Download-File $appxUrl $appxDest
        if ($dlOk) {{
            try {{
                Write-Host '[Nexus] Instalando paquete Appx...'
                Add-AppxPackage -Path $appxDest -ErrorAction Stop
                Write-Host '[Nexus] Paquete Appx instalado.'
                Start-Sleep -Seconds 3
            }} catch {{
                Write-Host "[Nexus] ERROR al instalar Appx: $_"
            }}
            Remove-Item $appxDest -Force -ErrorAction SilentlyContinue
        }} else {{
            Write-Host '[Nexus] ERROR: No se pudo descargar el paquete Appx.'
        }}
    }} else {{
        Write-Host "[Nexus] Paquete Appx ya instalado en: $($pkg.InstallLocation)"
    }}

    # Locate launcher exe and register the WSL distro
    $pkg = Get-AppxPackage -Name $pkgName -ErrorAction SilentlyContinue
    if ($pkg) {{
        $installLoc = $pkg.InstallLocation
        Write-Host "[Nexus] Paquete encontrado en: $installLoc"
        $exes = Get-ChildItem -Path $installLoc -Filter '*.exe' -ErrorAction SilentlyContinue
        $exe  = ($exes | Where-Object {{ $_.Name -like "$exeHint*.exe" }} | Select-Object -First 1)
        if (-not $exe) {{ $exe = $exes | Select-Object -First 1 }}

        if ($exe) {{
            Write-Host "[Nexus] Ejecutable encontrado: $($exe.Name)"
            Write-Host '[Nexus] Registrando distribución en WSL (install --root)...'
            $logFile = "C:\\WSL\\log-$distroName-out.txt"
            $logFileErr = "C:\\WSL\\log-$distroName-err.txt"
            foreach ($f in @($logFile, $logFileErr)) {{
                if (Test-Path $f) {{ Remove-Item $f -Force -ErrorAction SilentlyContinue }}
            }}

            $reg = Start-Process -FilePath $exe.FullName -ArgumentList 'install --root' -PassThru -NoNewWindow `
                -RedirectStandardOutput $logFile -RedirectStandardError $logFileErr
            $timeout = 90; $interval = 2; $lastPosOut = 0; $lastPosErr = 0
            for ($i = 0; $i -lt $timeout; $i += $interval) {{
                Start-Sleep -Seconds $interval
                foreach ($entry in @(@{{f=$logFile;p=[ref]$lastPosOut}}, @{{f=$logFileErr;p=[ref]$lastPosErr}})) {{
                    if (Test-Path $entry.f) {{
                        try {{
                            $c = Get-Content $entry.f -Raw -ErrorAction SilentlyContinue
                            if ($c -and $c.Length -gt $entry.p.Value) {{
                                Write-Host $c.Substring($entry.p.Value) -NoNewline
                                $entry.p.Value = $c.Length
                            }}
                        }} catch {{}}
                    }}
                }}
                $list = (& $wslExe --list --quiet) | ForEach-Object {{ $_.Replace("`0","").Trim() }} | Where-Object {{ $_ }}
                if ($list -like "*$distroName*") {{
                    $registered = $true
                    Write-Host "`n[Nexus] Distribución registrada (Appx launcher)."
                    break
                }}
                if ($reg -and $reg.HasExited -and $reg.ExitCode -ne 0) {{ break }}
            }}
            if ($reg -and -not $reg.HasExited) {{ Stop-Process -Id $reg.Id -Force -ErrorAction SilentlyContinue }}
            foreach ($f in @($logFile, $logFileErr)) {{
                if (Test-Path $f) {{ Remove-Item $f -Force -ErrorAction SilentlyContinue }}
            }}
        }} else {{
            Write-Host '[Nexus] ERROR: No se encontró el ejecutable de la distribución en el paquete Appx.'
        }}
    }} else {{
        Write-Host '[Nexus] ERROR: Paquete Appx no encontrado tras la instalación.'
    }}
}}

# ── Resultado final ──────────────────────────────────────
if ($registered) {{
    $wslList = (& $wslExe --list --quiet) | ForEach-Object {{ $_.Replace("`0","").Trim() }} | Where-Object {{ $_ }}
    $actualName = $wslList | Where-Object {{ $_.ToLower() -eq $distroName.ToLower() -or $_ -like "*$distroName*" }} | Select-Object -First 1
    if (-not $actualName) {{ $actualName = $distroName }}
    Write-Host "[Nexus] Deteniendo '$actualName'..."
    & $wslExe --terminate $actualName 2>$null
    Write-Host "[Nexus] RegisteredName: $actualName"
    Write-Host '[Nexus] Instalación de fallback completada con éxito.'
    exit 0
}} else {{
    Write-Host '[Nexus] ERROR: Todos los métodos de instalación fallaron.'
    exit 1
}}
"""

        try:
            proc = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                startupinfo=_make_si(),
                creationflags=_NO_WIN,
                encoding='utf-8',
                errors='replace',
            )
            self._sessions[session_id] = proc

            actual_registered_name = distro_name
            for line in proc.stdout:
                if self._window:
                    self._window.evaluate_js(
                        f"window.onInstallData('{distro_name}', {json.dumps(line)});"
                    )
                if "[Nexus] RegisteredName:" in line:
                    parts = line.split("[Nexus] RegisteredName:")
                    if len(parts) > 1:
                        actual_registered_name = parts[1].strip()

            exit_code = proc.wait()
            return exit_code == 0, actual_registered_name
        except Exception as e:
            if self._window:
                self._window.evaluate_js(
                    f"window.onInstallData('{distro_name}', '[Nexus] ERROR al iniciar PowerShell: {json.dumps(str(e))}\\n');"
                )
            return False, distro_name

    def unregister_distro(self, distro_name):
        try:
            subprocess.run(
                [self._wsl_path, '--unregister', distro_name],
                startupinfo=_make_si(), creationflags=_NO_WIN,
                check=True
            )
            return True
        except Exception:
            return False

    def import_custom_distro(self, name, install_dir, tar_path):
        session_id = f"import_{name}"
        try:
            if not os.path.exists(tar_path):
                return {"started": False, "message": "Tarball file does not exist."}
            
            try:
                os.makedirs(install_dir, exist_ok=True)
            except Exception as e:
                return {"started": False, "message": f"Failed to create directory: {str(e)}"}
            
            pty = PTY(80, 24, backend=Backend.WinPTY)
            cmd = f"wsl.exe --import {name} \"{install_dir}\" \"{tar_path}\""
            success = pty.spawn(self._wsl_path, cmdline=cmd)
            
            if not success:
                return {"started": False, "message": "Failed to spawn wsl.exe --import process"}
            
            self._sessions[session_id] = pty
            
            def import_read_loop():
                while True:
                    try:
                        if not pty.isalive():
                            break
                        data = pty.read(blocking=True)
                        if not data:
                            break
                        if self._window:
                            self._window.evaluate_js(f"window.onInstallData('{name}', {json.dumps(data)});")
                    except Exception:
                        break
                
                exit_code = 1
                try:
                    exit_code = pty.get_exitstatus()
                    pty.close()
                except Exception:
                    pass
                    
                if session_id in self._sessions:
                    del self._sessions[session_id]
                
                success_status = (exit_code == 0)
                msg = f"Exit code: {exit_code}" if not success_status else "Finished successfully"
                if self._window:
                    self._window.evaluate_js(f"window.onInstallComplete('{name}', {json.dumps(success_status)}, {json.dumps(msg)});")
                    
            threading.Thread(target=import_read_loop, daemon=True).start()
            return {"started": True, "session_id": session_id}
        except Exception as e:
            return {"started": False, "message": str(e)}

    def select_tarball_dialog(self):
        if not self._window:
            return ""
        file_types = ('Tarball files (*.tar;*.tar.gz;*.tgz)', 'All files (*.*)')
        res = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=file_types
        )
        if res and len(res) > 0:
            return res[0]
        return ""

    def select_folder_dialog(self):
        if not self._window:
            return ""
        res = self._window.create_file_dialog(
            webview.FOLDER_DIALOG
        )
        if res and len(res) > 0:
            return res[0]
        return ""

    def download_and_import_preset(self, preset_name):
        session_id = f"preset_{preset_name}"
        if preset_name.lower() != 'alpine':
            return {"started": False, "message": "Unsupported preset"}
            
        url = "https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/x86_64/alpine-minirootfs-3.20.0-x86_64.tar.gz"
        name = "Alpine"
        install_dir = r"C:\WSL\Alpine"
        tar_path = r"C:\WSL\alpine-temp.tar.gz"
        
        try:
            import urllib.request
            
            def download_with_progress(url, dest_path, progress_callback):
                def report(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = min(100, int(block_num * block_size * 100 / total_size))
                        progress_callback(f"Downloading: {percent}%\n")
                urllib.request.urlretrieve(url, dest_path, reporthook=report)
                
            def task_thread():
                try:
                    os.makedirs(r"C:\WSL", exist_ok=True)
                    if self._window:
                        self._window.evaluate_js(f"window.onInstallData('{name}', 'Starting download of Alpine Linux rootfs (5MB)...\n');")
                    
                    def progress_cb(msg):
                        if self._window:
                            self._window.evaluate_js(f"window.onInstallData('{name}', {json.dumps(msg)});")
                            
                    download_with_progress(url, tar_path, progress_cb)
                    
                    if self._window:
                        self._window.evaluate_js(f"window.onInstallData('{name}', '\nDownload complete! Starting import into WSL...\n');")
                    
                    pty = PTY(80, 24, backend=Backend.WinPTY)
                    cmd = f"wsl.exe --import {name} \"{install_dir}\" \"{tar_path}\""
                    success = pty.spawn(self._wsl_path, cmdline=cmd)
                    
                    if not success:
                        if self._window:
                            self._window.evaluate_js(f"window.onInstallComplete('{name}', false, 'Failed to spawn import process.');")
                        return
                    
                    self._sessions[session_id] = pty
                    
                    while True:
                        try:
                            if not pty.isalive():
                                break
                            data = pty.read(blocking=True)
                            if not data:
                                break
                            if self._window:
                                self._window.evaluate_js(f"window.onInstallData('{name}', {json.dumps(data)});")
                        except Exception:
                            break
                    
                    exit_code = 1
                    try:
                        exit_code = pty.get_exitstatus()
                        pty.close()
                    except Exception:
                        pass
                        
                    if session_id in self._sessions:
                        del self._sessions[session_id]
                    
                    try:
                        if os.path.exists(tar_path):
                            os.remove(tar_path)
                    except Exception:
                        pass
                        
                    success_status = (exit_code == 0)
                    msg = f"Exit code: {exit_code}" if not success_status else "Imported successfully!"
                    if self._window:
                        self._window.evaluate_js(f"window.onInstallComplete('{name}', {json.dumps(success_status)}, {json.dumps(msg)});")
                except Exception as ex:
                    try:
                        if os.path.exists(tar_path):
                            os.remove(tar_path)
                    except Exception:
                        pass
                    if self._window:
                        self._window.evaluate_js(f"window.onInstallComplete('{name}', false, {json.dumps(str(ex))});")
            
            threading.Thread(target=task_thread, daemon=True).start()
            return {"started": True}
        except Exception as e:
            return {"started": False, "message": str(e)}

def get_asset_path(filename):
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        path = os.path.join(exe_dir, filename)
        if os.path.exists(path):
            return path
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            return os.path.join(meipass, filename)
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) if __file__ else os.getcwd()
    return os.path.join(current_dir, filename)

def main():
    terminal_windows = []
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            import os

            TH32CS_SNAPPROCESS = 2

            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ('dwSize', wintypes.DWORD),
                    ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_void_p),
                    ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD),
                    ('szExeFile', ctypes.c_wchar * 260)
                ]

            def get_parent_pid(pid):
                h = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
                if h == -1 or h is None:
                    return None
                pe = PROCESSENTRY32()
                pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
                if ctypes.windll.kernel32.Process32FirstW(h, ctypes.byref(pe)):
                    while True:
                        if pe.th32ProcessID == pid:
                            ctypes.windll.kernel32.CloseHandle(h)
                            return pe.th32ParentProcessID
                        if not ctypes.windll.kernel32.Process32NextW(h, ctypes.byref(pe)):
                            break
                ctypes.windll.kernel32.CloseHandle(h)
                return None

            # Collect all ancestor PIDs of the current Python process
            ancestor_pids = set()
            curr_pid = os.getpid()
            ancestor_pids.add(curr_pid)
            while curr_pid:
                curr_pid = get_parent_pid(curr_pid)
                if curr_pid:
                    ancestor_pids.add(curr_pid)

            # Callback to find top-level visible window belonging to any ancestor process
            def enum_windows_callback(hwnd, lParam):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    lpdw_process_id = wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
                    wpid = lpdw_process_id.value
                    if wpid in ancestor_pids:
                        buf = ctypes.create_unicode_buffer(256)
                        ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
                        # Check against common terminal window classes:
                        # - CASCADIA_HOSTING_WINDOW_CLASS (Windows Terminal)
                        # - ConsoleWindowClass (Classic CMD/PowerShell)
                        # - mintty (Git Bash terminal)
                        # - VirtualConsoleClass (ConEmu/Cmder)
                        if buf.value in ("CASCADIA_HOSTING_WINDOW_CLASS", "ConsoleWindowClass", "mintty", "VirtualConsoleClass"):
                            terminal_windows.append(hwnd)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

            # Fallback to GetConsoleWindow if no terminal window was matched through ancestors
            if not terminal_windows:
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    terminal_windows.append(hwnd)

            # Hide the detected terminal windows
            for hwnd in terminal_windows:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
        except Exception:
            pass

    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('nexus.wsl.manager.v1')
        except Exception:
            pass

    api = Api()
    
    html_path = get_asset_path('index.html')

    window = webview.create_window(
        f'WSL Desktop Nexus  v{APP_VERSION}',
        html_path,
        js_api=api,
        width=1280,
        height=800,
        min_size=(900, 600),
        background_color='#0c0f16'
    )
    
    api._window = window
    
    def on_closed():
        for session_id, pty in list(api._sessions.items()):
            try:
                pty.close(force=True)
            except Exception:
                pass
                
    window.events.closed += on_closed

    def check_for_updates():
        """Comprueba GitHub Releases en segundo plano y avisa si hay nueva versión."""
        import time
        time.sleep(4)  # espera a que la UI esté cargada
        try:
            url = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'
            req = urllib.request.Request(url, headers={'User-Agent': 'WSLNexus-UpdateChecker'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            latest = data.get('tag_name', '').lstrip('v').strip()
            if latest and latest != APP_VERSION:
                dl_url = data.get('html_url', f'https://github.com/{GITHUB_REPO}/releases/latest')
                if window:
                    window.evaluate_js(
                        f"window.onUpdateAvailable({json.dumps(latest)}, {json.dumps(dl_url)});"
                    )
        except Exception:
            pass  # silencioso si no hay internet

    threading.Thread(target=check_for_updates, daemon=True).start()

    try:
        webview.start(icon=get_asset_path('app.ico'), debug=False)
    finally:
        if sys.platform == 'win32' and terminal_windows:
            try:
                import ctypes
                for hwnd in terminal_windows:
                    ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW = 5
            except Exception:
                pass

if __name__ == '__main__':
    main()
