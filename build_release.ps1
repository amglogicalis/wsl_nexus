<#
.SYNOPSIS
    Build script completo para WSL Desktop Nexus.
    Compila app.exe con PyInstaller, luego compila el installer.exe con Inno Setup,
    y opcionalmente sube el resultado a GitHub Releases.

.PARAMETER Version
    Versión del release (sobrescribe el archivo VERSION si se especifica).

.PARAMETER UploadRelease
    Si se especifica, crea el release en GitHub y sube el installer.

.PARAMETER GitHubToken
    Personal Access Token de GitHub para subir el release.

.EXAMPLE
    # Solo compilar
    .\build_release.ps1

    # Compilar y subir release v1.2.0
    .\build_release.ps1 -Version "1.2.0" -UploadRelease -GitHubToken "ghp_..."
#>

param(
    [string]$Version      = "",
    [switch]$UploadRelease,
    [string]$GitHubToken  = ""
)

$ErrorActionPreference = "Stop"
$RepoOwner = "amglogicalis"
$RepoName  = "wsl_nexus"

# ─── Helpers ──────────────────────────────────────────────────────────────────

function Write-Step($msg) {
    Write-Host ""
    Write-Host "  ➜ $msg" -ForegroundColor Cyan
}

function Write-OK($msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "  ✗ $msg" -ForegroundColor Red
    exit 1
}

function Require-Command($cmd, $installHint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Fail "$cmd no encontrado. $installHint"
    }
}

# ─── Verificar herramientas ────────────────────────────────────────────────────

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "   WSL Desktop Nexus - Build & Release      " -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════" -ForegroundColor Magenta

Write-Step "Verificando herramientas..."
Require-Command "python"     "Instala Python 3.10+ desde https://python.org"
Require-Command "git"        "Instala Git desde https://git-scm.com"

# Verificar PyInstaller
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Fail "PyInstaller no instalado. Ejecuta: pip install pyinstaller" }

# Detectar Inno Setup
$innoPath = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $innoPath) {
    Write-Fail "Inno Setup 6 no encontrado. Descárgalo desde https://jrsoftware.org/isdl.php"
}
Write-OK "Herramientas verificadas."

# ─── Versión ───────────────────────────────────────────────────────────────────

if ($Version -ne "") {
    $Version | Out-File -FilePath "VERSION" -Encoding ascii -NoNewline
    Write-OK "Versión establecida a: $Version"
} else {
    $Version = (Get-Content "VERSION").Trim()
    Write-OK "Versión leída del archivo VERSION: $Version"
}

# ─── Compilar app.exe con PyInstaller ─────────────────────────────────────────

Write-Step "Compilando app.exe con PyInstaller..."
python -m PyInstaller app.spec --clean
if ($LASTEXITCODE -ne 0) { Write-Fail "PyInstaller falló." }
Write-OK "app.exe compilado correctamente en dist\"

# ─── Compilar installer con Inno Setup ────────────────────────────────────────

Write-Step "Compilando installer con Inno Setup..."

# Crear carpeta de output si no existe
New-Item -ItemType Directory -Force -Path "installer_output" | Out-Null

& $innoPath "installer.iss"
if ($LASTEXITCODE -ne 0) { Write-Fail "Inno Setup falló al compilar installer.iss" }

$installerFile = "installer_output\WSLNexus_Setup_v$Version.exe"
if (-not (Test-Path $installerFile)) {
    Write-Fail "No se encontró el installer compilado: $installerFile"
}

$sizeMB = [math]::Round((Get-Item $installerFile).Length / 1MB, 1)
Write-OK "Installer creado: $installerFile ($sizeMB MB)"

# ─── Copiar app.exe a carpeta raíz (para desarrollo) ──────────────────────────

Copy-Item -Path "dist\app.exe" -Destination "app.exe" -Force
Write-OK "app.exe copiado a carpeta raíz."

# ─── Subir a GitHub Releases ──────────────────────────────────────────────────

if ($UploadRelease) {
    if ($GitHubToken -eq "") {
        Write-Fail "Especifica -GitHubToken para subir el release."
    }

    $headers = @{
        Authorization = "token $GitHubToken"
        Accept        = "application/vnd.github.v3+json"
    }

    Write-Step "Creando tag v$Version en git..."
    git tag -a "v$Version" -m "Release v$Version"
    git push https://amglogicalis:$GitHubToken@github.com/$RepoOwner/$RepoName.git "v$Version"

    Write-Step "Creando release en GitHub..."
    $releaseBody = @{
        tag_name         = "v$Version"
        target_commitish = "main"
        name             = "WSL Desktop Nexus v$Version"
        body             = "## WSL Desktop Nexus v$Version`n`n### Instalación`nDescarga ``WSLNexus_Setup_v$Version.exe`` y ejecútalo como administrador.`n`n### Requisitos`n- Windows 10/11 (64-bit)`n- El installer activará WSL automáticamente si es necesario."
        draft            = $false
        prerelease       = $false
    } | ConvertTo-Json

    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$RepoOwner/$RepoName/releases" `
        -Method POST -Headers $headers -Body $releaseBody -ContentType "application/json"

    Write-OK "Release creado: $($release.html_url)"

    # Subir installer.exe como asset
    Write-Step "Subiendo $installerFile al release..."
    $uploadUrl = $release.upload_url -replace "\{.*\}", "?name=WSLNexus_Setup_v$Version.exe"
    $fileBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $installerFile))
    Invoke-RestMethod -Uri $uploadUrl -Method POST -Headers $headers `
        -Body $fileBytes -ContentType "application/octet-stream" | Out-Null

    Write-OK "Installer subido al release de GitHub."
    Write-Host ""
    Write-Host "  🎉 Release disponible en: $($release.html_url)" -ForegroundColor Green
}

# ─── Resumen ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "   Build completado con éxito               " -ForegroundColor Green
Write-Host "═══════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  app.exe          → dist\app.exe" -ForegroundColor White
Write-Host "  installer.exe    → $installerFile" -ForegroundColor White
Write-Host ""
