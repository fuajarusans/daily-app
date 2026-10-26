"""Fungsi bantu: simpan upload, buat zip, deteksi dependency eksternal."""
from __future__ import annotations

import logging
import os
import re
import shutil
import sys
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional

from fastapi import UploadFile

from app import config


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    """Bersihkan nama file agar aman dipakai di filesystem."""
    name = Path(name).name  # buang komponen path apa pun
    name = _SAFE_NAME_RE.sub("_", name).strip("._")
    return name or "file"


def new_job_dir(base: Path) -> Path:
    """Buat sub-folder unik untuk satu job (agar file antar-request tidak campur)."""
    job_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    d = base / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


async def save_uploads(files: list[UploadFile], dest_dir: Path) -> list[Path]:
    """Simpan daftar UploadFile ke folder tujuan, kembalikan path-nya."""
    saved: list[Path] = []
    for f in files:
        if not f.filename:
            continue
        target = dest_dir / safe_filename(f.filename)
        # Hindari tabrakan nama dalam satu batch
        counter = 1
        while target.exists():
            target = dest_dir / f"{target.stem}_{counter}{target.suffix}"
            counter += 1
        with target.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(target)
    return saved


def make_zip(files: list[Path], dest_dir: Path, zip_name: str = "hasil.zip") -> Path:
    """Bungkus beberapa file menjadi satu .zip."""
    zip_path = dest_dir / safe_filename(zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.name)
    return zip_path


def find_executable(*candidates: str) -> Optional[str]:
    """Cari executable di PATH. Terima beberapa nama kandidat."""
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    return None


def _vendor_file(*parts: str) -> Optional[str]:
    """Program yang ikut dibundel installer (folder vendor), bila ada."""
    p = config.VENDOR_DIR.joinpath(*parts)
    return str(p) if p.is_file() else None


def find_libreoffice() -> Optional[str]:
    """Cari 'soffice': bawaan installer dulu, lalu PATH atau lokasi umum Windows/macOS/Linux."""
    bundled = _vendor_file("libreoffice", "program", "soffice.exe")
    if bundled:
        return bundled
    found = find_executable("soffice", "soffice.exe", "libreoffice")
    if found:
        return found
    common = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
        Path("/usr/bin/soffice"),
        Path("/usr/local/bin/soffice"),
    ]
    for p in common:
        if p.exists():
            return str(p)
    return None


def no_window() -> dict:
    """Argumen subprocess agar program konsol (Ghostscript, LibreOffice) tidak memunculkan
    jendela hitam saat dipanggil dari aplikasi desktop tanpa konsol."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW, "stdin": subprocess.DEVNULL}
    return {}


def _gs_version(exe: Path) -> tuple[int, ...]:
    """...\\gs10.07.1\\bin\\gswin64c.exe → (10, 7, 1); folder tak dikenal → ()."""
    m = re.match(r"gs(\d+(?:\.\d+)*)$", exe.parent.parent.name, re.IGNORECASE)
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def find_ghostscript() -> Optional[str]:
    """Cari Ghostscript: bawaan installer dulu, lalu PATH atau lokasi instalasi umum Windows.

    Setelah instal via winget, PATH proses yang sedang berjalan belum tentu
    ter-update, jadi kita juga memindai folder standar `C:\\Program Files\\gs\\`.
    """
    bundled = _vendor_file("ghostscript", "bin", "gswin64c.exe")
    if bundled:
        return bundled
    found = find_executable("gs", "gswin64c", "gswin64c.exe", "gswin32c", "gswin32c.exe")
    if found:
        return found
    # Fallback Windows: biasanya di C:\Program Files\gs\gs<versi>\bin\gswin64c.exe
    bases = [Path(r"C:\Program Files\gs"), Path(r"C:\Program Files (x86)\gs")]
    candidates: list[Path] = []
    for base in bases:
        if base.is_dir():
            candidates.extend(base.glob("gs*/bin/gswin64c.exe"))
            candidates.extend(base.glob("gs*/bin/gswin32c.exe"))
    if candidates:
        # Pilih versi tertinggi. Urut per angka, bukan teks: "gs9.56" > "gs10.07"
        # bila dibandingkan sebagai string.
        candidates.sort(key=_gs_version, reverse=True)
        return str(candidates[0])
    return None


def ghostscript_env(gs_exe: str) -> Optional[dict]:
    """Lingkungan untuk Ghostscript bundel: GS_LIB menunjuk ke foldernya sendiri agar
    Ghostscript lain yang terpasang (registry GS_LIB, versi berbeda) tidak ikut terbaca.
    File init sudah tertanam di gsdll64.dll."""
    if not gs_exe.startswith(str(config.VENDOR_DIR)):
        return None
    return {**os.environ, "GS_LIB": str(Path(gs_exe).parent)}


# --- LibreOffice: profil sendiri + pemanasan ------------------------------------------
_LO_READY_MARKER = ".dailyapp-siap"


def _short_path(path: Path) -> Path:
    """Nama pendek 8.3 Windows untuk path panjang (folder harus sudah ada)."""
    if sys.platform != "win32" or len(str(path)) <= 90:
        return path
    import ctypes
    buf = ctypes.create_unicode_buffer(1024)
    if ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, 1024):
        return Path(buf.value)
    return path


def libreoffice_profile_arg() -> str:
    """Argumen -env:UserInstallation ke profil Daily App.

    Profil terpisah membuat konversi tidak bentrok dengan LibreOffice yang sedang dibuka
    pengguna. Root profil harus pendek (< ~115 karakter): berkas terdalam di dalam profil
    menambah ~140 karakter, dan path > 260 karakter membuat soffice crash (0xC0000409).
    """
    config.LIBREOFFICE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return "-env:UserInstallation=" + _short_path(config.LIBREOFFICE_PROFILE_DIR.resolve()).as_uri()


# Satu konversi LibreOffice dalam satu waktu: konversi paralel pada profil yang sama gagal.
LIBREOFFICE_LOCK = threading.Lock()


def run_libreoffice_convert(soffice: str, src: Path, outdir: Path, fmt: str = "pdf",
                            timeout: int = 300) -> Optional[Path]:
    """Konversi satu file dengan LibreOffice headless; kembalikan path hasil atau None.

    Pada profil baru, konversi pertama kadang selesai tanpa menghasilkan file (rc 0),
    jadi dicoba sekali lagi bila hasilnya tidak ada.
    """
    out = outdir / f"{src.stem}.{fmt}"
    cmd = [soffice, libreoffice_profile_arg(), "--headless", "--norestore",
           "--convert-to", fmt, "--outdir", str(outdir), str(src)]
    with LIBREOFFICE_LOCK:
        for _ in range(2):
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout, **no_window())
            if out.exists():
                return out
    return None


def libreoffice_ready() -> bool:
    return (config.LIBREOFFICE_PROFILE_DIR / _LO_READY_MARKER).is_file()


def warm_libreoffice(attempts: int = 3) -> bool:
    """Siapkan profil LibreOffice dengan konversi kecil (dipanggil saat instal/start).

    Konversi pertama pada profil baru lambat (20-30 detik) dan kadang tidak menghasilkan
    file; setelah profil siap, konversi berikutnya 2-5 detik.
    """
    soffice = find_libreoffice()
    if not soffice:
        return False
    log = logging.getLogger(__name__)
    with tempfile.TemporaryDirectory(prefix="dailyapp-lo-") as tmp:
        src = Path(tmp) / "siap.txt"
        src.write_text("Daily App\n", encoding="utf-8")
        for i in range(attempts):
            try:
                if run_libreoffice_convert(soffice, src, Path(tmp), timeout=180):
                    (config.LIBREOFFICE_PROFILE_DIR / _LO_READY_MARKER).write_text(soffice, encoding="utf-8")
                    log.info("Profil LibreOffice siap (percobaan %d)", i + 1)
                    return True
            except (subprocess.SubprocessError, OSError):
                log.warning("Pemanasan LibreOffice gagal (percobaan %d)", i + 1, exc_info=True)
    return False


class IdleRelease:
    """Panggil `release` bila objek tidak dipakai selama `seconds` (mis. lepas model AI).

    Bungkus setiap pemakaian dengan `with idle.in_use():` — selama ada pemakaian aktif
    pewaktu berhenti, dan baru mulai menghitung setelah pemakaian terakhir selesai.
    """

    def __init__(self, seconds: float, release: Callable[[], None]) -> None:
        self._seconds = seconds
        self._release = release
        self._timer: Optional[threading.Timer] = None
        self._active = 0
        self._lock = threading.Lock()

    def _fire(self) -> None:
        with self._lock:
            if self._active:
                return
            self._timer = None
        self._release()

    @contextmanager
    def in_use(self):
        with self._lock:
            self._active += 1
            if self._timer:
                self._timer.cancel()
                self._timer = None
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1
                if self._active == 0:
                    self._timer = threading.Timer(self._seconds, self._fire)
                    self._timer.daemon = True
                    self._timer.start()
