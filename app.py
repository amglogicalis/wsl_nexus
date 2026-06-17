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

# Each entry: url=AppxBundle download, pkg_name=Get-AppxPackage -Name pattern,
# exe_hint=prefix of the launcher exe inside the package, winget_id=winget package id.
DISTRO_FALLBACK_INFO = {
    "ubuntu": {
        "url": "https://aka.ms/wslubuntu",
        "pkg_name": "CanonicalGroupLimited.Ubuntu*",
        "exe_hint": "ubuntu",
        "winget_id": "Canonical.Ubuntu"
    },
    "ubuntu-24.04": {
        "url": "https://aka.ms/wslubuntu2404",
        "pkg_name": "CanonicalGroupLimited.Ubuntu24.04LTS*",
        "exe_hint": "ubuntu2404",
        "winget_id": "Canonical.Ubuntu.2404"
    },
    "ubuntu-22.04": {
        "url": "https://aka.ms/wslubuntu2204",
        "pkg_name": "CanonicalGroupLimited.Ubuntu22.04LTS*",
        "exe_hint": "ubuntu2204",
        "winget_id": "Canonical.Ubuntu.2204"
    },
    "ubuntu-20.04": {
        "url": "https://aka.ms/wslubuntu2004",
        "pkg_name": "CanonicalGroupLimited.Ubuntu20.04LTS*",
        "exe_hint": "ubuntu2004",
        "winget_id": "Canonical.Ubuntu.2004"
    },
    "ubuntu-18.04": {
        "url": "https://aka.ms/wsl-ubuntu-1804",
        "pkg_name": "CanonicalGroupLimited.Ubuntu18.04onWindows*",
        "exe_hint": "ubuntu1804",
        "winget_id": "Canonical.Ubuntu.1804"
    },
    "debian": {
        "url": "https://aka.ms/wsl-debian-gnulinux",
        "pkg_name": "TheDebianProject.DebianGNULinux*",
        "exe_hint": "debian",
        "winget_id": "TheDebianProject.DebianGNULinux"
    },
    "kali-linux": {
        "url": "https://aka.ms/wsl-kali-linux-new",
        "pkg_name": "KaliLinux.KaliLinuxforWindowsSubsystemforLinux*",
        "exe_hint": "kali",
        "winget_id": "KaliLinux.KaliLinux"
    },
    "opensuse-leap-15.5": {
        "url": "https://aka.ms/wsl-opensuse-leap-15-5",
        "pkg_name": "46932SUSE.openSUSELeap15.5*",
        "exe_hint": "openSUSE",
        "winget_id": "openSUSE.openSUSELeap15.5"
    },
    "sles-15": {
        "url": "https://aka.ms/wsl-sles-15",
        "pkg_name": "46932SUSE.SUSELinuxEnterpriseServer15SP5*",
        "exe_hint": "SLES",
        "winget_id": "SUSE.SUSELinuxEnterpriseServer15SP5"
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
                except Exception as e:
                    if self._window:
                        self._window.evaluate_js(
                            f"window.onInstallComplete('{distro_name}', false, {json.dumps(str(e))});"
                        )
                    return

                try:
                    for line in proc.stdout:
                        if self._window:
                            self._window.evaluate_js(
                                f"window.onInstallData('{distro_name}', {json.dumps(line)});"
                            )
                        # Check for unrecognized/invalid option error text
                        lower_line = line.lower()
                        if any(term in lower_line for term in ["invalid option", "unrecognized option", "unknown option", "opción no válida", "parámetro no válido", "invalid command line option", "error: 0x"]):
                            # Note: "error: 0x" might also indicate other errors, but we want to make sure it's invalid parameter related if it fails immediately.
                            if any(opt in lower_line for opt in ["--web-download", "option", "parameter", "argument", "opción", "parámetro"]):
                                invalid_option_detected = True
                except Exception:
                    pass
                finally:
                    try:
                        proc.stdout.close()
                    except Exception:
                        pass

                exit_code = proc.wait()

                # If it failed due to an unrecognized parameter, retry without --web-download
                if exit_code != 0 and invalid_option_detected:
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
                    except Exception as e:
                        if self._window:
                            self._window.evaluate_js(
                                f"window.onInstallComplete('{distro_name}', false, {json.dumps(str(e))});"
                            )
                        return

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

                if exit_code != 0:
                    if self._window:
                        self._window.evaluate_js(
                            f"window.onInstallData('{distro_name}', '\\n[Nexus] Instalación estándar fallida. Iniciando instalación de fallback vía PowerShell (Start-BitsTransfer & Add-AppxPackage)...\\n\\n');"
                        )
                    fallback_success = self._run_powershell_fallback_install(distro_name, session_id)
                    if fallback_success:
                        success_status = True
                        msg = "Finished successfully (via fallback)"
                    else:
                        success_status = False
                        msg = f"Standard installation and PowerShell fallback both failed (Exit code: {exit_code})"
                else:
                    success_status = True
                    msg = "Finished successfully"

                if session_id in self._sessions:
                    del self._sessions[session_id]

                if self._window:
                    self._window.evaluate_js(
                        f"window.onInstallComplete('{distro_name}', {json.dumps(success_status)}, {json.dumps(msg)});"
                    )

            threading.Thread(target=run_installation, daemon=True).start()
            return {"started": True, "session_id": session_id}
        except Exception as e:
            return {"started": False, "message": str(e)}

    def _run_powershell_fallback_install(self, distro_name, session_id):
        """Fallback WSL distro installation via winget (preferred) or
        Start-BitsTransfer + Add-AppxPackage + silent --root registration.
        No interactive console window is opened; the distro is initialised
        with root as the default user so it appears correctly in the app.
        """
        info = get_fallback_info(distro_name)
        url        = info["url"]
        pkg_name   = info["pkg_name"]
        exe_hint   = info["exe_hint"]
        winget_id  = info["winget_id"]

        ps_script = f"""
$ErrorActionPreference = 'Continue'
$distroName = '{distro_name}'
$wingetId   = '{winget_id}'
$url        = '{url}'
$pkgName    = '{pkg_name}'
$exeHint    = '{exe_hint}'

# ── Step 1: try winget (silent, no window) ───────────────────────────────────
Write-Host '[Nexus] Intentando instalación con winget...'
$wingetExe = (Get-Command winget -ErrorAction SilentlyContinue)?.Source
if ($wingetExe) {{
    $wg = Start-Process -FilePath $wingetExe `
        -ArgumentList "install --id $wingetId --source winget --accept-source-agreements --accept-package-agreements --silent --disable-interactivity" `
        -Wait -PassThru -NoNewWindow
    if ($wg.ExitCode -eq 0) {{
        Write-Host '[Nexus] winget instaló el paquete correctamente.'
    }} else {{
        Write-Host "[Nexus] winget falló (código $($wg.ExitCode)). Probando con AppxPackage..."
    }}
}}

# ── Step 2: fallback via Start-BitsTransfer + Add-AppxPackage ────────────────
$pkg = Get-AppxPackage -Name $pkgName -ErrorAction SilentlyContinue
if (-not $pkg) {{
    Write-Host "[Nexus] Descargando paquete desde $url ..."
    New-Item -ItemType Directory -Force -Path 'C:\\WSL' | Out-Null
    $dest = "C:\\WSL\\$distroName.appx"
    if (Test-Path $dest) {{ Remove-Item $dest -Force }}
    try {{
        Start-BitsTransfer -Source $url -Destination $dest -ErrorAction Stop
        Write-Host '[Nexus] Descarga completada. Instalando paquete...'
        Add-AppxPackage -Path $dest -ErrorAction Stop
        Write-Host '[Nexus] Paquete instalado.'
        Start-Sleep -Seconds 3
    }} catch {{
        Write-Host "[Nexus] ERROR al instalar paquete: $_"
        exit 1
    }}
}}

# ── Step 3: locate the distro launcher exe ───────────────────────────────────
$pkg = Get-AppxPackage -Name $pkgName -ErrorAction SilentlyContinue
if (-not $pkg) {{
    Write-Host '[Nexus] ERROR: No se encontró el paquete AppxPackage tras la instalación.'
    exit 1
}}
$installLoc = $pkg.InstallLocation
Write-Host "[Nexus] Paquete encontrado en: $installLoc"

# Find exe: prefer one whose name starts with the exe_hint, else take the first
$exes = Get-ChildItem -Path $installLoc -Filter '*.exe' -ErrorAction SilentlyContinue
$exe  = ($exes | Where-Object {{ $_.Name -like "$exeHint*.exe" }} | Select-Object -First 1)
if (-not $exe) {{ $exe = $exes | Select-Object -First 1 }}
if (-not $exe) {{
    Write-Host '[Nexus] ERROR: No se encontró el ejecutable de la distribución.'
    exit 1
}}
Write-Host "[Nexus] Ejecutable encontrado: $($exe.Name)"

# ── Step 4: silent registration (--root avoids interactive username prompt) ──
Write-Host '[Nexus] Registrando distribución en WSL (modo root)...'
$reg = Start-Process -FilePath $exe.FullName `
    -ArgumentList 'install --root' `
    -Wait -PassThru -NoNewWindow `
    -RedirectStandardOutput 'NUL' -RedirectStandardError 'NUL'

if ($reg.ExitCode -eq 0) {{
    Write-Host "[Nexus] Distribución '$distroName' registrada correctamente como root."
    Write-Host "[Nexus] Puedes crear un usuario normal desde el terminal de la app con: adduser <nombre>"
}} else {{
    # Some distros don't support --root; try plain launch and wait briefly
    Write-Host '[Nexus] --root no soportado; intentando registro directo...'
    $reg2 = Start-Process -FilePath $exe.FullName -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput 'NUL' -RedirectStandardError 'NUL'
    Write-Host "[Nexus] Proceso de registro finalizado (código $($reg2.ExitCode))."
}}

Write-Host '[Nexus] Instalación de fallback completada con éxito.'
exit 0
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

            for line in proc.stdout:
                if self._window:
                    self._window.evaluate_js(
                        f"window.onInstallData('{distro_name}', {json.dumps(line)});"
                    )

            exit_code = proc.wait()
            return exit_code == 0
        except Exception as e:
            if self._window:
                self._window.evaluate_js(
                    f"window.onInstallData('{distro_name}', '[Nexus] ERROR al iniciar PowerShell: {json.dumps(str(e))}\\n');"
                )
            return False

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

    webview.start(icon=get_asset_path('app.ico'), debug=False)

if __name__ == '__main__':
    main()
