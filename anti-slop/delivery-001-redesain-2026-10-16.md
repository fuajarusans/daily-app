# Delivery Gate · Redesain gaya konsol (v1.1.0)

- **Tanggal:** 16 Oktober 2026
- **Arah:** `DESIGN.md` (ditetapkan pemilik: gaya PS5, aksen teal emblem, semua halaman, suara opsional)
- **Dial:** ENERGY 2 / RHYTHM 2 / MOTION 2
- **Diuji di:** server uji dengan salinan data, exe hasil build (uji asap 31/31), dan aplikasi terpasang 1.1.0

## Block 1 · Hard Gate (semua harus "tidak")

| Aturan | Hasil | Bukti |
|---|---|---|
| R-02 em dash | PASS | `grep "—"` di templates/static: tidak ada di teks UI |
| R-03 mobile | PASS | 375 px: Beranda, Catatan (daftar+form), Invoice (daftar, form, brand), tool, watermark: tidak ada yang melebar; nama tile selalu tampil di ponsel |
| R-17 statistik tanpa sumber | PASS | Kartu Beranda membaca `/api/notes/due` dan `/api/invoice/state` (data asli); tanpa angka statis |
| R-18 testimoni | N/A | Tidak ada |
| R-23 aset tanpa izin | PASS | Logo = emblem milik pemilik; ikon Tabler (MIT) dipilih dan ditulis alasannya di DESIGN.md |
| R-24 navigasi mati | PASS | Tab Beranda/Catatan/Invoice dan semua tile menuju halaman yang ada |
| R-25 kontras | PASS | Skrip audit memeriksa setiap elemen teks di 11 halaman/state: 0 di bawah AA (skrip diverifikasi menangkap teks uji 1,62:1) |
| R-26 kontrol mati | PASS | Tombol suara, Esc, tombol ikon, "Buka" semuanya berfungsi |
| R-27 status | PASS | Kartu Beranda: "Memuat…", kosong ("Tidak ada yang jatuh tempo…"), gagal ("Gagal memuat… Muat ulang"); status lain dari audit #001 tetap |
| R-28 FAQ | N/A | Tidak ada |
| R-32 keyboard | PASS | Panah kiri/kanan, Home/End di rail; Enter membuka; Esc ke Beranda (tertahan saat form terbuka/mengetik); cincin fokus terlihat di semua kontrol; tautan "Lewati ke konten" |
| R-33 patch via skrip | PASS | Semua perubahan ditulis di sumber; token warna di `static/theme.js` (konfigurasi Tailwind resmi) |
| R-34 tema | N/A | Satu tema (gelap) tanpa toggle, alasan di DESIGN.md |
| R-35 dijalankan | PASS | Dijalankan di server uji, exe, dan aplikasi terpasang; console tanpa error |
| R-36 klaim palsu | PASS | Tidak ada klaim baru |
| R-37 arahan | PASS | DESIGN.md ditulis dari jawaban pemilik |
| R-38 konten karangan | PASS | Sorotan & chip berasal dari registry tool (format, batch, status setup) |

## Block 2 · Purpose-Gate

- **R-01 PASS:** satu gradien (cahaya teal kanan atas), alasan di DESIGN.md.
- **R-04 PASS:** emoji dihapus dari UI; ikon Tabler, satu ikon satu makna (kategori Catatan punya ikon sendiri).
- **R-06 PASS:** Segoe UI (bawaan Windows, offline), judul sorotan ringan; alasan tertulis.
- **R-07, R-10, R-22 PASS:** tanpa pola latar, glassmorphism, atau ilustrasi.
- **R-08 PASS:** tidak ada panah dekoratif di tombol.
- **R-09 PASS:** lencana hanya status nyata (jumlah jatuh tempo, perlu setup, Lunas, Default).
- **R-12 PASS:** bayangan hanya pada toast.
- **R-13 PASS:** cahaya hanya di cincin fokus (motif) dan latar.
- **R-14 PASS:** tile rail seragam dengan alasan tertulis (pilihan setara di menu konsol; hierarki dari fokus).
- **R-19 PASS:** gerak hanya skala fokus 180 ms dan transisi hover; tanpa loop; `prefers-reduced-motion` dihormati.

## Block 3 · Liveliness

- Dial tertulis dan konsisten (Beranda tiga lapis, halaman kerja lebih tenang): PASS
- Titik fokus per layar: sorotan di Beranda, kepala halaman di halaman kerja: PASS
- Ruang kosong struktural (sorotan → rail → ringkasan): PASS
- Satu aksen (teal): aksi utama, tab aktif, cahaya latar: PASS
- Motif identitas: cincin fokus: PASS
- Design Read dideklarasikan sebelum membangun: PASS (DESIGN.md)

## Block 4 · Craftsmanship & Quality Locks

- C-1..C-5: PASS (tiap keputusan punya alasan di DESIGN.md; tidak ada kontrol mati; tidak ada bagian template; tahan di status/breakpoint/keyboard; tidak ada klaim karangan).
- R-05 PASS (bukan template landing/dashboard default), R-11 PASS (radius 6/10/12 px), R-15 PASS ("Buka", "Buat Invoice", "Tambah Catatan"), R-16 PASS, R-20 PASS (teal emblem + motif cincin fokus khas aplikasi ini), R-21 PASS (gelap dengan alasan), R-29 PASS (netral + teal + warna status; kategori netral), R-30 PASS (tanpa aset/warna/ikon PlayStation), R-31 PASS.

## Temuan audit #001 yang ikut tertutup oleh redesain

No. 19 (arahan desain), 24 (emoji), 26 (kartu tool seragam tanpa alasan), 27 (label 10 px kapital hilang dari Beranda), 37 (Tailwind lokal), 38 (palet & aksen), 39 (satu gaya field), 42 (footer menyebut 1 jam). Sebagian: 29 (tombol ikon kini punya `aria-label` + label teks di ponsel), 30 (`aria-pressed` pada mode kuas dan chip kategori), 31 (`role="status"` di halaman tool).

## Catatan

- Akses pertama ke beberapa berkas exe yang baru dibangun/dipasang sempat gagal sekali (Ghostscript, PDF ke Word) lalu normal. Antivirus Avast aktif di PC ini dan dikenal memindai program baru tanpa tanda tangan saat pertama dipakai; dicatat di PANDUAN-PENERIMA.

## Pembaruan v1.2.0 (keputusan pemilik)

- **Warna PlayStation:** tombol utama biru PS `#0070D1` (teks putih 4,95:1), tautan biru PS terang
  (≥7:1), latar sorotan berganti warna per tile maks. 38% (kontras teks terburuk ≈5:1, dihitung
  untuk semua 11 warna). Penyimpangan sadar dari R-30 atas permintaan pemilik, dicatat di DESIGN.md;
  tetap tanpa aset Sony. R-29: warna tile hanya di wajah tile terfokus dan latar sorotan.
- **Kartu Catatan dilipat:** isi panjang 2 baris + tombol Selengkapnya/Tutup (`aria-expanded`,
  fokus tetap di tombol); daftar dua kolom di layar lebar. Uji: 40 px terlipat vs 1.500 px terbuka.
- **Hak cipta:** © 2026 Fajar Santoso + AGPL-3.0 (`LICENSE`, `NOTICE.md`), footer dengan tautan
  lisensi, kode sumber, dan Instagram @fajar_snts; installer menampilkan halaman lisensi dan
  memasang LICENSE + NOTICE; properti exe berisi hak cipta.
- **Ulang gate:** kontras AA 0 gagal di 16 halaman/state (desktop + 375 px), tidak ada yang melebar,
  uji asap exe 31/31, aplikasi terpasang 1.2.0 diperiksa lewat tangkapan layar.
