r"""Konfigurasi terpusat aplikasi.

Semua path dan parameter penting didefinisikan di sini agar mudah diubah.

Dua mode:
- Pengembang (`python run.py`): semua folder ada di folder proyek, seperti biasa.
- Terpasang (exe hasil PyInstaller): template & static dibaca dari paket aplikasi,
  sedangkan data milik pengguna disimpan di %LOCALAPPDATA%\DailyApp agar aman saat
  aplikasi diperbarui atau di-uninstall.
"""
import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))

# Folder berisi templates/ dan static/ (di exe: folder _internal milik PyInstaller).
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))

# Folder milik pengguna: data permanen, file sementara, model AI, log.
# DAILYAPP_HOME (opsional) memindahkan folder ini, mis. untuk uji coba atau versi portable.
if os.environ.get("DAILYAPP_HOME"):
    USER_DIR = Path(os.environ["DAILYAPP_HOME"])
elif FROZEN:
    USER_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "DailyApp"
else:
    USER_DIR = BASE_DIR

# Folder penyimpanan sementara
STORAGE_DIR = USER_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"

# Folder data permanen (tidak ikut dibersihkan otomatis), mis. catatan & pengingat.
DATA_DIR = USER_DIR / "data"
NOTES_FILE = DATA_DIR / "notes.json"

# Folder model AI yang diunduh sekali (mis. LaMa untuk Hapus Watermark).
# Tidak ikut auto-cleanup; di-gitignore karena besar.
MODELS_DIR = USER_DIR / "models"

# Log aplikasi terpasang (tanpa jendela konsol, jadi error dicatat ke file).
LOG_DIR = USER_DIR / "logs"

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

# Batas total ukuran upload per proses tool (dicek di main.process_tool).
MAX_UPLOAD_BYTES = 200 * 1024 * 1024

# Catatan & Pengingat: default berapa hari sebelum jatuh tempo dianggap "akan datang".
REMINDER_DEFAULT_LEAD_DAYS = 7

# Kategori bawaan untuk Catatan & Pengingat. Cukup tambah/ubah di sini —
# dropdown form, chip filter, dan warna kartu otomatis menyesuaikan.
NOTE_CATEGORIES = [
    {"id": "umum",    "label": "Umum",    "emoji": "🗒️", "icon": "notes",     "color": "slate"},
    {"id": "tugas",   "label": "Tugas",   "emoji": "✅", "icon": "checkbox",  "color": "green"},
    {"id": "dokumen", "label": "Dokumen", "emoji": "📄", "icon": "file-text", "color": "blue"},
    {"id": "klien",   "label": "Klien",   "emoji": "👤", "icon": "user",      "color": "purple"},
    {"id": "jadwal",  "label": "Jadwal",  "emoji": "📅", "icon": "calendar",  "color": "amber"},
    {"id": "ide",     "label": "Ide",     "emoji": "💡", "icon": "bulb",      "color": "pink"},
]
DEFAULT_NOTE_CATEGORY = "umum"

# Invoice Generator: data permanen (brand, klien, invoice) + logo per brand.
INVOICES_FILE = DATA_DIR / "invoices.json"
INVOICE_ASSETS_DIR = DATA_DIR / "invoice_assets"

# Default awal untuk brand baru (bisa diubah per brand di tab Brand).
INVOICE_DEFAULT_PREFIX = "INV"        # nomor: 001/INV/X/2026
INVOICE_DEFAULT_DUE_DAYS = 14         # jatuh tempo = tanggal invoice + N hari
INVOICE_DEFAULT_TAX_RATE = 11         # PPN (%) saat diaktifkan
INVOICE_DEFAULT_DESIGN = "klasik"


def ensure_dirs() -> None:
    """Pastikan semua folder penyimpanan ada."""
    for d in (STORAGE_DIR, UPLOAD_DIR, OUTPUT_DIR, DATA_DIR, MODELS_DIR, INVOICE_ASSETS_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
