# check_prereqs.ps1
# Ejecutado por el installer con privilegios de administrador.
# Habilita WSL y Virtual Machine Platform si no están activos,
# instala WebView2 si es necesario, y establece WSL 2 como versión por defecto.

$logFile = "$env:TEMP\WSLNexus_prereqs.log"
"[$(Get-Date)] Iniciando verificación de requisitos..." | Out-File $logFile -Append

function Log($msg) {
    "[$(Get-Date)] $msg" | Out-File $logFile -Append
}

# --- Habilitar WSL ---
$wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -ErrorAction SilentlyContinue
if ($wslFeature -and $wslFeature.State -ne "Enabled") {
    Log "Habilitando WSL (Microsoft-Windows-Subsystem-Linux)..."
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart -ErrorAction SilentlyContinue
    Log "WSL habilitado."
} else {
    Log "WSL ya estaba habilitado."
}

# --- Habilitar Virtual Machine Platform (necesario para WSL 2) ---
$vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -ErrorAction SilentlyContinue
if ($vmFeature -and $vmFeature.State -ne "Enabled") {
    Log "Habilitando VirtualMachinePlatform..."
    Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart -ErrorAction SilentlyContinue
    Log "VirtualMachinePlatform habilitado."
} else {
    Log "VirtualMachinePlatform ya estaba habilitado."
}

# --- Habilitar WebView2 Runtime ---
function Get-WebView2Installed {
    $paths = @(
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8ABB-7D3E475C78E7}",
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8ABB-7D3E475C78E7}",
        "HKCU:\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8ABB-7D3E475C78E7}"
    )
    foreach ($path in $paths) {
        if (Test-Path $path) {
            $pv = (Get-ItemProperty -Path $path -Name "pv" -ErrorAction SilentlyContinue).pv
            if ($pv) { return $true }
        }
    }
    return $false
}

if (-not (Get-WebView2Installed)) {
    Log "WebView2 Runtime no encontrado. Descargando instalador de Edge WebView2..."
    $url = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    $installerPath = "$env:TEMP\MicrosoftEdgeWebview2Setup.exe"
    try {
        if (Get-Command Invoke-WebRequest -ErrorAction SilentlyContinue) {
            Invoke-WebRequest -Uri $url -OutFile $installerPath -UseBasicParsing
        } else {
            $webClient = New-Object System.Net.WebClient
            $webClient.DownloadFile($url, $installerPath)
        }
        Log "Descarga de WebView2 completada. Iniciando instalación silenciosa..."
        $process = Start-Process -FilePath $installerPath -ArgumentList "/silent /install" -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -eq 0) {
            Log "WebView2 instalado correctamente."
        } else {
            Log "Instalador de WebView2 finalizó con código de salida: $($process.ExitCode)"
        }
    } catch {
        Log "Error al descargar o instalar WebView2: $_"
    } finally {
        if (Test-Path $installerPath) {
            Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Log "WebView2 Runtime ya está instalado."
}

# --- Actualizar WSL a la versión más reciente (si es posible) ---
try {
    Log "Actualizando WSL..."
    $updateResult = & wsl.exe --update 2>&1
    Log "wsl --update: $updateResult"
} catch {
    Log "No se pudo actualizar WSL: $_"
}

# --- Establecer WSL 2 como versión por defecto ---
try {
    $result = & wsl.exe --set-default-version 2 2>&1
    Log "wsl --set-default-version 2: $result"
} catch {
    Log "No se pudo establecer WSL 2 por defecto (puede requerir reinicio): $_"
}

Log "Verificación de requisitos completada."
