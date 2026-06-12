"""Konfigurasi terpusat aplikasi.

Semua path dan parameter penting didefinisikan di sini agar mudah diubah.
"""
from pathlib import Path

# Root folder proyek (folder yang berisi run.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Folder penyimpanan sementara
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"

# Folder data PERMANEN (TIDAK ikut dibersihkan otomatis) — mis. catatan & pengingat.
DATA_DIR = BASE_DIR / "data"
NOTES_FILE = DATA_DIR / "notes.json"

# Folder model AI yang diunduh sekali (mis. LaMa untuk Hapus Watermark).
# Tidak ikut auto-cleanup; di-gitignore karena besar.
MODELS_DIR = BASE_DIR / "models"

# Folder template & static
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Konfigurasi server
HOST = "127.0.0.1"
PORT = 8000

# Berapa lama (detik) file hasil/upload disimpan sebelum dibersihkan otomatis.
# Default: 1 jam.
FILE_TTL_SECONDS = 60 * 60

# Interval (detik) pembersihan berkala berjalan di background.
CLEANUP_INTERVAL_SECONDS = 10 * 60  # tiap 10 menit

# Batas ukuran upload per request (byte). Default 200 MB.
MAX_UPLOAD_BYTES = 200 * 1024 * 1024

# Catatan & Pengingat: default berapa hari sebelum jatuh tempo dianggap "akan datang".
REMINDER_DEFAULT_LEAD_DAYS = 7

# Kategori bawaan untuk Catatan & Pengingat. Cukup tambah/ubah di sini —
# dropdown form, chip filter, dan warna kartu otomatis menyesuaikan.
NOTE_CATEGORIES = [
    {"id": "umum",    "label": "Umum",    "emoji": "🗒️", "color": "slate"},
    {"id": "tugas",   "label": "Tugas",   "emoji": "✅", "color": "green"},
    {"id": "dokumen", "label": "Dokumen", "emoji": "📄", "color": "blue"},
    {"id": "klien",   "label": "Klien",   "emoji": "👤", "color": "purple"},
    {"id": "jadwal",  "label": "Jadwal",  "emoji": "📅", "color": "amber"},
    {"id": "ide",     "label": "Ide",     "emoji": "💡", "color": "pink"},
]
DEFAULT_NOTE_CATEGORY = "umum"


def ensure_dirs() -> None:
    """Pastikan semua folder penyimpanan ada."""
    for d in (STORAGE_DIR, UPLOAD_DIR, OUTPUT_DIR, DATA_DIR, MODELS_DIR):
        d.mkdir(parents=True, exist_ok=True)
