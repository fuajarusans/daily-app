; Skrip Inno Setup untuk installer Daily App.
; Dijalankan oleh "Build Installer.bat" setelah PyInstaller selesai, contoh manual:
;   ISCC.exe /DAppVersion=1.0.0 packaging\installer.iss
; Installer per-pengguna: tidak butuh hak admin, terpasang di
; %LOCALAPPDATA%\Programs\Daily App. Data pengguna ada di %LOCALAPPDATA%\DailyApp
; dan TIDAK dihapus saat uninstall.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
; AppId jangan diubah: dipakai Windows untuk mengenali versi lama saat update.
AppId={{4075EC59-5A4B-4942-8FB1-F5B29AEA5C5A}
AppName=Daily App
AppVersion={#AppVersion}
AppVerName=Daily App {#AppVersion}
AppPublisher=Fajar Santoso
AppCopyright=Hak cipta (c) 2026 Fajar Santoso. Lisensi AGPL-3.0.
LicenseFile=..\LICENSE
AppPublisherURL=https://github.com/fuajarusans/daily-app
DefaultDirName={autopf}\Daily App
DefaultGroupName=Daily App
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=DailyApp-Setup-{#AppVersion}
SetupIconFile=..\daily.ico
UninstallDisplayIcon={app}\DailyApp.exe
UninstallDisplayName=Daily App
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Cegah pemasangan saat Daily App masih berjalan (nama sama dengan MUTEX_NAME di desktop.py).
AppMutex=DailyAppSingleInstance
CloseApplications=yes

[Messages]
ButtonBack=< &Kembali
ButtonNext=&Lanjut >
ButtonInstall=&Pasang
ButtonCancel=Batal
ButtonYes=&Ya
ButtonNo=&Tidak
ButtonFinish=&Selesai
ButtonBrowse=&Telusuri...
WelcomeLabel1=Selamat datang di instalasi [name]
WelcomeLabel2=[name/ver] akan dipasang di komputer ini.%n%nData Anda (catatan, brand, invoice) disimpan terpisah dan tetap aman saat memperbarui versi.
WizardSelectDir=Pilih lokasi instalasi
SelectDirDesc=Di mana [name] akan dipasang?
SelectDirLabel3=[name] akan dipasang di folder berikut.
SelectDirBrowseLabel=Klik Lanjut untuk meneruskan, atau Telusuri untuk memilih folder lain.
DiskSpaceMBLabel=Butuh ruang kosong minimal [mb] MB.
WizardSelectTasks=Pilihan tambahan
SelectTasksDesc=Pilihan apa saja yang dijalankan?
SelectTasksLabel2=Pilih pilihan tambahan untuk [name], lalu klik Lanjut.
WizardReady=Siap dipasang
ReadyLabel1=[name] siap dipasang di komputer ini.
ReadyLabel2a=Klik Pasang untuk mulai, atau Kembali untuk mengubah pilihan.
ReadyMemoDir=Lokasi instalasi:
ReadyMemoTasks=Pilihan tambahan:
WizardPreparing=Menyiapkan instalasi
PreparingDesc=Menyiapkan pemasangan [name] di komputer ini.
WizardInstalling=Memasang
InstallingLabel=Mohon tunggu, [name] sedang dipasang.
FinishedHeadingLabel=Instalasi [name] selesai
FinishedLabelNoIcons=[name] sudah terpasang di komputer ini.
FinishedLabel=[name] sudah terpasang. Buka lewat shortcut di Desktop atau Start Menu.
RunEntryExec=Jalankan %1
ExitSetupTitle=Batalkan instalasi
ExitSetupMessage=Instalasi belum selesai. Jika dibatalkan sekarang, aplikasi tidak terpasang.%n%nBatalkan instalasi?
SetupAppRunningError=%1 sedang berjalan.%n%nTutup aplikasinya dulu, lalu klik OK untuk melanjutkan atau Batal untuk keluar.
UninstallAppRunningError=%1 sedang berjalan.%n%nTutup aplikasinya dulu, lalu klik OK untuk melanjutkan atau Batal untuk keluar.
ConfirmUninstall=Hapus %1 dari komputer ini?%n%nData Anda (catatan, brand, invoice) di folder AppData\Local\DailyApp tidak ikut terhapus.
UninstalledAll=%1 sudah dihapus dari komputer ini.
WizardLicense=Perjanjian lisensi
LicenseLabel=Baca informasi berikut sebelum melanjutkan.
LicenseLabel3=Daily App, hak cipta (c) 2026 Fajar Santoso, dibagikan dengan lisensi GNU AGPL-3.0 berikut (bahasa Inggris). Anda harus menyetujuinya untuk melanjutkan.
LicenseAccepted=Saya &menyetujui lisensi ini
LicenseNotAccepted=Saya &tidak menyetujui

[CustomMessages]
AdditionalIcons=Shortcut tambahan:
CreateDesktopIcon=Buat shortcut di &Desktop
LaunchProgram=Jalankan %1

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\DailyApp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\PANDUAN-PENERIMA.md"; DestDir: "{app}"; DestName: "Panduan Daily App.txt"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\NOTICE.md"; DestDir: "{app}"; DestName: "Hak Cipta dan Lisensi.txt"; Flags: ignoreversion

[InstallDelete]
; Bersihkan sisa versi lama agar modul yang sudah dihapus tidak tertinggal.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\Daily App"; Filename: "{app}\DailyApp.exe"
Name: "{group}\Panduan Daily App"; Filename: "{app}\Panduan Daily App.txt"
Name: "{group}\Hak Cipta dan Lisensi"; Filename: "{app}\Hak Cipta dan Lisensi.txt"
Name: "{group}\Hapus Daily App"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Daily App"; Filename: "{app}\DailyApp.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DailyApp.exe"; Description: "{cm:LaunchProgram,Daily App}"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2Key = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2Installed(): Boolean;
var
  Version: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\' + WebView2Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\' + WebView2Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\' + WebView2Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not WebView2Installed() then
    MsgBox('Microsoft Edge WebView2 Runtime belum terpasang di komputer ini.' + #13#10#13#10 +
           'Daily App tetap bisa dipasang dan akan terbuka di browser. Agar tampil sebagai ' +
           'jendela aplikasi, pasang WebView2 (gratis dari Microsoft):' + #13#10 +
           'https://developer.microsoft.com/microsoft-edge/webview2/', mbInformation, MB_OK);
end;
