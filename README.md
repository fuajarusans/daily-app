<p align="center">
  <img src="static/img/emblem.png" alt="" width="96">
</p>

<h1 align="center">Daily App</h1>

<p align="center">
  Kumpulan alat kerja harian untuk Windows: PDF, gambar, invoice, dan catatan.<br>
  Gratis, dan semua file diproses di laptop Anda sendiri.
</p>

<p align="center">
  <!-- Ganti LINK_GOOGLE_DRIVE dengan link berbagi folder/file installer di Google Drive. -->
  <a href="LINK_GOOGLE_DRIVE"><b>Unduh Daily App 1.2.1 untuk Windows</b></a>
  ·
  <a href="#cara-memasang">Cara memasang</a>
  ·
  <a href="https://www.instagram.com/fajar_snts">Instagram @fajar_snts</a>
</p>

![Beranda Daily App](docs/screenshots/beranda.png)

## Isinya

Pilih alat dari Beranda dengan mouse, atau tombol panah lalu **Enter**. Tombol **Esc** kembali
ke Beranda.

| Alat | Fungsi |
|---|---|
| PDF ke Word | Ubah `.pdf` menjadi `.docx` yang bisa diedit |
| Office ke PDF | Word, Excel, PowerPoint menjadi PDF (perlu LibreOffice) |
| Kompres PDF | Perkecil ukuran PDF; metode Maksimal perlu Ghostscript |
| Ubah ukuran gambar | Skala, lebar/tinggi, atau target ukuran file (KB) |
| Konversi gambar | PNG, JPG, JFIF, WEBP, HEIC, BMP, TIFF |
| Hapus background | Latar belakang foto dihapus otomatis (AI) |
| Hapus watermark | Sapukan kuas di atas watermark, lalu hapus (OpenCV atau LaMa AI) |
| QR code | Teks atau URL menjadi gambar QR |
| Catatan & pengingat | Catatan, tugas, tenggat, dan pengingat jatuh tempo |
| Invoice | Invoice PDF untuk beberapa brand: 10 desain, nomor otomatis, klien tersimpan, PPN & diskon, terbilang |

Banyak alat menerima beberapa file sekaligus; hasilnya diunduh sebagai satu `.zip`.

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/catatan.png" alt="Catatan dengan pengingat jatuh tempo"></td>
    <td width="50%"><img src="docs/screenshots/invoice.png" alt="Daftar invoice dengan status lunas dan belum lunas"></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/desain-invoice.png" alt="Pilihan 10 desain invoice"></td>
    <td><img src="docs/screenshots/pdf-invoice.png" alt="Contoh PDF invoice desain Modern"></td>
  </tr>
</table>

<sub>Tangkapan layar memakai data contoh.</sub>

## Cara memasang

1. Unduh `DailyApp-Setup-1.2.1.exe` dari link di atas.
2. Jalankan. Bila muncul layar **"Windows protected your PC"**, klik **More info**, lalu
   **Run anyway**. Peringatan ini muncul karena aplikasi belum ditandatangani sertifikat
   berbayar.
3. Ikuti langkah instalasi (tidak perlu hak admin), lalu buka **Daily App** dari Desktop atau
   Start Menu.

**Persyaratan:** Windows 10/11 64-bit. Daily App tampil sebagai jendela aplikasi memakai
Microsoft Edge WebView2 (sudah ada di Windows 11 dan sebagian besar Windows 10).

**Memeriksa keaslian file (opsional):** SHA-256 `DailyApp-Setup-1.2.1.exe`:

```
ab8ff60f61e7313b6b933472e10ffdd091c1b9ee9ca9916996252363b4217052
```

Cek di PowerShell:

```powershell
Get-FileHash .\DailyApp-Setup-1.2.1.exe -Algorithm SHA256
```

## Privasi & data

- File yang Anda proses tidak diunggah ke server mana pun; semuanya diproses di komputer Anda.
- Catatan, brand, klien, dan invoice tersimpan di `%LOCALAPPDATA%\DailyApp` dan tidak terhapus
  saat aplikasi diperbarui atau di-uninstall. Untuk backup, salin folder `data` di dalamnya.
- File hasil di dalam aplikasi dihapus otomatis 1 jam setelah dibuat.
- Internet hanya dibutuhkan sekali, saat **Hapus Background** (~170 MB) dan **Hapus Watermark
  engine LaMa** (~208 MB) pertama kali mengunduh model AI.

## Bila ada masalah

- **Office ke PDF** atau **Kompres PDF Maksimal** berlabel *perlu setup*: pasang
  [LibreOffice](https://www.libreoffice.org/download/) atau
  [Ghostscript](https://ghostscript.com/releases/gsdnld.html) (keduanya gratis).
- **Proses pertama gagal lalu berhasil saat diulang:** antivirus (mis. Avast/AVG) sedang
  memindai berkas aplikasi yang baru dipasang. Klik **Proses** sekali lagi.
- **Aplikasi tidak mau terbuka:** kirim berkas log dari `%LOCALAPPDATA%\DailyApp\logs` lewat
  DM Instagram [@fajar_snts](https://www.instagram.com/fajar_snts).

## Untuk pengembang

Menjalankan dari kode sumber, menambah alat baru, dan membuat installer:
[docs/PENGEMBANG.md](docs/PENGEMBANG.md). Arah desain tampilan: [DESIGN.md](DESIGN.md).

## Hak cipta & lisensi

Hak cipta © 2026 **Fajar Santoso** · [Instagram @fajar_snts](https://www.instagram.com/fajar_snts)

Daily App adalah perangkat lunak bebas dengan lisensi **GNU AGPL-3.0** ([LICENSE](LICENSE)).
Anda boleh memakai, membagikan, dan mengubahnya; bila membagikan ulang, sertakan pemberitahuan
hak cipta dan kode sumbernya. Daftar komponen pihak ketiga ada di [NOTICE.md](NOTICE.md).

"PlayStation" adalah merek dagang Sony Interactive Entertainment. Daily App hanya terinspirasi
tata letak layar berandanya dan tidak berafiliasi dengan Sony.
