# 🧰 Daily App

Aplikasi utilitas internal yang berjalan **lokal** di komputer Anda. Berupa dashboard
web (diakses lewat browser di `http://localhost:8000`) berisi kumpulan *tools* harian
untuk konversi dan manipulasi file.

Tidak butuh internet untuk operasi sehari-hari (kecuali tool "Hapus Background" dan engine
**LaMa** pada "Hapus Watermark" — masing-masing mengunduh model sekali saat pemakaian
pertama), tidak di-deploy ke server.

> 📘 Mau langsung pakai? Lihat **[PANDUAN.md](PANDUAN.md)** untuk cara pemakaian
> harian dan cara update.

---

## ✨ Daftar Tools

| Tool | Fungsi | Library | Catatan |
|------|--------|---------|---------|
| 📄 PDF ke Word | `.pdf` → `.docx` | pdf2docx | — |
| 🗜️ Compress PDF | Perkecil ukuran PDF | pikepdf / Ghostscript | Metode "Maksimal" perlu Ghostscript |
| 📑 Office ke PDF | `.docx/.xlsx/.pptx` → `.pdf` | LibreOffice | **Wajib** LibreOffice terpasang |
| 🖼️ Resize / Compress Gambar | Ubah ukuran, kualitas, atau target ukuran file (KB) | Pillow | Mendukung batch; mode target: PNG→JPG |
| 🔄 Convert Format Gambar | PNG/JPG/WEBP/HEIC/… | Pillow + pillow-heif | Mendukung batch |
| ✂️ Hapus Background Gambar | Hapus latar otomatis (AI) | rembg | Unduh model ~170MB sekali (perlu internet) |
| 🧽 Hapus Watermark | Tandai area di kanvas → hapus (inpainting); engine OpenCV / LaMa (AI) | opencv-python-headless · onnxruntime | Halaman kanvas khusus (`/watermark`); LaMa unduh model ~208MB sekali |
| 🔳 Generate QR Code | Teks/URL → PNG | qrcode[pil] | — |

---

## 📝 Catatan & Pengingat

Selain tools pengolah file, ada fitur **Catatan & Pengingat** (menu **📝 Catatan** di
header atau kartu di dashboard) untuk to-do, tenggat tugas, dan **pengingat masa berlaku
dokumen**.

- Tiap catatan: judul, isi, **kategori** (Umum/Tugas/Dokumen/Klien/Jadwal/Ide), **tag**,
  **pin**, **status selesai**, dan **tanggal jatuh tempo** + *"ingatkan sejak H-…"* (mis.
  H-30 untuk dokumen). Saring cepat lewat **chip kategori** di atas daftar.
- Sorot warna otomatis: **merah** (lewat tempo), **oranye** (hari ini), **kuning** (akan datang).
- **Lencana** jumlah jatuh tempo muncul di header semua halaman.
- **Notifikasi browser**: klik **🔔 Aktifkan pengingat** sekali untuk memberi izin; pop-up
  muncul untuk catatan lewat tempo / jatuh tempo hari ini selama aplikasi terbuka
  (lokal, tanpa internet, tanpa dependency tambahan).

Data tersimpan permanen di **`data/notes.json`** (tidak ikut auto-cleanup). Daftar
**kategori** diatur terpusat di `app/config.py` (`NOTE_CATEGORIES`) — tambah/ubah di situ,
dropdown & chip filter otomatis menyesuaikan. Fitur ini adalah komponen tersendiri
(`app/notes_store.py` + `app/notes_routes.py`), **bukan** sebuah `Tool` di folder `tools/`
— sebab tools bersifat *stateless* (file masuk → keluar), sedangkan catatan harus
tersimpan permanen.

---

## 📋 Prasyarat

- **Python 3.10+** ([unduh](https://www.python.org/downloads/) — saat instal di Windows,
  centang *"Add Python to PATH"*).
- (Opsional, untuk tool tertentu) **LibreOffice** dan **Ghostscript** — lihat
  [Dependency Eksternal](#-dependency-eksternal).

---

## 🚀 Cara Install

1. Buka terminal (PowerShell) di folder proyek ini.

2. (Disarankan) Buat virtual environment agar rapi:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   > Jika muncul error *execution policy* di PowerShell, jalankan sekali:
   > `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

3. Install dependency Python:
   ```powershell
   pip install -r requirements.txt
   ```
   > Catatan: `rembg` dan `pdf2docx` cukup besar; instalasi pertama bisa beberapa menit.

---

## ▶️ Cara Menjalankan

```powershell
python run.py
```

Server menyala di `http://localhost:8000` dan browser akan **terbuka otomatis**.
Tekan `CTRL+C` di terminal untuk menghentikan.

---

## 🧪 Cara Menguji (langkah demi langkah)

1. Jalankan `python run.py`, dashboard terbuka.
2. **Generate QR Code** (paling cepat, tanpa dependency eksternal): buka tool, isi teks
   `https://contoh.com`, klik **Proses**, lalu **Unduh hasil** → harus berupa PNG QR.
3. **Resize Gambar**: buka tool, pilih satu gambar, set skala `50%`, **Proses** → unduh.
   Atau isi **Target ukuran file (KB)** (mis. `200`) untuk dikompres otomatis ke ukuran itu.
4. **PDF ke Word**: pilih satu `.pdf`, **Proses** → unduh `.docx`.
5. **Batch**: pada tool gambar, pilih beberapa file sekaligus → hasil otomatis berupa
   `.zip`.
6. **Office ke PDF**: bila LibreOffice belum terpasang, tool menampilkan badge
   *"perlu setup"* dan pesan cara instalasi (perilaku yang diharapkan).
7. **Hapus Watermark**: klik kartunya (membuka halaman kanvas), pilih gambar, **sapukan
   kuas** menutupi watermark, lalu **Proses** → muncul pratinjau *sebelum/sesudah* + unduh.
   Coba juga **Engine → LaMa (AI)** untuk hasil lebih halus (unduh model ~208MB sekali).

---

## 🔧 Dependency Eksternal

Dependency ini **bukan** paket pip; instal manual bila ingin memakai tool terkait.

### LibreOffice — wajib untuk "Office ke PDF"
- **Windows**: unduh di <https://www.libreoffice.org/download/>, instal seperti biasa.
  Aplikasi akan otomatis mencari `soffice.exe` di lokasi instalasi umum
  (`C:\Program Files\LibreOffice\program\`).
- **macOS**: instal LibreOffice.app ke folder Applications.
- **Linux**: `sudo apt install libreoffice` (atau paket distro Anda).

Jika setelah instal masih tidak terdeteksi, pastikan `soffice` ada di PATH, lalu jalankan
ulang `python run.py`.

### Ghostscript — opsional untuk "Compress PDF" metode Maksimal
Metode **Cepat** (pikepdf) selalu tersedia tanpa instalasi tambahan. Untuk hasil
kompresi lebih agresif (terutama PDF berisi banyak gambar), gunakan metode **Maksimal**
yang memerlukan Ghostscript:
- **Windows**: unduh di <https://ghostscript.com/releases/gsdnld.html> (pilih versi 64-bit).
  Aplikasi mencari `gswin64c`.
- **macOS**: `brew install ghostscript`
- **Linux**: `sudo apt install ghostscript`

---

## 📁 Struktur Folder

```
Daily App/
├── run.py                  # Entry point: start server + buka browser
├── requirements.txt        # Dependency Python
├── README.md
│
├── app/                    # Kode inti aplikasi
│   ├── main.py             # FastAPI: dashboard, halaman tool, proses, download
│   ├── registry.py         # ★ Tool registry + kontrak dasar `Tool`
│   ├── config.py           # Konfigurasi (port, folder, TTL cleanup)
│   ├── cleanup.py          # Pembersihan file sementara otomatis
│   ├── utils.py            # Helper (simpan upload, zip, deteksi dependency)
│   ├── notes_store.py      # ★ Penyimpanan Catatan & Pengingat (data/notes.json)
│   ├── notes_routes.py     # ★ Route halaman + API Catatan & Pengingat
│   └── watermark_routes.py # ★ Route halaman kustom Hapus Watermark (kanvas)
│
├── tools/                  # ★ Satu file = satu tool (auto-terdaftar)
│   ├── __init__.py         # Auto-import semua modul di folder ini
│   ├── pdf_to_word.py
│   ├── compress_pdf.py
│   ├── office_to_pdf.py
│   ├── image_resize.py
│   ├── image_convert.py
│   ├── remove_background.py
│   ├── generate_qr.py
│   ├── watermark_remove.py # Halaman kustom (custom_url) → /watermark
│   └── _lama.py            # Engine LaMa (ONNX) — bukan Tool (diawali _ = tak auto-import)
│
├── templates/              # HTML (Jinja2 + Tailwind via CDN)
│   ├── base.html
│   ├── dashboard.html      # Daftar tool — terisi OTOMATIS dari registry
│   ├── tool.html           # Halaman generik 1 tool (form dari metadata tool)
│   └── watermark.html      # Halaman kustom Hapus Watermark (editor kanvas)
│
├── static/
│   ├── app.js              # JS vanilla: upload, status, download
│   ├── watermark.js        # JS editor kanvas Hapus Watermark
│   ├── notes.js            # JS Catatan & Pengingat (CRUD + render)
│   ├── reminders.js        # JS lencana + notifikasi pengingat (semua halaman)
│   └── img/                # Logo & ikon (emblem.png, logo.png, favicon, …)
│
├── storage/                # File sementara (auto-cleanup setiap jam)
│   ├── uploads/
│   └── outputs/
│
├── data/                   # Data PERMANEN (TIDAK dibersihkan)
│   └── notes.json          # Catatan & pengingat
│
└── models/                 # Model AI diunduh sekali (lama_fp32.onnx ~208MB) — gitignored
```

---

## ➕ Cara Menambah Tool Baru

Arsitektur ini **modular berbasis registry**. Untuk menambah tool, Anda **cukup membuat
satu file** di folder `tools/` — dashboard akan otomatis menampilkannya. Tidak perlu
menyentuh kode dashboard, route, atau template.

### Langkah

1. Buat file baru, mis. `tools/contoh_uppercase.py`.
2. Definisikan subclass `Tool`, isi metadata, dan method `process()`.
3. Beri decorator `@register_tool`.
4. Jalankan ulang `python run.py`. Selesai.

### Contoh lengkap (template siap salin)

```python
"""Tool contoh: ubah isi file teks menjadi HURUF BESAR."""
from pathlib import Path

from app.registry import Tool, ToolError, register_tool


@register_tool
class UppercaseTool(Tool):
    id = "uppercase-text"                 # ID unik, URL-friendly
    name = "Teks ke HURUF BESAR"          # Nama tampil di dashboard
    description = "Ubah isi file .txt menjadi huruf kapital semua."
    icon = "🔠"                            # Emoji ikon
    accepted_extensions = [".txt"]        # [] berarti bebas / tanpa file
    supports_batch = True                 # True = boleh banyak file → hasil .zip
    requires_file = True                  # False bila tidak butuh upload (mis. QR)

    # Opsi form tambahan (deklaratif). Kosongkan bila tidak perlu.
    options = [
        {
            "name": "suffix",            # nama field → key di dict `options`
            "label": "Akhiran nama file",
            "type": "text",              # text | number | range | select | textarea | checkbox
            "default": "_UPPER",
        },
    ]

    # (Opsional) cek dependency eksternal. Kembalikan pesan bila belum siap.
    def check_dependencies(self):
        return None

    def process(self, input_paths, options, output_dir):
        """input_paths: list[Path] file upload
           options: dict nilai dari form
           output_dir: Path folder tujuan hasil
           return: list[Path] file hasil (>1 file → otomatis dibungkus .zip)"""
        suffix = options.get("suffix") or "_UPPER"
        results = []
        for src in input_paths:
            try:
                teks = src.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                raise ToolError(f"Gagal membaca '{src.name}': {e}")
            out = output_dir / f"{src.stem}{suffix}.txt"
            out.write_text(teks.upper(), encoding="utf-8")
            results.append(out)
        return results
```

### Skema `options` yang didukung

| `type` | Render UI | Tipe nilai diterima `process` |
|--------|-----------|-------------------------------|
| `text` | input teks | str |
| `number` | input angka | int/float |
| `range` | slider | int/float |
| `select` | dropdown (butuh `choices`) | str |
| `textarea` | kotak teks multi-baris | str |
| `checkbox` | centang | bool |

Untuk `select`, isi `choices` sebagai list `{"value": "...", "label": "..."}`.
Field umum lain: `default`, `min`, `max`, `placeholder`.

### Tips

- Gunakan `raise ToolError("pesan ramah")` untuk kegagalan yang pesannya **aman
  ditampilkan ke pengguna** (format salah, konversi gagal, dependency hilang).
- Error lain yang tidak terduga tetap ditangkap framework dan ditampilkan dengan aman.
- File di-`tools/` yang namanya diawali `_` (mis. `_helpers.py`) **tidak** di-auto-import,
  jadi cocok untuk modul bantu bersama.

### Tool dengan halaman kustom (UI sendiri)

Sebagian tool butuh antarmuka di luar form standar (mis. **kanvas** untuk menandai area).
Caranya: isi atribut **`custom_url`** pada kelas tool ke URL halaman Anda, lalu sediakan
route + template untuk URL itu. Kartu di dashboard otomatis menaut ke `custom_url` tersebut
(bukan ke `/tool/<id>`), sementara pemrosesan tetap bisa memakai endpoint standar
`/api/tool/<id>/process` — cukup kirim file + opsi dari halaman kustom Anda.

Contoh nyata: **Hapus Watermark** — `tools/watermark_remove.py` (`custom_url = "/watermark"`)
+ `app/watermark_routes.py` + `templates/watermark.html` + `static/watermark.js`. Halaman
kanvas mengirim **gambar + mask** ke `/api/tool/watermark-remove/process`.

---

## 🧹 Penyimpanan & Pembersihan

- File upload & hasil disimpan sementara di `storage/`.
- Pembersih otomatis menghapus file yang lebih tua dari **1 jam** (berjalan tiap 10 menit
  dan saat startup). Ubah di `app/config.py` (`FILE_TTL_SECONDS`).
- **Catatan & Pengingat** disimpan permanen di `data/notes.json` dan **tidak** pernah ikut
  dibersihkan. Untuk backup, cukup salin berkas itu.

---

## ❓ Troubleshooting

- **Browser tidak terbuka otomatis** → buka manual `http://localhost:8000`.
- **Port 8000 dipakai aplikasi lain** → ubah `PORT` di `app/config.py`.
- **"Office ke PDF" gagal / badge perlu setup** → pastikan LibreOffice terpasang & tidak
  ada file Office yang sedang dibuka aplikasi lain.
- **"Hapus Background" lama / gagal di pemakaian pertama** → butuh internet sekali untuk
  unduh model AI (~170MB). Setelah itu jalan offline.
- **HEIC tidak terbaca** → pastikan `pillow-heif` terpasang (`pip install pillow-heif`).
