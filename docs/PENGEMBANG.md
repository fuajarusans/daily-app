# Daily App · Dokumentasi Pengembang

Dokumen ini untuk pengembang (menjalankan dari kode sumber, menambah tool, membuat installer). Untuk pengguna, lihat [README](../README.md). Aplikasi berjalan **lokal** di komputer Anda. Berupa dashboard
web (diakses lewat browser di `http://localhost:8000`) berisi kumpulan *tools* harian
untuk konversi dan manipulasi file.

Tidak butuh internet untuk operasi sehari-hari (kecuali tool "Hapus Background" dan engine
**LaMa** pada "Hapus Watermark" — masing-masing mengunduh model sekali saat pemakaian
pertama), tidak di-deploy ke server.

> 📘 Mau langsung pakai? Lihat **[PANDUAN.md](PANDUAN.md)** untuk cara pemakaian
> harian dan cara update.

---

## ©️ Hak Cipta & Lisensi

Hak cipta © 2026 **Fajar Santoso** ([Instagram @fajar_snts](https://www.instagram.com/fajar_snts)).
Daily App dibagikan dengan lisensi **GNU AGPL-3.0** (lihat [LICENSE](../LICENSE)); detail hak cipta
dan daftar komponen pihak ketiga ada di [NOTICE.md](../NOTICE.md). AGPL dipilih karena installer
membawa komponen AGPL/GPL (PyMuPDF, libx265). Hak cipta kode tetap milik pemilik; siapa pun yang
membagikan ulang wajib menyertakan pemberitahuan ini dan kode sumbernya.

---

## 🎮 Tampilan

Tampilan bergaya **layar beranda konsol (PS5)**: Beranda berisi deretan tile (pilih dengan
mouse atau panah kiri/kanan, **Enter** membuka, **Esc** kembali), area sorotan untuk tile yang
difokus dengan latar yang berganti warna per alat, dan ringkasan pengingat & invoice dari data
asli. Tema biru-hitam dengan aksen biru PlayStation. Arah desain, palet, dial, dan alasan tiap keputusan ada di
**[DESIGN.md](../DESIGN.md)**; audit & laporan antislop ada di folder `anti-slop/`.

- Token warna: `static/theme.js` (palet Tailwind dipetakan ulang ke tema gelap).
- Gaya & motif: `static/console.css`; perilaku bersama (jam, suara, Esc): `static/console.js`;
  Beranda: `static/home.js`.
- Ikon: `static/vendor/tabler-sprite.svg` (Tabler, MIT). Di template: `{{ icon('eraser') }}`;
  di JS: `DailyIcon("eraser")`. Tool baru memilih ikonnya lewat atribut `glyph`.

---

## ✨ Daftar Tools

| Tool | Fungsi | Library | Catatan |
|------|--------|---------|---------|
| 📄 PDF ke Word | `.pdf` → `.docx` | pdf2docx | — |
| 🗜️ Compress PDF | Perkecil ukuran PDF | pikepdf / Ghostscript | Metode "Maksimal" perlu Ghostscript |
| 📑 Office ke PDF | `.docx/.xlsx/.pptx` → `.pdf` | LibreOffice | **Wajib** LibreOffice terpasang |
| 🖼️ Resize / Compress Gambar | Ubah ukuran, kualitas, atau target ukuran file (KB) | Pillow | Mendukung batch; mode target: PNG→JPG |
| 🔄 Convert Format Gambar | PNG/JPG/JFIF/WEBP/HEIC/… | Pillow + pillow-heif | Mendukung batch |
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

## 🧾 Invoice Generator

Fitur **Invoice Generator** (menu **🧾 Invoice** / kartu di dashboard, halaman `/invoice`)
membuat invoice PDF berbahasa Indonesia:

- **Multi-brand** — kelola beberapa brand/perusahaan sekaligus. Tiap brand punya nama,
  alamat, kontak, **NPWP opsional**, **logo sendiri**, beberapa **rekening bank**, **prefix
  nomor unik**, jatuh tempo & PPN default, catatan default, serta desain & warna default.
  Satu brand ditandai ⭐ default (otomatis terpilih untuk invoice baru). Data brand **tidak**
  di-snapshot: PDF selalu memakai data brand terbaru. Brand yang masih punya invoice tidak
  bisa dihapus.
- **Klien tersimpan** (dipakai bersama semua brand) — pilih dari dropdown saat membuat
  invoice; data klien disalin ke invoice sehingga invoice lama tidak berubah bila data
  klien diedit.
- **Nomor otomatis per brand** `001/INV/X/2026` (urut/prefix/bulan romawi/tahun; urutan
  terpisah tiap brand & reset tiap tahun), tetap bisa diedit; nomor ganda dalam satu brand
  ditolak.
- **Item dinamis**, **diskon opsional** (% / Rp), **PPN opsional**, format `Rp 1.500.000`,
  dan **terbilang** ("satu juta lima ratus ribu rupiah").
- **Riwayat** invoice: cari, saring per brand & status (belum lunas / lewat tempo / lunas), edit,
  duplikat, tandai lunas (PDF diberi cap **LUNAS**), hapus, pratinjau & unduh PDF.
- **10 desain PDF**: Klasik, Modern, Minimalis, Spreadsheet, Elegan, Korporat, Bold,
  Kreatif, Ringkas, Kop Surat — 5 di antaranya bisa diganti warna aksennya.

PDF dibuat dengan **fpdf2** (murni Python). Di Windows dipakai font Arial/Georgia/Segoe UI
bawaan sistem (mendukung Unicode); bila tidak ada, otomatis jatuh ke font inti PDF.
Data tersimpan permanen di **`data/invoices.json`** (`brands`, `default_brand_id`,
`clients`, `invoices`) + logo per brand di **`data/invoice_assets/logo_<brand-id>.png`**
(tidak ikut auto-cleanup, tidak ikut ke repo). Berkas format lama (satu `profile`) otomatis
dimigrasi menjadi brand pertama saat pertama dibaca — salinan aslinya disimpan sebagai
`data/invoices.backup-<waktu>.json`. Seperti Catatan, fitur ini komponen
tersendiri (`app/invoice_store.py` + `app/invoice_routes.py`), **bukan** `Tool`.

### Menambah desain invoice baru

Satu file = satu desain, auto-terdaftar (pola sama dengan `tools/`). Buat mis.
`app/invoice_designs/pastel.py`:

```python
from app.invoice_designs._base import (
    InvoiceDesign, footer_section, items_table, meta, party, register_design, tint,
)


@register_design
class Pastel(InvoiceDesign):
    id = "pastel"
    name = "Pastel"
    description = "Warna lembut."
    order = 11
    default_color = "#E58FB1"
    uses_accent = True          # warna aksen bisa diganti pengguna

    def render(self, d):
        c, a = d.ctx, d.ctx.accent
        d.font(26, "B", color=a)
        d.set_xy(d.l_margin, 15)
        d.cell(100, 12, "INVOICE")
        y1 = party(d, d.l_margin, 35, 95, "DITAGIHKAN KEPADA",
                   c.client.get("name", ""), c.client_lines())
        y2 = meta(d, d.right - 75, 35, 75, c.meta_rows())
        d.set_y(max(y1, y2) + 8)
        items_table(d, head_fill=tint(a, 0.8), borders="NONE", zebra=tint(a, 0.94))
        footer_section(d, totals_kw={"total_fill": a, "total_color": (255, 255, 255)})
```

Lalu tambahkan sketsa thumbnail-nya di `templates/invoice.html` (blok `#thumbs`,
`data-thumb="pastel"`) agar galeri menampilkan pratinjau. Jalankan ulang aplikasi.

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

## 🪟 Aplikasi Windows (installer untuk dibagikan)

Daily App bisa dibungkus menjadi installer Windows biasa (`DailyApp-Setup-<versi>.exe`)
yang terbuka sebagai **jendela aplikasi sendiri** (Edge WebView2), tanpa Python dan
tanpa internet.

**Membuat installer:** naikkan versi di `app/version.py`, lalu klik dua kali
**`Build Installer.bat`**. Hasilnya: `dist/installer/DailyApp-Setup-<versi>.exe`.
Butuh `pyinstaller` + `pywebview` (dipasang otomatis oleh skrip) dan **Inno Setup 6**
(`winget install --id JRSoftware.InnoSetup -e --source winget`).

| Hal | Mode pengembang (`python run.py`) | Aplikasi terpasang (`DailyApp.exe`) |
|---|---|---|
| Tampilan | Browser, `http://localhost:8000` | Jendela sendiri, port acak di 127.0.0.1 |
| Data (`data/`, `storage/`, `models/`) | Folder proyek | `%LOCALAPPDATA%\DailyApp\` (+ `logs/`) |
| Unduhan | Browser | Dialog **Simpan sebagai** |
| Pratinjau/buka PDF | Tab baru | Browser bawaan |

Komponen: `desktop.py` (entry point: server + jendela, cegah buka ganda, log, cadangan ke
browser bila WebView2 tak ada; `--server-only` untuk diagnosa), `packaging/daily_app.spec`
(PyInstaller, mode folder, tanpa konsol), `packaging/installer.iss` (Inno Setup: per-pengguna
tanpa admin, shortcut, uninstaller, data pengguna tidak dihapus), dan
`PANDUAN-PENERIMA.md` (ikut terpasang sebagai "Panduan Daily App").

Catatan: installer tidak ditandatangani sertifikat, jadi Windows SmartScreen menampilkan
peringatan (penerima klik **More info → Run anyway**). LibreOffice & Ghostscript tidak ikut
installer. Notifikasi pop-up pengingat Catatan bisa tidak muncul di jendela aplikasi
(lencana jumlah tetap tampil).

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
8. **Invoice Generator**: buka **🧾 Invoice** → tab **Brand** → **➕ Tambah Brand**, isi nama
   usaha + rekening + prefix, klik **Contoh PDF** pada beberapa desain. Tambah brand kedua
   dengan prefix lain. Lalu tab **Invoice** → **➕ Buat Invoice**, pilih brand, isi klien +
   item, coba diskon/PPN → **👁️ Pratinjau PDF** → **💾 Simpan**. Ganti brand di form →
   nomor & desain ikut berubah. Coba **📋 duplikat** (nomor naik ke `002/…` di brand yang
   sama) dan **✅ tandai lunas** (PDF bercap LUNAS).

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
├── desktop.py              # Entry point aplikasi Windows (jendela WebView2)
├── Build Installer.bat     # Membuat installer Windows (PyInstaller + Inno Setup)
├── PANDUAN-PENERIMA.md     # Panduan singkat untuk penerima installer
├── DESIGN.md               # Arah desain (gaya konsol), palet, dial, alasan keputusan
├── anti-slop/              # Audit & laporan Delivery Gate antislop
├── packaging/              # daily_app.spec (PyInstaller) + installer.iss (Inno Setup)
├── requirements.txt        # Dependency Python
├── README.md
│
├── app/                    # Kode inti aplikasi
│   ├── main.py             # FastAPI: dashboard, halaman tool, proses, download
│   ├── registry.py         # ★ Tool registry + kontrak dasar `Tool`
│   ├── config.py           # Konfigurasi (port, folder, TTL cleanup, mode terpasang)
│   ├── version.py          # Nomor versi aplikasi (tampil di footer & installer)
│   ├── templating.py       # Objek template Jinja2 bersama
│   ├── cleanup.py          # Pembersihan file sementara otomatis
│   ├── utils.py            # Helper (simpan upload, zip, deteksi dependency)
│   ├── notes_store.py      # ★ Penyimpanan Catatan & Pengingat (data/notes.json)
│   ├── notes_routes.py     # ★ Route halaman + API Catatan & Pengingat
│   ├── invoice_store.py    # ★ Penyimpanan Invoice (brand, klien, invoice, penomoran, migrasi)
│   ├── invoice_routes.py   # ★ Route halaman + API Invoice Generator (brand, logo, PDF)
│   ├── invoice_format.py   # Format Rupiah, tanggal Indonesia, terbilang, romawi
│   ├── invoice_designs/    # ★ Satu file = satu desain PDF invoice (auto-terdaftar)
│   │   ├── _base.py        #   Kanvas fpdf2 + helper blok (tabel, total, terbilang, …)
│   │   └── klasik.py …     #   10 desain: klasik, modern, minimalis, spreadsheet, elegan,
│   │                       #   korporat, bold, kreatif, ringkas, kop_surat
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
│   ├── watermark.html      # Halaman kustom Hapus Watermark (editor kanvas)
│   └── invoice.html        # Halaman Invoice Generator (+ sketsa thumbnail desain)
│
├── static/
│   ├── app.js              # JS vanilla: upload, status, download
│   ├── watermark.js        # JS editor kanvas Hapus Watermark
│   ├── notes.js            # JS Catatan & Pengingat (CRUD + render)
│   ├── invoice.js          # JS Invoice Generator (form, kalkulasi live, klien, brand)
│   ├── theme.js            # Token warna tema konsol (konfigurasi Tailwind)
│   ├── console.css         # Gaya tema konsol: rail tile, cincin fokus, ikon
│   ├── console.js          # Jam, suara navigasi opsional, Esc ke Beranda, DailyIcon()
│   ├── home.js             # Beranda: navigasi rail, sorotan, ringkasan
│   ├── vendor/             # Tailwind 3.4.17 + sprite ikon Tabler (lokal, offline)
│   ├── reminders.js        # JS lencana + notifikasi pengingat (semua halaman)
│   └── img/                # Logo & ikon (emblem.png, logo.png, favicon, …)
│
├── storage/                # File sementara (auto-cleanup setiap jam)
│   ├── uploads/
│   └── outputs/
│
├── data/                   # Data PERMANEN (TIDAK dibersihkan)
│   ├── notes.json          # Catatan & pengingat
│   ├── invoices.json       # Brand, klien, & invoice
│   └── invoice_assets/     # Logo tiap brand (logo_<brand-id>.png)
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
    icon = "🔠"                            # Emoji (cadangan, tidak tampil di UI)
    glyph = "file-text"                   # Ikon tile Beranda (nama simbol di tabler-sprite.svg)
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
- **Invoice** (brand, klien, invoice) disimpan permanen di `data/invoices.json` + logo brand di
  `data/invoice_assets/`. PDF dibuat saat diminta (tidak disimpan). Backup: salin folder `data/`.

---

## ❓ Troubleshooting

- **Browser tidak terbuka otomatis** → buka manual `http://localhost:8000`.
- **Port 8000 dipakai aplikasi lain** → ubah `PORT` di `app/config.py`.
- **"Office ke PDF" gagal / badge perlu setup** → pastikan LibreOffice terpasang & tidak
  ada file Office yang sedang dibuka aplikasi lain.
- **"Hapus Background" lama / gagal di pemakaian pertama** → butuh internet sekali untuk
  unduh model AI (~170MB). Setelah itu jalan offline.
- **HEIC tidak terbaca** → pastikan `pillow-heif` terpasang (`pip install pillow-heif`).
