; installer.iss - LOGIPORT
; Inno Setup 6.x

#define AppName      "LOGIPORT"
#define AppVersion   "1.0.0"
#define AppPublisher "LOGIPORT"
#define AppURL       "https://github.com/ahmedsalih99/LOGIPORT-V1.0.0"
#define AppExeName   "LOGIPORT.exe"
#define SourceDir    "dist\LOGIPORT"

[Setup]
AppId={{D7F057AA-B8F8-4B55-AAAE-A59D95268B23}
AppName={#AppName}
AppVersion={#AppVersion}
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
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
; يسمح للمستخدم العادي بالتثبيت بدون admin — وإذا أراد admin يختار ذلك
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
WizardResizable=no
CloseApplications=yes
CloseApplicationsFilter=*LOGIPORT*
RestartApplications=yes
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
; منع تشغيل نسختين من المثبّت في نفس الوقت
AppMutex=LOGIPORT_Setup_Mutex

[Languages]
Name: "arabic";  MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
; ملفات التطبيق الرئيسية
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; إنشاء مجلد البيانات والسجلات مع صلاحيات كتابة للمستخدم
Name: "{userappdata}\LOGIPORT\logs"; Permissions: users-full
Name: "{userappdata}\LOGIPORT\backups"; Permissions: users-full
Name: "{userappdata}\LOGIPORT\documents"; Permissions: users-full

[Icons]
Name: "{group}\{#AppName}";            Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";      Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\logs"

[Registry]
Root: HKCU; Subkey: "Software\{#AppName}";                          ValueType: string; ValueName: "InstallPath"; ValueData: "{app}";          Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#AppName}";                          ValueType: string; ValueName: "Version";     ValueData: "{#AppVersion}"
Root: HKCU; Subkey: "Software\{#AppName}";                          ValueType: string; ValueName: "DataPath";    ValueData: "{userappdata}\LOGIPORT"

[Code]
// إذا كانت هناك نسخة قديمة مثبّتة — قم بإلغاء تثبيتها صامتاً قبل التثبيت الجديد
function InitializeSetup(): Boolean;
var
  UninstallString: String;
  ResultCode: Integer;
begin
  Result := True;
  if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{D7F057AA-B8F8-4B55-AAAE-A59D95268B23}_is1',
    'UninstallString', UninstallString) then
  begin
    Exec(RemoveQuotes(UninstallString), '/SILENT /NORESTART', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
  end;
end;
