"""Siapkan folder vendor/ untuk installer lengkap Daily App.

Isi vendor/ (sekitar 1 GB, di-gitignore) ikut dipasang di samping DailyApp.exe:
  libreoffice/   LibreOffice yang dipangkas (Office ke PDF) + font bawaannya + runtime VC++
  ghostscript/   gswin64c.exe + gsdll64.dll (kompresi PDF Maksimal) + runtime VC++
  models/        u2net.onnx (Hapus Background) + lama_fp32.onnx (Hapus Watermark LaMa)
  LICENSES/      teks lisensi komponen pihak ketiga
  manifest.json  versi, ukuran, dan checksum

Sumber: LibreOffice dan Ghostscript yang terpasang di komputer build (Program Files);
model dari cache lokal atau diunduh dari sumber resminya, lalu dicek checksum-nya.

Pemakaian (dari folder proyek):
    .venv\\Scripts\\python.exe packaging\\siapkan_vendor.py            # lewati bila sudah lengkap
    .venv\\Scripts\\python.exe packaging\\siapkan_vendor.py --paksa    # bangun ulang
    .venv\\Scripts\\python.exe packaging\\siapkan_vendor.py --uji      # plus uji konversi
"""
from __future__ import annotations

import argparse
import ctypes
import datetime
import fnmatch
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor"
PROGRAM_FILES = Path(os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles") or r"C:\Program Files")
SYSTEM32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
FONTS_DIR = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"

MODELS = {
    "u2net.onnx": {
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
        "md5": "60024c5c889badc19c04ad937298a77b",
        "lokal": [Path.home() / ".u2net" / "u2net.onnx"],
        "lisensi": "Apache-2.0 (U-2-Net, Xuebin Qin dkk.; didistribusikan lewat rembg)",
    },
    "lama_fp32.onnx": {
        "url": "https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx",
        "sha256": "1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6",
        "lokal": [Path(os.environ.get("LOCALAPPDATA", "")) / "DailyApp" / "models" / "lama_fp32.onnx",
                  ROOT / "models" / "lama_fp32.onnx"],
        "lisensi": "Apache-2.0 (LaMa, advimman/lama; ekspor ONNX Carve/LaMa-ONNX)",
    },
}

# Runtime Visual C++ 2015-2022 (x64) yang dibutuhkan LibreOffice dan Ghostscript; disalin
# ke samping program agar jalan di Windows yang belum memasang VC++ Redistributable.
VC_RUNTIME_LO = ["concrt140.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
                 "msvcp140_atomic_wait.dll", "msvcp140_codecvt_ids.dll",
                 "vcruntime140.dll", "vcruntime140_1.dll"]
VC_RUNTIME_GS = ["msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"]

# Bagian LibreOffice yang tidak dipakai untuk konversi headless ke PDF (sudah diuji:
# hasil PDF identik dengan instalasi penuh). Path relatif terhadap folder LibreOffice.
LO_SKIP_DIRS = ["help", "readmes", "share/extensions", "share/gallery", "share/template",
                "share/wizards", "share/xpdfimport", "program/classes", "program/python-core-*"]
LO_SKIP_FILES = ["program/xpdfimport.exe", "program/python*.dll", "program/python.exe",
                 "program/pyuno.pyd", "program/pythonloader*", "program/pythonscript.py",
                 "program/opencltest.exe", "program/update_service.exe", "program/updater.exe"]
LO_KEEP_ICONS = "images_colibre.zip"


def log(msg: str) -> None:
    print(msg, flush=True)


def file_hash(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def folder_size(path: Path) -> tuple[int, int]:
    total = count = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
            count += 1
    return total, count


def file_version(path: Path) -> str:
    """Versi produk dari resource versi berkas .exe Windows."""
    ver = ctypes.windll.version
    size = ver.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        return "?"
    buf = ctypes.create_string_buffer(size)
    ver.GetFileVersionInfoW(str(path), 0, size, buf)
    ptr, length = ctypes.c_void_p(), ctypes.c_uint()
    ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length))
    if not length.value:
        return "?"
    data = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32 * 13)).contents
    ms, ls = data[4], data[5]  # dwProductVersionMS/LS (VS_FIXEDFILEINFO)
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


# --- LibreOffice ------------------------------------------------------------------------
def _lo_ignore(src_root: Path):
    def ignore(directory: str, names: list[str]) -> set[str]:
        rel_dir = Path(directory).relative_to(src_root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        skipped = set()
        for name in names:
            rel = rel_dir + name
            if any(fnmatch.fnmatch(rel, pat) for pat in LO_SKIP_DIRS + LO_SKIP_FILES):
                skipped.add(name)
            elif rel_dir == "share/config/" and fnmatch.fnmatch(name, "images_*.zip") and name != LO_KEEP_ICONS:
                skipped.add(name)
        return skipped
    return ignore


def libreoffice_fonts_from_msi() -> list[str]:
    """Nama berkas font yang dipasang MSI LibreOffice ke C:\\Windows\\Fonts.

    Dibaca dari paket MSI LibreOffice yang disimpan Windows (C:\\Windows\\Installer). Font ini
    dibundel ke share\\fonts\\truetype; LibreOffice mendaftarkannya sendiri saat berjalan.
    """
    try:
        import msilib  # Python <= 3.12
        import winreg
    except ImportError:
        return []
    packages = []
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UserData\S-1-5-18\Products"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as products:
            for i in range(winreg.QueryInfoKey(products)[0]):
                code = winreg.EnumKey(products, i)
                try:
                    with winreg.OpenKey(products, code + r"\InstallProperties") as props:
                        name = winreg.QueryValueEx(props, "DisplayName")[0]
                        if str(name).startswith("LibreOffice"):
                            packages.append(winreg.QueryValueEx(props, "LocalPackage")[0])
                except OSError:
                    continue
    except OSError:
        return []
    for pkg in packages:
        if not Path(pkg).is_file():
            continue
        db = msilib.OpenDatabase(pkg, msilib.MSIDBOPEN_READONLY)
        view = db.OpenView("SELECT `File`.`FileName` FROM `File`, `Component` "
                           "WHERE `File`.`Component_` = `Component`.`Component` "
                           "AND `Component`.`Directory_` = 'FontsFolder'")
        view.Execute(None)
        names = []
        while True:
            rec = view.Fetch()
            if rec is None:
                break
            names.append(rec.GetString(1).split("|")[-1])  # "SHORT~1.TTF|NamaPanjang.ttf"
        view.Close()
        if names:
            return sorted(set(names))
    return []


def build_libreoffice(manifest: dict) -> None:
    src = PROGRAM_FILES / "LibreOffice"
    soffice = src / "program" / "soffice.exe"
    if not soffice.is_file():
        sys.exit("[ERROR] LibreOffice tidak ditemukan di " + str(src) +
                 ". Pasang LibreOffice di komputer build (winget install TheDocumentFoundation.LibreOffice).")
    dst = VENDOR / "libreoffice"
    log(f"LibreOffice {file_version(soffice)}: menyalin (dipangkas) dari {src} ...")
    shutil.copytree(src, dst, ignore=_lo_ignore(src))
    for dll in VC_RUNTIME_LO:
        if (SYSTEM32 / dll).is_file():
            shutil.copy2(SYSTEM32 / dll, dst / "program" / dll)
    fonts = libreoffice_fonts_from_msi()
    font_dir = dst / "share" / "fonts" / "truetype"
    font_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for name in fonts:
        if (FONTS_DIR / name).is_file():
            shutil.copy2(FONTS_DIR / name, font_dir / name)
            copied += 1
    log(f"  font bawaan LibreOffice: {copied} dari {len(fonts)} berkas")
    if copied == 0:
        # Tanpa font ini dokumen tetap terkonversi, tetapi font Carlito/Liberation/dll. diganti.
        sys.exit("[ERROR] Font bawaan LibreOffice tidak terbaca dari paket MSI-nya. Modul msilib hanya ada "
                 "di Python 3.12 ke bawah: buat .venv dengan Python 3.11/3.12, dan pasang LibreOffice "
                 "lewat installer MSI resminya (winget). vendor/ akan dibangun ulang pada percobaan berikutnya.")
    size, count = folder_size(dst)
    manifest["libreoffice"] = {"versi": file_version(soffice), "sumber": str(src), "font": copied,
                               "ukuran": size, "berkas": count,
                               "kode_sumber": "https://download.documentfoundation.org/libreoffice/src/"}


# --- Ghostscript ------------------------------------------------------------------------
def build_ghostscript(manifest: dict) -> None:
    # Urut per angka versi, bukan teks: "gs9.56.1" > "gs10.07.1" bila dibandingkan sebagai string.
    installs = sorted(glob.glob(str(PROGRAM_FILES / "gs" / "gs*" / "bin" / "gswin64c.exe")),
                      key=lambda p: tuple(int(x) for x in re.findall(r"\d+", Path(p).parent.parent.name)))
    if not installs:
        sys.exit("[ERROR] Ghostscript 64-bit tidak ditemukan di " + str(PROGRAM_FILES / "gs") +
                 ". Pasang Ghostscript di komputer build (winget install ArtifexSoftware.GhostScript).")
    exe = Path(installs[-1])
    version = exe.parent.parent.name.removeprefix("gs")
    dst = VENDOR / "ghostscript"
    (dst / "bin").mkdir(parents=True, exist_ok=True)
    log(f"Ghostscript {version}: menyalin gswin64c.exe + gsdll64.dll ...")
    for name in ("gswin64c.exe", "gsdll64.dll"):
        shutil.copy2(exe.parent / name, dst / "bin" / name)
    for dll in VC_RUNTIME_GS:
        if (SYSTEM32 / dll).is_file():
            shutil.copy2(SYSTEM32 / dll, dst / "bin" / dll)
    copying = exe.parent.parent / "doc" / "COPYING"
    if copying.is_file():
        shutil.copy2(copying, dst / "COPYING")
    size, count = folder_size(dst)
    manifest["ghostscript"] = {"versi": version, "ukuran": size, "berkas": count,
                               "kode_sumber": f"https://github.com/ArtifexSoftware/ghostpdl-downloads/releases"}


# --- Model AI ---------------------------------------------------------------------------
def _model_ok(path: Path, info: dict) -> bool:
    if not path.is_file():
        return False
    if "sha256" in info:
        return file_hash(path, "sha256") == info["sha256"]
    return file_hash(path, "md5") == info["md5"]


def _download(url: str, dest: Path) -> None:
    log(f"  mengunduh {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "DailyApp-build"})
    with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
        shutil.copyfileobj(resp, out, 1 << 20)
    os.replace(tmp, dest)


def build_models(manifest: dict) -> None:
    dst = VENDOR / "models"
    dst.mkdir(parents=True, exist_ok=True)
    manifest["model"] = {}
    for name, info in MODELS.items():
        target = dst / name
        source = next((p for p in info["lokal"] if _model_ok(p, info)), None)
        if source:
            log(f"Model {name}: dari {source}")
            shutil.copy2(source, target)
        else:
            _download(info["url"], target)
        if not _model_ok(target, info):
            sys.exit(f"[ERROR] Checksum {name} tidak cocok. Hapus vendor/models lalu ulangi.")
        manifest["model"][name] = {"ukuran": target.stat().st_size, "sumber": info["url"],
                                   "lisensi": info["lisensi"], "sha256": file_hash(target, "sha256")}


# --- Lisensi ----------------------------------------------------------------------------
def build_licenses() -> None:
    dst = VENDOR / "LICENSES"
    dst.mkdir(parents=True, exist_ok=True)
    # Teks lengkap Apache-2.0 (untuk model AI) diambil dari paket requests di venv.
    for lic in glob.glob(str(ROOT / ".venv" / "Lib" / "site-packages" / "requests-*.dist-info" / "**" / "*LICENSE*"),
                         recursive=True):
        if not Path(lic).is_file():
            continue
        text = Path(lic).read_text(encoding="utf-8", errors="replace")
        if "Apache License" in text and "Version 2.0" in text:
            (dst / "Apache-2.0.txt").write_text(text, encoding="utf-8")
            break
    (dst / "BACA.txt").write_text(
        "Komponen pihak ketiga di folder vendor (lihat juga 'Hak Cipta dan Lisensi.txt'):\n\n"
        "- libreoffice\\  LibreOffice, The Document Foundation. MPL-2.0 (LICENSE.html, NOTICE di folder\n"
        "  tersebut). Dipakai tanpa modifikasi kode; bantuan, kamus, galeri, Java, dan Python tidak\n"
        "  disertakan. Kode sumber: https://download.documentfoundation.org/libreoffice/src/\n"
        "- ghostscript\\  Ghostscript, Artifex Software. AGPL-3.0 (ghostscript\\COPYING). Kode sumber:\n"
        "  https://github.com/ArtifexSoftware/ghostpdl-downloads/releases\n"
        "- models\\u2net.onnx  U-2-Net (Qin dkk.), Apache-2.0 (Apache-2.0.txt).\n"
        "- models\\lama_fp32.onnx  LaMa (advimman/lama), ekspor ONNX Carve/LaMa-ONNX, Apache-2.0.\n"
        "- *.dll runtime Visual C++ 2015-2022, Microsoft (Visual C++ Redistributable).\n",
        encoding="utf-8")


def test_vendor() -> None:
    """Uji: Office ke PDF dengan profil baru (path pendek) dan kompresi Ghostscript."""
    soffice = VENDOR / "libreoffice" / "program" / "soffice.exe"
    gs = VENDOR / "ghostscript" / "bin" / "gswin64c.exe"
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW, "stdin": subprocess.DEVNULL, "capture_output": True}
    with tempfile.TemporaryDirectory(prefix="dv-") as tmp:  # %TEMP%: path pendek untuk profil
        tmp = Path(tmp)
        (tmp / "uji.txt").write_text("Uji Daily App\n", encoding="utf-8")
        profile = "-env:UserInstallation=" + (tmp / "p").as_uri()
        for attempt in range(3):
            subprocess.run([str(soffice), profile, "--headless", "--norestore", "--convert-to", "pdf",
                            "--outdir", str(tmp), str(tmp / "uji.txt")], timeout=300, **flags)
            if (tmp / "uji.pdf").is_file():
                break
        ok_lo = (tmp / "uji.pdf").is_file()
        log(f"Uji LibreOffice: {'OK' if ok_lo else 'GAGAL'} (percobaan {attempt + 1})")
        ok_gs = False
        if ok_lo:
            r = subprocess.run([str(gs), "-sDEVICE=pdfwrite", "-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dQUIET",
                                "-dBATCH", f"-sOutputFile={tmp / 'kecil.pdf'}", str(tmp / "uji.pdf")],
                               env={**os.environ, "GS_LIB": str(gs.parent)}, timeout=120, **flags)
            ok_gs = r.returncode == 0 and (tmp / "kecil.pdf").is_file()
        log(f"Uji Ghostscript: {'OK' if ok_gs else 'GAGAL'}")
    if not (ok_lo and ok_gs):
        sys.exit("[ERROR] Uji vendor gagal.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paksa", action="store_true", help="hapus dan bangun ulang vendor/")
    ap.add_argument("--uji", action="store_true", help="uji konversi setelah selesai")
    args = ap.parse_args()

    manifest_path = VENDOR / "manifest.json"
    if manifest_path.is_file() and not args.paksa:
        log("vendor/ sudah lengkap (manifest.json ada). Pakai --paksa untuk membangun ulang.")
        if args.uji:
            test_vendor()
        return 0
    if VENDOR.exists():
        log("Menghapus vendor/ lama ...")
        shutil.rmtree(VENDOR)
    VENDOR.mkdir()
    manifest: dict = {"dibuat": datetime.datetime.now().isoformat(timespec="seconds")}
    build_libreoffice(manifest)
    build_ghostscript(manifest)
    build_models(manifest)
    build_licenses()
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    size, count = folder_size(VENDOR)
    log(f"Selesai: vendor/ {size / 1048576:.0f} MB, {count} berkas")
    if args.uji:
        test_vendor()
    return 0


if __name__ == "__main__":
    sys.exit(main())
