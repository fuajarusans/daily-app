# Tindak lanjut audit antislop #001 · Daily App

- **Tanggal:** 16 Oktober 2026
- **Disetujui pemilik:** no. 1–18 dan 20–23 (sesuai saran). Nomor lain tidak disentuh.
- **Diuji di:** server uji dengan salinan data (data asli tidak tersentuh), lebar 375 px dan desktop, ditambah uji skrip untuk PDF dan Ghostscript.

## Status per nomor

| No | Status | Yang diubah | Bukti |
|---|---|---|---|
| 1 | Selesai | Judul tab memakai "·"; tagline header tanpa tanda pisah | Judul 6 halaman terbaca `… · Daily App`; tidak ada em dash di teks aplikasi |
| 2 | Selesai | Teks bantu, dropdown, label opsi tool, pesan error, dan metadata Creator PDF tanpa em dash | Pindaian halaman: em dash hanya tersisa di **isi catatan milik pengguna** (bukan teks aplikasi) |
| 3 | Selesai | `break-words`/`break-all` di isi catatan, tag, nomor invoice, kontak & alamat klien | Halaman Catatan di 375 px: lebar 818 px → **375 px** |
| 4 | Selesai | Tombol unduh `max-w-full`, nama file bisa terpotong baris | `app.js`, `watermark.js` |
| 5 | Selesai | Header `flex-wrap`, label tombol pengingat dipersingkat di ponsel | Dengan tombol pengingat + lencana tampil: tidak melebar, menu turun ke baris kedua |
| 6 | Selesai | `text-slate-400` → `text-slate-500` (putih) / `slate-600` (footer) | 4,76:1 dan 6,92:1 |
| 7 | Selesai | Teks pengantar & chip "batch" → `slate-600` | 6,92:1 di latar `slate-100` |
| 8 | Selesai | Lencana `bg-red-600`; tombol unduh `bg-green-700` | 4,83:1 dan 5,02:1 |
| 9 | Selesai | Peringatan LaMa `amber-700`; pesan error form `red-700` | 5,02:1 dan 5,95:1 |
| 10 | Selesai | `opacity-70` dihapus dari catatan selesai & angka chip; judul selesai `slate-500`, lencana `slate-600` | Tidak ada lagi `.opacity-70` di daftar |
| 11 | Selesai | Warna placeholder global `#64748b`; `aria-label` di kotak cari | Placeholder terukur `rgb(100,116,139)` (4,76:1) |
| 12 | Selesai | Kartu desain jadi `role="radio"` + `tabindex` + Enter/Spasi, grup `radiogroup`, garis fokus | Spasi memilih "Spreadsheet", Enter memilih "Korporat" |
| 13 | Selesai | Input logo `sr-only` (bisa difokus), label menampilkan cincin fokus | `document.activeElement === logoFile` |
| 14 | Selesai | Cincin fokus `blue-600` di `.inp` dan input Catatan/Invoice | 5,17:1 |
| 15 | Selesai | Catatan: "Memuat catatan…", pesan gagal + tombol coba lagi, `r.ok` dicek | Simulasi server error: toast "Gagal memperbarui/menghapus catatan", tidak ada toast sukses palsu |
| 16 | Selesai | Pesan kosong dibedakan: belum ada catatan vs tidak cocok filter | `notes.js` `render()` |
| 17 | Selesai | Invoice: "Memuat data invoice…", pesan gagal menetap + coba lagi; error hapus logo & nomor otomatis ditangani | Simulasi gagal muat → pesan + tombol; coba lagi → 2 invoice tampil |
| 18 | Selesai | Hapus Watermark: gambar yang tak bisa dibuka memunculkan pesan | File rusak → "❌ Gambar tidak bisa dibuka…", tanpa error di console |
| 20 | Selesai | Contoh PDF bernomor `CONTOH/…` + tanda "CONTOH" diagonal transparan di setiap halaman | `Invoice_CONTOH-…pdf`; dicek di desain Minimalis, Korporat, Modern |
| 21 | Selesai | Ghostscript diurutkan per angka versi | `gs10.07.1 > gs10.2 > gs9.56.1`; deteksi di PC ini tetap `gs10.07.1` |
| 22 | Selesai | Batas upload diterapkan (cek `Content-Length` + ukuran tersimpan), respons 413 | Uji batas 50 KB: file 100 KB ditolak dengan pesan jelas; file kecil lolos |
| 23 | Selesai | Komentar usang di `config.py` diperbarui | `config.py:56,60` |

## Delivery Gate (lingkup perbaikan ini)

- **R-02 PASS:** tidak ada em dash di teks aplikasi (judul, label, pesan, metadata PDF). Sisa em dash hanya di komentar kode (no. 46, belum disetujui) dan isi catatan pengguna.
- **R-03 PASS:** dashboard, Catatan, Invoice, 2 halaman tool, Hapus Watermark diukur di 375 px: tidak ada yang melebar. No. 35, 36, 45 belum disetujui.
- **R-25 PASS untuk pasangan warna yang diperbaiki** (lihat tabel). No. 33 (garis tepi input) belum disetujui.
- **R-26 PASS:** tombol baru (coba lagi) berfungsi; tidak ada kontrol mati.
- **R-27 PASS:** status memuat, kosong, dan gagal ada di Catatan, Invoice, Hapus Watermark, dan halaman tool.
- **R-32 PASS untuk no. 12–14.** No. 28–32 (label, aria, tab) belum disetujui.
- **R-35 PASS:** dijalankan dan diuji (lihat kolom Bukti); console tanpa error.
- **R-38 PASS:** contoh PDF ditandai jelas sebagai CONTOH.
- **R-37 FAIL (belum dikerjakan):** arahan desain sedang disusun bersama pemilik (konsep konsol). Akan ditutup oleh redesain.

## Masih terbuka

No. 19, 24–46 kecuali 20–23. No. 19, 24, 38 akan ditangani bersama redesain. Sisanya bisa dipilih kapan saja.
