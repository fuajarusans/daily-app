# Daily App · Dokumentasi Pengembang

Dokumen ini untuk pengembang (menjalankan dari kode sumber, menambah tool, membuat installer). Untuk pengguna, lihat [README](../README.md). Aplikasi berjalan **lokal** di komputer Anda. Berupa dashboard
web (diakses lewat browser di `http://localhost:8000`) berisi kumpulan *tools* harian
untuk konversi dan manipulasi file.

Tidak butuh internet dan tidak di-deploy ke server. Installer Windows menyertakan LibreOffice,
Ghostscript, dan model AI (folder `vendor/`). Di mode pengembang tanpa `vendor/`, dipakai
LibreOffice/Ghostscript yang terpasang, dan model AI diunduh sekali saat pemakaian pertama.

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
| 🗜️ Compress PDF | Perkecil ukuran PDF | pikepdf / Ghostscript | Ghostscript (metode "Maksimal") ikut installer |
| 📑 Office ke PDF | `.docx/.xlsx/.pptx` → `.pdf` | LibreOffice | LibreOffice ikut installer; profil sendiri, satu konversi per waktu |
| 🖼️ Resize / Compress Gambar | Ubah ukuran, kualitas, atau target ukuran file (KB) | Pillow | Mendukung batch; mode target: PNG→JPG |
| 🔄 Convert Format Gambar | PNG/JPG/JFIF/WEBP/HEIC/… | Pillow + pillow-heif | Mendukung batch |
| ✂️ Hapus Background Gambar | Hapus latar otomatis (AI) | rembg 2.0.75 (u2net) | Model ikut installer; sesi dipakai ulang & dilepas saat menganggur |
| 🧽 Hapus Watermark | Tandai area di kanvas → hapus (inpainting); engine OpenCV / LaMa (AI) | opencv-python-headless · onnxruntime | Halaman kanvas khusus (`/watermark`); model LaMa ikut installer |
| 🔳 Generate QR Code | Teks/URL → PNG | qrcode[pil] | — |

---

## 📝 Catatan & Pengingat

Selain tools pengolah file, ada fitur **Catatan & Pengingat** (menu **📝 Catatan** di
header atau kartu di dashboard) untuk to-do, tenggat tugas, dan **pengingat masa berlaku
dokumen**.

- Tiap catatan: judul, isi, **kategori** (Umum/Tugas/Dokumen/Klien/Jadwal/Ide), **tag**,
  **pin**, **status selesai**, dan **tanggal jatuh tempo** + *"ingatkan sejak H-…"* (mis.
  H-30 untuk dokumen). Saring cepat lewat **chip kategori** di atas daftar.
- **Checklist** (1.4): daftar datar `checklist: [{id, text, done, priority, level}]`; sub-item =
  `level: 1` yang mengikuti item `level: 0` di atasnya (maks. 1 tingkat). Diubah per item lewat
  `POST /api/notes/<id>/checklist {"ops": [...]}` (`add`, `set`, `remove`, `move`, `clear_done`)
  yang diterapkan server pada daftar terbaru di bawah lock, jadi edit dari sticky dan halaman
  Catatan tidak saling menimpa. Tampilan + kendali dipakai bersama di `static/checklist.js`
  (keyboard: Enter, Tab/Shift+Tab, Alt+↑/↓, Backspace; pegangan: klik = menu pindah, seret =
  pindah langsung). Teks diketik dikirim setelah jeda 600 ms; yang belum terkirim (dan isi kolom
  "Tambah item") ikut dikirim saat kartu digambar ulang, halaman ditutup, atau sticky ditutup.
- **Prioritas** `priority` (tinggi/sedang/rendah, `NOTE_PRIORITIES`) ikut urutan daftar di dalam
  status yang sama. Hanya "tinggi" berwarna (ungu): merah/kuning/hijau khusus status tenggat.
- **Tugas berulang** `recurrence` (harian/mingguan/bulanan, `NOTE_RECURRENCES`): `PUT {done: true}`
  memajukan `due` (`notes_store.next_due`, bulanan memakai tanggal acuan `recur_day`), mereset
  centang checklist, dan respons berisi `recurred: true`. Jarak pengingat dibatasi < periode.
  Klien mengirim `expect_due` (tenggat yang terlihat) dan server tidak memajukan dua kali dalam
  3 detik, jadi klik ganda atau tampilan basi tidak melompati satu periode.
- **Arsip** `archived` + `archived_at`: tidak ikut daftar, hitungan, pengingat, Beranda, maupun
  pemulihan sticky saat start (`GET /api/notes` mengembalikan `archived` terpisah).
- **Urungkan**: hapus, arsipkan, dan selesai-berulang disimpan sementara di memori (60 detik,
  `NOTE_UNDO_SECONDS`); `POST /api/notes/<id>/undo` mengembalikannya (hapus: catatan utuh + status
  sticky; lainnya: hanya kolom yang diubah, jadi edit sesudahnya tidak ikut hilang).
- Kolom baru diisi bawaannya saat dibaca (`_annotate`), tanpa migrasi; `notes.json` tetap list.
  Penulis membaca berkas dengan `strict=True` (gagal baca = error, bukan daftar kosong), dan
  `notes.json` yang rusak disalin dulu ke `notes.rusak-<waktu>.json`.
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

### Sticky note di desktop (aplikasi Windows)

Di jendela aplikasi, kartu catatan bisa diseret keluar jendela (atau klik ikon catatan di
kartu) menjadi **sticky note**: jendela kecil tanpa bingkai yang memuat `/sticky/<id>`.

- `app/desktop_shell.py`: jendela utama, sticky, ikon tray, single-instance. API untuk JS
  lewat `window.pywebview.api` (`sticky_open`, `sticky_tear`, `sticky_close`,
  `sticky_set_on_top`, `sticky_resize`, `open_stickies`, `show_main`).
- `app/sticky_store.py`: posisi, ukuran, warna, "selalu di atas", dan status terbuka per catatan
  di `data/stickies.json` (terpisah dari `notes.json` agar menggeser sticky tidak mengubah
  `updated_at` catatan).
- `templates/sticky.html` + `static/sticky.js` + `static/sticky.css`: halaman mandiri tanpa
  Tailwind (tiap sticky = satu proses WebView2, ±30–50 MB). Simpan otomatis, sinkron dengan
  halaman Catatan lewat `BroadcastChannel("dailyapp-notes")` (pesan `changed`, `deleted`,
  `archived`, `sticky`; `reminders.js` ikut mendengar untuk memperbarui lencana). Checklist
  memakai `static/checklist.js` yang sama dengan halaman Catatan; teks item yang belum terkirim
  ikut disimpan `stickyFlushSync()` saat Alt+F4 atau Keluar dari tray.
- Menutup jendela utama saat masih ada sticky: aplikasi tetap jalan di tray. `desktop.py --startup`
  (shortcut Startup dari installer) memulihkan sticky saat Windows menyala, dan langsung keluar
  bila tidak ada sticky. Membuka Daily App lagi menampilkan jendela yang sudah berjalan
  (event `DailyAppShowMain`).
- Di mode pengembang (`python run.py`, browser) fitur sticky disembunyikan.

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

- **Python 3.11 atau 3.12, 64-bit** ([unduh](https://www.python.org/downloads/) — saat instal di
  Windows, centang *"Add Python to PATH"*). `rembg==2.0.75` butuh Python ≥ 3.11, dan
  `packaging/siapkan_vendor.py` membaca font LibreOffice lewat modul `msilib`, yang dihapus di
  Python 3.13 (build berhenti dengan pesan galat bila font tidak terbaca).
- **LibreOffice** dan **Ghostscript** terpasang di komputer pengembang: dipakai langsung di mode
  pengembang, dan disalin ke `vendor/` saat membuat installer. Lihat
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
**`Build Installer.bat`**. Hasilnya: `dist/installer/DailyApp-Setup-<versi>.exe` (±615 MB,
build 15–25 menit). Butuh `.venv` dengan Python 3.11/3.12, `pyinstaller` + `pywebview` (dipasang otomatis oleh skrip),
**Inno Setup 6** (`winget install --id JRSoftware.InnoSetup -e --source winget`), serta
LibreOffice dan Ghostscript 64-bit terpasang di komputer build.

Langkah 2 skrip menjalankan `packaging/siapkan_vendor.py`, yang membuat folder `vendor/`
(±900 MB, di-gitignore) satu kali:
- `vendor/libreoffice/`: salinan LibreOffice yang dipangkas (tanpa bantuan, kamus, galeri,
  Java, Python), font bawaannya (dibaca dari paket MSI LibreOffice), dan DLL runtime VC++.
- `vendor/ghostscript/`: `bin/` (`gswin64c.exe`, `gsdll64.dll` dengan file init tertanam, DLL
  runtime VC++) dan `COPYING`.
- `vendor/models/`: `u2net.onnx` dan `lama_fp32.onnx`, dicek checksum-nya.
- `vendor/LICENSES/`, `vendor/manifest.json` (versi, ukuran, checksum).

Jalankan `.venv\Scripts\python.exe packaging\siapkan_vendor.py --paksa --uji` untuk membangun
ulang (mis. setelah memperbarui LibreOffice) sekaligus menguji konversinya. Saat instalasi,
installer menjalankan `DailyApp.exe --warmup` untuk menyiapkan profil LibreOffice.

| Hal | Mode pengembang (`python run.py`) | Aplikasi terpasang (`DailyApp.exe`) |
|---|---|---|
| Tampilan | Browser, `http://localhost:8000` | Jendela sendiri, port 47815 di 127.0.0.1 (acak bila terpakai) |
| Data (`data/`, `storage/`, `models/`) | Folder proyek (+ profil LibreOffice `lo/`, profil WebView2 `webview/` saat `python desktop.py`) | `%LOCALAPPDATA%\DailyApp\` (+ `logs/`, profil LibreOffice `lo/`, profil WebView2 `webview/`) |
| LibreOffice, Ghostscript, model AI | `vendor/` bila ada, selain itu yang terpasang/diunduh | `vendor/` di samping `DailyApp.exe` |
| Unduhan | Browser | Dialog **Simpan sebagai** |
| Pratinjau/buka PDF | Tab baru | Browser bawaan |

Komponen: `desktop.py` (entry point: server + jendela lewat `app/desktop_shell.py`, cegah buka
ganda, log, cadangan ke browser bila WebView2 tak ada; `--server-only` untuk diagnosa,
`--startup` untuk sticky saat Windows menyala, `--warmup` untuk installer), `packaging/daily_app.spec`
(PyInstaller, mode folder, tanpa konsol), `packaging/installer.iss` (Inno Setup: per-pengguna
tanpa admin, shortcut, uninstaller, data pengguna tidak dihapus), dan
`PANDUAN-PENERIMA.md` (ikut terpasang sebagai "Panduan Daily App").

Catatan: installer tidak ditandatangani sertifikat, jadi Windows SmartScreen menampilkan
peringatan (penerima klik **More info → Run anyway**). Notifikasi pop-up pengingat Catatan bisa
tidak muncul di jendela aplikasi (lencana jumlah tetap tampil).

Memori (diukur di i5-7200U, RAM 12 GB): aplikasi diam ±380 MB; tiap sticky +30–50 MB; Office
ke PDF +100–370 MB sementara (proses LibreOffice); Hapus Background dan LaMa memakai arena
onnxruntime nonaktif dan dilepas setelah 10 menit menganggur (`AI_IDLE_RELEASE_SECONDS`).

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
6. **Office ke PDF**: pilih `.docx`, **Proses** → unduh PDF. Bila LibreOffice tidak ada (tanpa
   `vendor/` dan tanpa instalasi), tool menampilkan badge *"perlu setup"* (perilaku yang diharapkan).
7. **Hapus Watermark**: klik kartunya (membuka halaman kanvas), pilih gambar, **sapukan
   kuas** menutupi watermark, lalu **Proses** → muncul pratinjau *sebelum/sesudah* + unduh.
   Coba juga **Engine → LaMa (AI)** untuk hasil lebih halus (pemakaian pertama memuat model 1–2 menit).
8. **Invoice Generator**: buka **🧾 Invoice** → tab **Brand** → **➕ Tambah Brand**, isi nama
   usaha + rekening + prefix, klik **Contoh PDF** pada beberapa desain. Tambah brand kedua
   dengan prefix lain. Lalu tab **Invoice** → **➕ Buat Invoice**, pilih brand, isi klien +
   item, coba diskon/PPN → **👁️ Pratinjau PDF** → **💾 Simpan**. Ganti brand di form →
   nomor & desain ikut berubah. Coba **📋 duplikat** (nomor naik ke `002/…` di brand yang
   sama) dan **✅ tandai lunas** (PDF bercap LUNAS).
9. **Sticky note** (jalankan `python desktop.py`, bukan `run.py`; butuh `pywebview`, sudah ada di
   `requirements.txt` untuk Windows): di **Catatan**, seret kartu (pegangan ⋮⋮ di samping judul)
   keluar jendela → sticky muncul di bawah kursor. Edit isinya → halaman Catatan ikut berubah.
   Tutup jendela utama → sticky tetap ada, ikon Daily App di tray. Jalankan `python desktop.py`
   lagi → jendela utama muncul kembali. Keluar lewat tray, lalu `python desktop.py --startup` →
   hanya sticky yang muncul.
10. **Checklist, prioritas, berulang, arsip** (pakai data uji: set `DAILYAPP_HOME` ke folder
    kosong agar `data/` Anda tidak tersentuh): buat catatan dengan beberapa baris checklist (baris
    berawalan spasi = sub-item), prioritas Tinggi, dan Ulangi Mingguan. Di kartu: centang item,
    Enter/Tab/Alt+↑ di item, seret item lewat pegangannya. Centang semua → muncul tawaran
    **Tandai selesai**. Klik **Selesai** → tenggat maju 7 hari + toast **Urungkan**. Coba
    **Arsipkan** dan **Hapus**, lalu **Urungkan** (atau Ctrl+Z). Di sticky, centang item →
    kartu di halaman Catatan ikut berubah.

---

## 🔧 Dependency Eksternal

Program ini **bukan** paket pip. Installer menyertakan semuanya lewat `vendor/`; urutan
pencarian di `app/utils.py`: `vendor/` → PATH → lokasi instalasi umum.

### LibreOffice — untuk "Office ke PDF"
- **Windows**: `winget install TheDocumentFoundation.LibreOffice` (atau unduh di
  <https://www.libreoffice.org/download/>). Dibutuhkan juga untuk membuat `vendor/`.
- **macOS**: instal LibreOffice.app ke folder Applications. **Linux**: `sudo apt install libreoffice`.
- Daily App memakai profil LibreOffice sendiri (`-env:UserInstallation`, folder `lo/` di data
  pengguna, path pendek karena path panjang membuat soffice crash) dan menjalankan satu
  konversi per waktu (konversi paralel pada profil yang sama gagal).

### Ghostscript — untuk "Compress PDF" metode Maksimal
Metode **Cepat** (pikepdf) selalu tersedia. Metode **Maksimal** memerlukan Ghostscript:
- **Windows**: `winget install ArtifexSoftware.GhostScript` (versi 64-bit; dibutuhkan juga untuk
  membuat `vendor/`). **macOS**: `brew install ghostscript`. **Linux**: `sudo apt install ghostscript`.
- Ghostscript bawaan dijalankan dengan `GS_LIB` menunjuk ke foldernya sendiri agar tidak membaca
  file init dari Ghostscript lain yang terpasang.

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
├── packaging/              # daily_app.spec (PyInstaller), installer.iss (Inno Setup),
│                           # siapkan_vendor.py (isi folder vendor/)
├── vendor/                 # LibreOffice, Ghostscript, model AI untuk installer — gitignored
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
│   ├── notes_routes.py     # ★ Route halaman + API Catatan & Pengingat (+ halaman sticky)
│   ├── sticky_store.py     # Status sticky note di desktop (data/stickies.json)
│   ├── desktop_shell.py    # Jendela desktop: utama, sticky, tray, single-instance
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
├── templates/              # HTML (Jinja2 + Tailwind lokal dari static/vendor/)
│   ├── base.html
│   ├── dashboard.html      # Daftar tool — terisi OTOMATIS dari registry
│   ├── tool.html           # Halaman generik 1 tool (form dari metadata tool)
│   ├── watermark.html      # Halaman kustom Hapus Watermark (editor kanvas)
│   ├── sticky.html         # Isi jendela sticky note (mandiri, tanpa base.html)
│   └── invoice.html        # Halaman Invoice Generator (+ sketsa thumbnail desain)
│
├── static/
│   ├── app.js              # JS vanilla: upload, status, download
│   ├── watermark.js        # JS editor kanvas Hapus Watermark
│   ├── notes.js            # JS Catatan & Pengingat (CRUD + render + seret jadi sticky, arsip, urungkan)
│   ├── checklist.js        # Checklist di kartu & sticky (tampilan, keyboard, seret, operasi per item)
│   ├── sticky.js           # JS + CSS jendela sticky note (sticky.css)
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
│   ├── stickies.json       # Posisi/warna sticky note di desktop
│   ├── invoices.json       # Brand, klien, & invoice
│   └── invoice_assets/     # Logo tiap brand (logo_<brand-id>.png)
│
├── lo/                     # Profil LibreOffice milik Daily App — gitignored
│
└── models/                 # Model AI unduhan mode pengembang tanpa vendor/ — gitignored
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
- **"Office ke PDF" gagal / badge perlu setup** → pasang LibreOffice (dipakai langsung, dan juga
  syarat untuk membuat `vendor/`), pastikan file tidak sedang dibuka aplikasi lain.
  `packaging\siapkan_vendor.py --uji` menguji salinan di `vendor/`.
- **"Hapus Background" gagal di mode pengembang tanpa `vendor/`** → butuh internet sekali untuk
  unduh model AI (~176MB ke `~/.u2net`). Setelah itu jalan offline.
- **LaMa lama di pemakaian pertama** → memuat model 40–100 detik di CPU lama, juga setelah model
  dilepas karena 10 menit tidak dipakai. Di mode pengembang tanpa `vendor/`, pemakaian pertama juga
  mengunduh ~208 MB.
- **HEIC tidak terbaca** → pastikan `pillow-heif` terpasang (`pip install pillow-heif`).
