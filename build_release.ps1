<#
.SYNOPSIS
    Build script para WSL Desktop Nexus.
    Compila app.exe con PyInstaller, el installer.exe con Inno Setup
    y opcionalmente sube el resultado a GitHub Releases.

.PARAMETER Version
    Version del release (sobrescribe el archivo VERSION si se indica).

.PARAMETER UploadRelease
    Si se especifica, crea un release en GitHub y sube el installer.

.PARAMETER GitHubToken
    PAT de GitHub. Opcional: si no se da, se usa 'git push origin' normal.

.EXAMPLE
    .\build_release.ps1
    .\build_release.ps1 -Version "1.1.0" -UploadRelease
    .\build_release.ps1 -Version "1.1.0" -UploadRelease -GitHubToken "ghp_..."
#>

param(
    [string]$Version       = "",
    [switch]$UploadRelease,
    [string]$GitHubToken   = ""
)

$ErrorActionPreference = "Stop"
$RepoOwner = "amglogicalis"
$RepoName  = "wsl_nexus"

function Step($msg)  { Write-Host ""; Write-Host "  >> $msg" -ForegroundColor Cyan }
function OK($msg)    { Write-Host "  OK  $msg" -ForegroundColor Green }
function Fail($msg)  { Write-Host "  ERR $msg" -ForegroundColor Red; exit 1 }

function Require-Cmd($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Fail "$cmd no encontrado. $hint" }
}

# ── Cabecera ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "   WSL Desktop Nexus - Build and Release    " -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta

# ── Verificar herramientas ────────────────────────────────────────────────────
Step "Verificando herramientas..."
Require-Cmd "python" "Instala Python 3.10+ desde https://python.org"
Require-Cmd "git"    "Instala Git desde https://git-scm.com"

python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller no instalado. Ejecuta: pip install pyinstaller" }

$innoPath = $null

# 1. Intentar buscar en el registro (HKLM y HKCU, incluyendo WOW6432Node)
$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
    "HKCU:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
)

foreach ($regPath in $regPaths) {
    if (Test-Path $regPath) {
        $installLoc = (Get-ItemProperty -Path $regPath -Name "InstallLocation" -ErrorAction SilentlyContinue).InstallLocation
        if ($installLoc) {
            $candidate = Join-Path $installLoc "ISCC.exe"
            if (Test-Path $candidate) {
                $innoPath = $candidate
                break
            }
        }
    }
}

# 2. Intentar buscar en el PATH del sistema
if (-not $innoPath) {
    $cmd = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        $innoPath = $cmd.Source
    }
}

# 3. Ubicaciones comunes hardcoded como fallback
if (-not $innoPath) {
    $innoPath = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $innoPath) {
    Fail "Inno Setup 6 no encontrado. Descargalo desde https://jrsoftware.org/isdl.php"
}
OK "Herramientas OK."

# ── Version ───────────────────────────────────────────────────────────────────
if ($Version -ne "") {
    [System.IO.File]::WriteAllText("$PWD\VERSION", $Version)
    OK "Version establecida: $Version"
} else {
    $Version = (Get-Content "VERSION" -Raw).Trim()
    OK "Version leida de VERSION: $Version"
}

# ── Compilar app.exe ─────────────────────────────────────────────────────────
Step "Compilando app.exe con PyInstaller..."
python -m PyInstaller app.spec --clean
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller fallo." }
OK "app.exe listo en dist\"

# Copia rapida a raiz para desarrollo
Copy-Item -Path "dist\app.exe" -Destination "app.exe" -Force
OK "app.exe copiado a raiz."

# ── Compilar installer.exe ────────────────────────────────────────────────────
Step "Compilando installer con Inno Setup..."
New-Item -ItemType Directory -Force -Path "installer_output" | Out-Null

& $innoPath "installer.iss"
if ($LASTEXITCODE -ne 0) { Fail "Inno Setup fallo al compilar installer.iss" }

$installerFile = "installer_output\WSLNexus_Setup_v$Version.exe"
if (-not (Test-Path $installerFile)) { Fail "No se encontro el installer: $installerFile" }

$sizeMB = [math]::Round((Get-Item $installerFile).Length / 1MB, 1)
OK "Installer listo: $installerFile ($sizeMB MB)"

# ── Resolver Token de GitHub ──────────────────────────────────────────────────
if ($UploadRelease) {
    if ($GitHubToken -eq "") {
        if ($env:GITHUB_TOKEN) {
            $GitHubToken = $env:GITHUB_TOKEN
            Write-Host "  (Token obtenido de la variable de entorno GITHUB_TOKEN)" -ForegroundColor Green
        }
        elseif (Get-Command "gh" -ErrorAction SilentlyContinue) {
            $ghToken = (gh auth token 2>$null)
            if ($ghToken) {
                $GitHubToken = $ghToken.Trim()
                Write-Host "  (Token obtenido de gh CLI)" -ForegroundColor Green
            }
        }
    }

    if ($GitHubToken -eq "") {
        Write-Host ""
        Write-Host "  Para crear y subir el release en GitHub se requiere un Token de Acceso Personal (PAT)." -ForegroundColor Yellow
        Write-Host "  Por favor, introducelo a continuacion (o pulsa Enter para omitir la subida a GitHub):" -ForegroundColor Yellow
        $promptToken = Read-Host -Prompt "GitHub PAT"
        if ($promptToken) {
            $GitHubToken = $promptToken.Trim()
        }
    }

    if ($GitHubToken -eq "") {
        Write-Host "  Advertencia: No se indico/encontro un token de GitHub. Se omitira la creacion del release." -ForegroundColor Yellow
        $UploadRelease = $false
    }
}

# ── Subir a GitHub Releases ───────────────────────────────────────────────────
if ($UploadRelease) {

    Step "Creando tag v$Version y haciendo push..."
    if (git tag -l "v$Version") {
        Write-Host "  (Tag local v$Version ya existe. Recreandolo...)" -ForegroundColor Yellow
        git tag -d "v$Version" | Out-Null
    }
    git tag -a "v$Version" -m "Release v$Version"
    if ($LASTEXITCODE -ne 0) { Fail "No se pudo crear el tag local." }

    if ($GitHubToken -ne "") {
        git push -f "https://amglogicalis:$GitHubToken@github.com/$RepoOwner/$RepoName.git" "v$Version"
    } else {
        git push -f origin "v$Version"
    }

    if ($LASTEXITCODE -ne 0) { Fail "No se pudo hacer push del tag." }
    OK "Tag v$Version subido."

    Step "Preparando release en GitHub..."
    $headers = @{
        Authorization = "token $GitHubToken"
        Accept        = "application/vnd.github.v3+json"
    }

    $releaseNotes = "## WSL Desktop Nexus v$Version`n`n" +
        "### Instalacion`n" +
        "Descarga ``WSLNexus_Setup_v$Version.exe`` y ejecutalo como Administrador.`n`n" +
        "### Requisitos`n" +
        "- Windows 10/11 (64-bit)`n" +
        "- El installer activa WSL automaticamente si es necesario."

    $body = @{
        tag_name         = "v$Version"
        target_commitish = "main"
        name             = "WSL Desktop Nexus v$Version"
        body             = $releaseNotes
        draft            = $false
        prerelease       = $false
    } | ConvertTo-Json -Compress

    # Intentar obtener release existente
    $release = $null
    try {
        $release = Invoke-RestMethod `
            -Uri "https://api.github.com/repos/$RepoOwner/$RepoName/releases/tags/v$Version" `
            -Method GET -Headers $headers -ErrorAction SilentlyContinue
    } catch {
        # El release no existe
    }

    if ($release) {
        Write-Host "  (Release existente encontrado. Actualizando descripcion...)" -ForegroundColor Yellow
        $release = Invoke-RestMethod `
            -Uri "https://api.github.com/repos/$RepoOwner/$RepoName/releases/$($release.id)" `
            -Method PATCH -Headers $headers -Body $body -ContentType "application/json"
    } else {
        $release = Invoke-RestMethod `
            -Uri "https://api.github.com/repos/$RepoOwner/$RepoName/releases" `
            -Method POST -Headers $headers -Body $body -ContentType "application/json"
    }

    OK "Release preparado: $($release.html_url)"

    Step "Subiendo installer al release de GitHub..."
    $assetName = "WSLNexus_Setup_v$Version.exe"
    if ($release.assets) {
        $existingAsset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
        if ($existingAsset) {
            Write-Host "  (El archivo '$assetName' ya existe en el release. Eliminandolo para actualizar...)" -ForegroundColor Yellow
            try {
                Invoke-RestMethod `
                    -Uri "https://api.github.com/repos/$RepoOwner/$RepoName/releases/assets/$($existingAsset.id)" `
                    -Method DELETE -Headers $headers -ErrorAction Stop
                OK "Archivo anterior eliminado."
            } catch {
                Fail "No se pudo eliminar el archivo anterior del release: $_"
            }
        }
    }

    $uploadUrl = $release.upload_url -replace "\{.*\}", "?name=$assetName"
    $fileBytes  = [System.IO.File]::ReadAllBytes((Resolve-Path $installerFile))

    Invoke-RestMethod -Uri $uploadUrl -Method POST -Headers $headers `
        -Body $fileBytes -ContentType "application/octet-stream" | Out-Null

    OK "Installer subido correctamente."
    Write-Host ""
    Write-Host "  Release publicado en: $($release.html_url)" -ForegroundColor Green
}

# ── Resumen ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "   Build completado con exito               " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  app.exe       --> dist\app.exe"
Write-Host "  installer.exe --> $installerFile"
Write-Host ""
