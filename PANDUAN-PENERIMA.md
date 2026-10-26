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
   **Buat shortcut di Desktop** bila ingin. Di akhir instalasi, installer menyiapkan
   konverter dokumen sekitar setengah menit.
4. Buka **Daily App** dari Desktop atau Start Menu.

Semua komponen sudah termasuk di installer (konverter dokumen LibreOffice, Ghostscript,
dan model AI), jadi tidak ada yang perlu diunduh atau dipasang lagi.

**Kebutuhan:** Windows 10/11 64-bit, ruang kosong sekitar 2 GB saat instalasi (1,4 GB
setelah terpasang), RAM 4 GB (8 GB disarankan bila memakai Hapus Background atau
Hapus Watermark LaMa). Daily App tampil sebagai jendela aplikasi memakai Microsoft Edge
WebView2 (sudah ada di Windows 11 dan sebagian besar Windows 10). Bila belum terpasang,
installer memberi tahu dan aplikasi terbuka di browser.

## Memakai

- Di **Beranda**, pilih alat dengan mouse atau tombol panah kiri/kanan lalu **Enter**. Tombol
  **Esc** kembali ke Beranda. Ada bunyi halus saat berpindah pilihan; matikan lewat ikon
  speaker di kanan atas bila tidak ingin mendengarnya.
- Unggah file, lalu klik **Proses**. Tombol **Unduh hasil**
  membuka dialog **Simpan sebagai**.
- File hasil di dalam aplikasi dihapus otomatis 1 jam setelah dibuat, jadi segera simpan.
- **Pratinjau PDF** dan tombol **PDF** di Invoice membuka PDF di browser Anda.
- Tutup jendela Daily App untuk keluar. Bila masih ada sticky note di desktop, Daily App
  tetap berjalan di ikon tray (pojok kanan bawah); keluar lewat menu **Keluar** di ikon itu.

## Sticky note di desktop

- Di halaman **Catatan**, seret kartu catatan (lewat pegangan bertitik di samping judul atau area
  kosong kartu) sampai keluar dari jendela Daily App, atau klik ikon catatan di kartu. Catatan
  itu muncul sebagai sticky note di desktop.
- Isi sticky bisa langsung diedit dan tersimpan otomatis; perubahannya ikut tampil di
  halaman Catatan.
- Seret bilah atas sticky untuk memindahkan, dan pojok kanan bawah untuk mengubah ukuran.
  Tombol di bilah atas: **Selalu di atas**, **Warna**, **Buka di Daily App**, dan **Lepas dari
  desktop** (ikon X).
- Sticky note hanya tersedia saat Daily App tampil sebagai jendela aplikasi (WebView2), tidak saat
  terbuka di browser.
- Sticky muncul lagi di tempat yang sama saat Daily App dibuka berikutnya, dan saat Windows
  menyala bila pilihan itu dicentang waktu instalasi.

## Catatan per alat

- **Hapus Watermark (engine LaMa AI)**: memuat model AI bisa 1–2 menit di laptop lama, yaitu saat
  pertama dipakai dan setelah 10 menit tidak dipakai (model dilepas agar memori lega). Selama
  model masih dimuat, proses berikutnya lebih cepat.
- **Office ke PDF**: konversi dijalankan satu per satu; konversi pertama setelah instalasi
  bisa sedikit lebih lama.
- **Compress PDF metode Maksimal** mengompres ulang gambar di dalam PDF. Hasilnya tidak pernah
  lebih besar dari aslinya: bila PDF tidak bisa dikecilkan lagi, Daily App mengembalikan file aslinya.

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

- **Membuka Daily App tidak memunculkan jendela baru**: aplikasi sudah berjalan, dan jendelanya
  akan ditampilkan ke depan. Cek juga ikon Daily App di tray.
- **Proses pertama sangat lambat, atau gagal lalu berhasil saat diulang**: antivirus (misalnya
  Avast/AVG) sedang memindai berkas aplikasi yang baru dipasang, termasuk model AI, saat pertama
  kali dipakai. Hapus Background pertama setelah instalasi bisa butuh 2–3 menit; berikutnya
  sekitar 10 detik. Bila gagal, klik **Proses** sekali lagi; setelah pemindaian pertama, aplikasi
  berjalan normal.
- **Aplikasi tidak mau terbuka**: kirim berkas log dari
  `%LOCALAPPDATA%\DailyApp\logs` kepada pemberi aplikasi.
