[Setup]
AppId={{f7ba1f01-27ad-49d4-87af-1848bbf9bc40}
AppName={#ApplicationName}
AppVerName={cm:NameAndVersion,{#ApplicationName},{#ApplicationVersion}}
AppVersion={#ApplicationVersion}
VersionInfoVersion={#ApplicationVersion}
WizardStyle=modern
DefaultDirName={autopf}\{#ApplicationName}
DefaultGroupName={#ApplicationName}
UninstallDisplayIcon={app}\{#ApplicationName}.exe
Compression=lzma2/max
SolidCompression=yes
OutputDir=.\installer
OutputBaseFilename=AutoJimmy-v{#ApplicationVersion}-x64
; "ArchitecturesAllowed=x64" specifies that Setup cannot run on
; anything but x64.
ArchitecturesAllowed=x64
; "ArchitecturesInstallIn64BitMode=x64" requests that the install be
; done in "64-bit mode" on x64, meaning it should use the native
; 64-bit Program Files directory and the 64-bit view of the registry.
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\{#ApplicationName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Icons]
Name: "{group}\{#ApplicationName}"; Filename: "{app}\{#ApplicationName}.exe"
Name: "{group}\{cm:UninstallProgram,{#ApplicationName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#ApplicationName}"; Filename: "{app}\{#ApplicationName}.exe"; Tasks: desktopicon

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
    mres : integer;
begin
    case CurUninstallStep of usPostUninstall:
        begin
            mres := MsgBox('Do you want to remove user content?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2)

            if mres = IDYES then
                mres := MsgBox('Are you sure you want to delete all user content?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2);

            if mres = IDYES then
                DelTree(ExpandConstant('{userappdata}\{#ApplicationName}'), True, True, True);
       end;
   end;
end;