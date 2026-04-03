; installer.iss - LOGIPORT
; Inno Setup 6.x

#define AppName      "LOGIPORT"
#define AppVersion   "1.0.0"
#define AppPublisher "LOGIPORT"
#define AppURL       "https://github.com/ahmedsalih99/LOGIPORT-V1.0.0"
#define AppExeName   "LOGIPORT.exe"
#define AppID        "D7F057AA-B8F8-4B55-AAAE-A59D95268B23"
#define SourceDir    "dist\LOGIPORT"

[Setup]
AppId={{{#AppID}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=LOGIPORT_Setup_{#AppVersion}
SetupIconFile=icons\logo.ico
; Splash Screen
WizardImageFile=icons\logo.png
WizardSmallImageFile=icons\logo.png
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
; يسمح للمستخدم العادي بالتثبيت بدون admin
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
WizardResizable=no
CloseApplications=yes
CloseApplicationsFilter=*LOGIPORT*
RestartApplications=yes
; معلومات الإصدار
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Logistics Management System
VersionInfoProductName={#AppName}
VersionInfoCopyright=Copyright © 2026 {#AppPublisher}
; منع تشغيل نسختين من المثبّت في نفس الوقت
AppMutex=LOGIPORT_Setup_Mutex
; minimum Windows 10
MinVersion=10.0
; Uninstall
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}

[Languages]
Name: "arabic";  MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "startupicon"; Description: "Launch on Windows startup"; GroupDescription: "Options:"; Flags: unchecked

[Files]
; ملفات التطبيق الرئيسية
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; مجلدات البيانات مع صلاحيات كتابة كاملة للمستخدم
Name: "{userappdata}\LOGIPORT";                     Permissions: users-full
Name: "{userappdata}\LOGIPORT\logs";                Permissions: users-full
Name: "{userappdata}\LOGIPORT\backups";             Permissions: users-full
Name: "{userappdata}\LOGIPORT\documents";           Permissions: users-full
Name: "{userappdata}\LOGIPORT\documents\generated"; Permissions: users-full

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#AppExeName}"

[Registry]
; حفظ مسارات التثبيت
Root: HKCU; Subkey: "Software\{#AppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}";                     Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#AppName}"; ValueType: string; ValueName: "Version";     ValueData: "{#AppVersion}"
Root: HKCU; Subkey: "Software\{#AppName}"; ValueType: string; ValueName: "DataPath";    ValueData: "{userappdata}\LOGIPORT"
; تشغيل مع بدء Windows (اختياري)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Tasks: startupicon; Flags: uninsdeletevalue

[Run]
; تشغيل التطبيق بعد التثبيت
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\logs"

[Code]
// ──────────────────────────────────────────────────────────────────
// إلغاء تثبيت النسخة القديمة صامتاً قبل التثبيت الجديد
// ──────────────────────────────────────────────────────────────────
function InitializeSetup(): Boolean;
var
  UninstallString: String;
  ResultCode: Integer;
begin
  Result := True;
  // تحقق من HKCU أولاً (تثبيت بدون admin)
  if RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{' + '{#AppID}' + '}_is1',
    'UninstallString', UninstallString) then
  begin
    Exec(RemoveQuotes(UninstallString), '/SILENT /NORESTART', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
  end
  // تحقق من HKLM (تثبيت مع admin)
  else if RegQueryStringValue(HKLM,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{' + '{#AppID}' + '}_is1',
    'UninstallString', UninstallString) then
  begin
    Exec(RemoveQuotes(UninstallString), '/SILENT /NORESTART', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
  end;
end;

// ──────────────────────────────────────────────────────────────────
// التحقق من Visual C++ Redistributable (مطلوب لـ PySide6)
// ──────────────────────────────────────────────────────────────────
function VCRedistInstalled(): Boolean;
var
  Version: String;
begin
  // نتحقق من VC++ 2015-2022 Redistributable x64
  Result := RegQueryStringValue(HKLM,
    'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64',
    'Version', Version);
  if not Result then
    Result := RegKeyExists(HKLM,
      'SOFTWARE\Classes\Installer\Dependencies\VC,redist.x64,amd64,14.36,bundle');
end;

procedure InitializeWizard();
begin
  if not VCRedistInstalled() then
    MsgBox(
      'تنبيه: لم يُعثر على Visual C++ Redistributable 2015-2022.' + #13#10 +
      'Warning: Visual C++ Redistributable 2015-2022 not found.' + #13#10#13#10 +
      'قد لا يعمل التطبيق بشكل صحيح. يُنصح بتحميله من موقع Microsoft.' + #13#10 +
      'The application may not work correctly. Please download it from Microsoft.',
      mbInformation, MB_OK);
end;
