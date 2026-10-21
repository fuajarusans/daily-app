# -*- mode: python ; coding: utf-8 -*-
# Konfigurasi PyInstaller untuk Daily App (mode folder, tanpa jendela konsol).
# Jalankan lewat "Build Installer.bat" atau:
#   .venv\Scripts\python.exe -m PyInstaller packaging\daily_app.spec --noconfirm
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
)

ROOT = Path(SPECPATH).parent  # noqa: F821 (SPECPATH disediakan PyInstaller)
VERSION = re.search(r'__version__\s*=\s*"([^"]+)"', (ROOT / "app" / "version.py").read_text()).group(1)
NUMS = tuple(int(x) for x in (VERSION.split(".") + ["0", "0", "0"])[:4])

# Tool & desain invoice dimuat dinamis (pkgutil), uvicorn & rembg memilih modul lewat
# string, jadi semuanya didaftarkan eksplisit agar ikut terbungkus.
hiddenimports = (
    collect_submodules("tools")
    + collect_submodules("app")
    + collect_submodules("uvicorn")
    + collect_submodules("rembg")
    + ["webview.platforms.edgechromium", "webview.platforms.winforms", "multipart"]
)

datas = [
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "static"), "static"),
]
for pkg in ("rembg", "docx", "fpdf", "pdf2docx", "pymatting"):
    datas += collect_data_files(pkg)
# Beberapa paket membaca versinya sendiri lewat importlib.metadata saat diimpor
# (mis. pymatting, dipakai rembg). Tanpa metadata ini impornya gagal di exe.
for pkg in ("pymatting", "rembg", "pooch", "onnxruntime", "numba", "scikit-image", "fpdf2", "pdf2docx"):
    datas += copy_metadata(pkg)

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=NUMS, prodvers=NUMS),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "Fajar Santoso"),
            StringStruct("FileDescription", "Daily App"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "DailyApp"),
            StringStruct("LegalCopyright", "\u00a9 2026 Fajar Santoso. Lisensi AGPL-3.0."),
            StringStruct("OriginalFilename", "DailyApp.exe"),
            StringStruct("ProductName", "Daily App"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

a = Analysis(  # noqa: F821
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DailyApp",
    console=False,
    icon=str(ROOT / "daily.ico"),
    version=version_info,
    upx=False,
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    name="DailyApp",
    upx=False,
)
