; Inno Setup script untuk OptiPulse NOC
; Build: "C:\Users\Lenovo\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
; Hasil: dist\OptiPulse-NOC-Setup.exe

#define MyAppName "OptiPulse NOC"
#define MyAppVersion "1.4.0"
#define MyAppPublisher "OptiPulse"
#define MyAppExeName "OptiPulse-NOC.exe"

[Setup]
AppId={{8F3C2E7A-5B1D-4E9A-9C41-2D7F6A0B3E58}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\OptiPulse NOC
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=OptiPulse-NOC-Setup
SetupIconFile=assets\optipulse.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
InfoAfterFile=installer\PANDUAN-SETELAH-INSTALL.txt

[Languages]
Name: "indonesian"; MessagesFile: "installer\Indonesian.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut:"; Flags: checkedonce
Name: "autostart"; Description: "Jalankan OptiPulse NOC otomatis saat Windows login"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\OptiPulse-NOC.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "optipulse.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer\PANDUAN-SETELAH-INSTALL.txt"; DestDir: "{app}"; DestName: "PANDUAN.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Panduan"; Filename: "{app}\PANDUAN.txt"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan {#MyAppName} sekarang"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\optipulse.env"
Type: files; Name: "{app}\optipulse.env.example"
Type: files; Name: "{app}\PANDUAN.txt"
