# check_prereqs.ps1
# Ejecutado por el installer con privilegios de administrador.
# Habilita WSL y Virtual Machine Platform si no están activos,
# y establece WSL 2 como versión por defecto.

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

# --- Establecer WSL 2 como versión por defecto ---
try {
    $result = & wsl.exe --set-default-version 2 2>&1
    Log "wsl --set-default-version 2: $result"
} catch {
    Log "No se pudo establecer WSL 2 por defecto (puede requerir reinicio): $_"
}

Log "Verificación de requisitos completada."
