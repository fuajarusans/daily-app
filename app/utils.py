"""Fungsi bantu: simpan upload, buat zip, deteksi dependency eksternal."""
from __future__ import annotations

import re
import shutil
import time
import uuid
import zipfile
from pathlib import Path
from typing import Optional

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


def find_libreoffice() -> Optional[str]:
    """Cari 'soffice' (LibreOffice) di PATH atau lokasi umum Windows/macOS/Linux."""
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


def find_ghostscript() -> Optional[str]:
    """Cari Ghostscript di PATH atau lokasi instalasi umum Windows.

    Setelah instal via winget, PATH proses yang sedang berjalan belum tentu
    ter-update, jadi kita juga memindai folder standar `C:\\Program Files\\gs\\`.
    """
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
        # Pilih versi tertinggi (urut mundur berdasarkan nama folder gs<versi>)
        candidates.sort(key=lambda p: p.as_posix(), reverse=True)
        return str(candidates[0])
    return None
