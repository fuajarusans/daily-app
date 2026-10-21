# Panduan Daily App

Daily App adalah kumpulan alat harian yang berjalan di komputer Anda sendiri:
konversi PDF/Word/gambar, kompres PDF, hapus background dan watermark, QR code,
catatan dan pengingat, serta pembuat invoice PDF. File Anda tidak dikirim ke internet.

## Memasang

1. Jalankan `DailyApp-Setup-<versi>.exe`.
2. Jika muncul layar biru **"Windows protected your PC"**: klik **More info**, lalu
   **Run anyway**. Peringatan ini muncul karena aplikasi belum ditandatangani
   sertifikat berbayar, bukan karena berbahaya.
3. Ikuti langkah instalasi (tidak perlu hak admin). Centang
   **Buat shortcut di Desktop** bila ingin.
4. Buka **Daily App** dari Desktop atau Start Menu.

Butuh Windows 10/11 64-bit. Daily App tampil sebagai jendela aplikasi memakai
Microsoft Edge WebView2 (sudah ada di Windows 11 dan sebagian besar Windows 10). Bila
belum terpasang, installer memberi tahu dan aplikasi terbuka di browser.

## Memakai

- Di **Beranda**, pilih alat dengan mouse atau tombol panah kiri/kanan lalu **Enter**. Tombol
  **Esc** kembali ke Beranda. Ada bunyi halus saat berpindah pilihan; matikan lewat ikon
  speaker di kanan atas bila tidak ingin mendengarnya.
- Unggah file, lalu klik **Proses**. Tombol **Unduh hasil**
  membuka dialog **Simpan sebagai**.
- File hasil di dalam aplikasi dihapus otomatis 1 jam setelah dibuat, jadi segera simpan.
- **Pratinjau PDF** dan tombol **PDF** di Invoice membuka PDF di browser Anda.
- Tutup jendela Daily App untuk keluar.

## Catatan per alat

- **Hapus Background** dan **Hapus Watermark (engine LaMa AI)**: pemakaian pertama
  mengunduh model AI (sekitar 170 MB dan 208 MB). Butuh internet sekali saja, setelah
  itu bisa offline.
- **Office ke PDF**: butuh LibreOffice (gratis): https://www.libreoffice.org/download/
- **Compress PDF metode Maksimal**: butuh Ghostscript (gratis):
  https://ghostscript.com/releases/gsdnld.html (metode Cepat tidak butuh apa-apa).
  Tanpa program itu, alat terkait menampilkan label **perlu setup**.

## Data Anda

Catatan, brand, klien, dan invoice tersimpan di folder:

    %LOCALAPPDATA%\DailyApp

(ketik alamat itu di File Explorer). Folder ini **tidak** terhapus saat aplikasi
diperbarui atau di-uninstall. Untuk backup, salin folder `data` di dalamnya.

## Memperbarui

Jalankan installer versi baru. Data Anda tetap aman.

## Menghapus

Settings → Apps → **Daily App** → Uninstall (atau Start Menu → **Hapus Daily App**).
Hapus juga folder `%LOCALAPPDATA%\DailyApp` bila ingin membuang semua data.

## Bila ada masalah

- **"Daily App sudah berjalan"**: aplikasi sudah terbuka; cek taskbar.
- **Proses pertama gagal, lalu berhasil saat diulang**: antivirus (misalnya Avast/AVG) sedang
  memindai berkas aplikasi yang baru dipasang saat pertama kali dipakai. Klik **Proses** sekali
  lagi; setelah pemindaian pertama, aplikasi berjalan normal.
- **Aplikasi tidak mau terbuka**: kirim berkas log dari
  `%LOCALAPPDATA%\DailyApp\logs` kepada pemberi aplikasi.
