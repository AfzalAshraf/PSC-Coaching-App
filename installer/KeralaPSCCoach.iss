#define AppName "Kerala PSC Coach"
#define AppExeName "KeralaPSCCoach.exe"
#ifndef AppVersion
#define AppVersion "2.0.0"
#endif
#ifndef FileVersion
#define FileVersion "2.0.0.0"
#endif

[Setup]
; Keep this AppId stable between releases. Inno Setup uses it to recognise
; an existing installation and upgrade it in place.
AppId={{B6465A70-8089-455C-B5F5-824EBB512C1C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Afzal Ashraf
DefaultDirName={localappdata}\Programs\Kerala PSC Coach
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\dist
OutputBaseFilename=KeralaPSCCoach-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#FileVersion}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent
