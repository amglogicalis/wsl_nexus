; ============================================================
;  WSL Desktop Nexus - Inno Setup Installer Script
;  Requiere: Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; ============================================================

#define AppName      "WSL Desktop Nexus"
#define AppPublisher "AMG Logicalis"
#define AppURL       "https://github.com/amglogicalis/wsl_nexus"
#define AppExeName   "app.exe"
#define VersionFile  "VERSION"
#define VerFile      FileOpen(VersionFile)
#define AppVersion   Trim(FileRead(VerFile))
#expr FileClose(VerFile)

[Setup]
AppId={{A3F7B2E1-0C4D-4A9F-8E3B-1D5C7F2A8B6E}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=WSLNexus_Setup_v{#AppVersion}
SetupIconFile=app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
spanish.WSLCheckTitle=Verificando requisitos del sistema
spanish.WSLCheckMsg=Habilitando Windows Subsystem for Linux (WSL 2)...%nEsto puede tardar un momento.
spanish.WSLRestartWarning=WSL ha sido habilitado correctamente.%n%nIMPORTANTE: Es posible que necesites reiniciar el equipo antes de usar WSL Desktop Nexus.%n%n¿Deseas reiniciar ahora?
spanish.WSLAlreadyOK=WSL 2 ya está disponible en este equipo.

[Tasks]
Name: "desktopicon";   Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Anclar al Menú de Inicio";                    GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
; Ejecutable principal (compilado con PyInstaller - incluye Python)
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Icono
Source: "app.ico";            DestDir: "{app}"; Flags: ignoreversion
; Archivo de versión (para update checker)
Source: "VERSION";            DestDir: "{app}"; Flags: ignoreversion
; Script de prereqs (se elimina después de instalación)
Source: "check_prereqs.ps1";  DestDir: "{app}"; Flags: ignoreversion deleteafterinstall

[Icons]
; Menú de Inicio
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\app.ico"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
; Escritorio (opcional)
Name: "{autodesktop}\{#AppName}";       Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon
; Barra de tareas / Anclar inicio (opcional)
Name: "{userstartmenu}\{#AppName}";     Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\app.ico"; Tasks: startmenuicon

[Registry]
; Registrar en Agregar/Quitar programas con metadatos extra
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1"; ValueType: string; ValueName: "DisplayVersion";   ValueData: "{#AppVersion}";        Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1"; ValueType: string; ValueName: "Publisher";        ValueData: "{#AppPublisher}";      Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1"; ValueType: string; ValueName: "URLInfoAbout";     ValueData: "{#AppURL}";            Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1"; ValueType: dword;  ValueName: "EstimatedSize";    ValueData: "20480";                Flags: uninsdeletevalue

[Run]
; 1. Habilitar WSL silenciosamente (como admin - ya que el installer lo es)
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\check_prereqs.ps1"""; StatusMsg: "Habilitando WSL 2 (si es necesario)..."; Flags: runhidden waituntilterminated

; 2. Lanzar la app al terminar (opcional)
Filename: "{app}\{#AppExeName}"; Description: "Lanzar {#AppName} ahora"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
var
  WSLNeedsRestart: Boolean;

// Comprueba si WSL está disponible ejecutando "wsl --status"
function IsWSL2Available(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('wsl.exe', '--status', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Después de instalar, comprobar si WSL quedó disponible
    if not IsWSL2Available() then
    begin
      WSLNeedsRestart := True;
    end else
    begin
      MsgBox(CustomMessage('WSLAlreadyOK'), mbInformation, MB_OK);
    end;
  end;
end;

function NeedRestart(): Boolean;
begin
  Result := WSLNeedsRestart;
end;

// Limpiar acceso directo del escritorio al desinstalar
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DeleteFile(ExpandConstant('{autodesktop}\{#AppName}.lnk'));
    DeleteFile(ExpandConstant('{userstartmenu}\{#AppName}.lnk'));
  end;
end;
