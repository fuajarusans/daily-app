# 📘 Panduan Pemakaian & Update — Daily App

Panduan praktis sehari-hari. Untuk dokumentasi teknis lengkap (instalasi awal,
arsitektur, cara membuat tool baru), lihat [README.md](README.md).

---

## ▶️ Menjalankan & Menghentikan Aplikasi

### 🖱️ Cara termudah (tanpa PowerShell) — klik dua kali
- **Menjalankan:** klik dua kali pintasan **"Daily App"** di Desktop (atau berkas
  **`Jalankan Daily App.bat`** di folder proyek). Sebuah jendela hitam akan terbuka dan
  **browser otomatis** menuju `http://localhost:8000`. Biarkan jendela hitam itu tetap
  terbuka selama memakai aplikasi.
- **Menghentikan:** cukup **tutup jendela hitam** tadi (atau tekan **CTRL + C** di
  dalamnya). Bila jendelanya telanjur hilang dan aplikasi masih berjalan, klik dua kali
  **`Hentikan Daily App.bat`** di folder proyek.

> Pintasan Desktop bernama **"Daily App"**. Jika terhapus, jalankan saja
> `Jalankan Daily App.bat` di folder proyek (atau buat ulang pintasannya).

### ⌨️ Cara alternatif (lewat PowerShell)
Buka **PowerShell** di folder proyek ini, lalu jalankan:

```powershell
.\.venv\Scripts\python.exe run.py
```

- Server menyala di `http://localhost:8000` dan **browser terbuka otomatis**.
- Biarkan jendela PowerShell tetap terbuka selama Anda memakai aplikasi.

> ⚠️ Selalu pakai `.\.venv\Scripts\python.exe` (bukan `python` saja). Perintah
> `python` polos di komputer ini masih mengarah ke stub Microsoft Store dan tidak
> akan berfungsi.

### Menghentikan
- Tekan **CTRL + C** di jendela PowerShell tempat server berjalan, **atau**
- Tutup jendela PowerShell tersebut.

### Kalau browser tidak terbuka otomatis
Buka manual di browser: **http://localhost:8000**

### Kalau port 8000 sedang dipakai
Ubah angka `PORT` di file [app/config.py](app/config.py), simpan, lalu jalankan ulang.

---

## 🧭 Cara Memakai Tool (alur umum)

Semua tool memakai pola yang sama:

1. Di dashboard, **klik kartu tool** yang ingin dipakai.
2. **Pilih file** (atau isi teks untuk QR Code), lalu atur opsi yang tersedia.
3. Klik **Proses**, tunggu sebentar, lalu klik **Unduh hasil**.

> 💡 **Batch (banyak file):** tool yang mendukung batch bisa menerima beberapa file
> sekaligus. Bila hasilnya lebih dari satu file, otomatis dibungkus menjadi satu
> file **`.zip`**.

---

## 🛠️ Panduan Per Tool

| Tool | Input | Opsi utama | Output |
|------|-------|-----------|--------|
| 🔳 **Generate QR Code** | Teks / URL (tanpa file) | Ukuran modul, tebal border | PNG |
| 🖼️ **Resize / Compress Gambar** | Gambar (batch) | Skala % atau lebar/tinggi, kualitas | Gambar (zip bila banyak) |
| 🔄 **Convert Format Gambar** | Gambar/HEIC (batch) | Format tujuan, kualitas | Gambar (zip bila banyak) |
| 🗜️ **Compress PDF** | PDF (batch) | Metode Cepat / Maksimal, kualitas | PDF (zip bila banyak) |
| 📄 **PDF ke Word** | PDF (batch) | — | DOCX (zip bila banyak) |
| 📑 **Office ke PDF** | DOCX/XLSX/PPTX (batch) | — | PDF (zip bila banyak) |
| ✂️ **Hapus Background** | Gambar (batch) | — | PNG transparan (zip bila banyak) |

### Catatan penting per tool
- **Compress PDF** — metode **Cepat** selalu bisa dipakai. Metode **Maksimal**
  (lebih kecil, terutama untuk PDF berisi banyak gambar) memakai **Ghostscript yang
  sudah terpasang** di komputer ini, jadi langsung bisa digunakan. Pilih preset
  *screen* (paling kecil), *ebook* (seimbang), atau *printer* (kualitas tinggi).
- **Hapus Background** — **pemakaian pertama** mengunduh model AI (~170 MB), jadi
  butuh internet **sekali saja** dan terasa lebih lama. Setelah itu jalan offline.
- **Office ke PDF** — memakai LibreOffice. Pastikan file Office yang akan dikonversi
  **tidak sedang dibuka** di aplikasi lain.
- **Convert Gambar** — mendukung HEIC (foto iPhone) berkat pillow-heif.

---

## 📝 Catatan & Pengingat

Buka lewat menu **📝 Catatan** di kanan atas, atau kartu **Catatan & Pengingat** di dashboard.

**Menambah:** klik **➕ Tambah Catatan**, isi judul / isi, pilih **Kategori** (Umum, Tugas,
Dokumen, Klien, Jadwal, Ide), lalu (opsional) **tag**, **tanggal jatuh tempo**, dan
**"ingatkan sejak H-…"** (mis. isi `30` agar diingatkan 30 hari sebelumnya — cocok untuk
masa berlaku paspor/izin/kontrak). Centang **Sematkan** agar selalu di atas, lalu **Simpan**.

**Mengelola:** tombol **✓ Selesai** menandai tuntas, **📌** menyematkan, **✏️** mengedit,
**🗑️** menghapus. Saring cepat lewat **chip kategori** (menampilkan jumlah per kategori),
kotak **Cari**, atau filter **tag**.

**Warna status:** 🔴 lewat tempo · 🟠 jatuh tempo hari ini · 🟡 akan datang. Angka di
lencana **📝 Catatan** = jumlah yang lewat tempo + hari ini.

**Notifikasi:** klik **🔔 Aktifkan pengingat** sekali lalu **izinkan** di browser. Selama
aplikasi terbuka, pop-up muncul untuk catatan yang lewat tempo / jatuh tempo hari ini.

> Catatan tersimpan permanen di `data/notes.json` — **tidak** terhapus otomatis (berbeda
> dengan file hasil tool yang dibersihkan tiap 1 jam). Untuk backup, cukup salin berkas itu.

---

## 🔄 Cara Update

### A. Update library Python (dependency)
Untuk memperbarui semua library ke versi terbaru sesuai daftar:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
```

Memperbarui satu library tertentu saja, contoh:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pdf2docx
```

Setelah update, **jalankan ulang** aplikasi (lihat bagian D).

### B. Update program eksternal (LibreOffice / Ghostscript)
Lewat winget:

```powershell
winget upgrade --id TheDocumentFoundation.LibreOffice
winget upgrade --id Python.Python.3.12
```

### C. Update kode aplikasi atau menambah/mengubah tool
- Bila Anda mengubah file di `app/` atau menambah/menyunting tool di `tools/`,
  perubahan **baru aktif setelah server dijalankan ulang**.
- Menambah tool baru cukup membuat satu file di folder `tools/`; dashboard akan
  menampilkannya otomatis. Langkah & template lengkap ada di
  [README.md](README.md#-cara-menambah-tool-baru).

### D. Menjalankan ulang setelah update
1. Hentikan server: **CTRL + C** di jendela PowerShell-nya.
2. Jalankan lagi:
   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```

> Catatan: aplikasi sengaja **tidak** auto-reload. Jadi setiap perubahan kode atau
> update library mengharuskan Anda menjalankan ulang agar perubahan terbaca.

---

## ❓ Masalah Umum (Ringkas)

| Gejala | Solusi |
|--------|--------|
| Halaman tidak terbuka / "tidak bisa dijangkau" | Pastikan server berjalan; jalankan `.\.venv\Scripts\python.exe run.py` |
| Tool baru / perubahan kode tidak muncul | Jalankan ulang server (CTRL+C lalu jalankan lagi) |
| Office→PDF "perlu setup" | Pastikan LibreOffice terpasang, lalu refresh halaman |
| Compress PDF "Maksimal" gagal | Pilih metode "Cepat", atau pasang Ghostscript |
| Hapus Background lama/gagal di awal | Butuh internet sekali untuk unduh model ~170 MB |
| Hasil unduhan hilang | Normal — file dibersihkan otomatis setelah 1 jam |
| Catatan hilang? | Tidak — catatan permanen di `data/notes.json` (beda dengan file hasil tool) |
| Pengingat/notifikasi tak muncul | Klik **🔔 Aktifkan pengingat** & izinkan di browser; notifikasi hanya tampil saat aplikasi terbuka |
| `python` tidak dikenali | Gunakan `.\.venv\Scripts\python.exe`, bukan `python` |
