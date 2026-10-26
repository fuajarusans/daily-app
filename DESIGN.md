# DESIGN.md · Daily App

Arah desain ini ditetapkan pemilik (Fajar Santoso) pada 16 Oktober 2026 dan menjadi acuan
untuk semua pekerjaan UI. `antislop` dipakai sebagai filter, bukan sumber arah.

**Pembaruan v1.2.0 (keputusan pemilik):** aksen teal diganti **biru PlayStation**, dan latar
sorotan Beranda **berganti warna per tile** seperti layar beranda PS5 (contoh dari pemilik).
Ini penyimpangan sadar dari antislop R-30 ("jangan meniru produk populer") atas permintaan
pemilik; batasnya: tetap tanpa logo, font SST, ikon △○×□, suara, atau aset Sony lainnya.

## Identitas

- **Konsep:** layar beranda konsol (gaya PS5): deretan tile horizontal, tile yang difokus
  membesar, area sorotan menampilkan judul, keterangan, dan satu aksi, dengan latar yang
  berganti warna mengikuti tile. Warna biru PlayStation dipakai atas permintaan pemilik; logo,
  font SST, ikon △○×□, dan suara Sony **tidak** dipakai.
- **Kepribadian:** tenang, fokus, cepat. Aplikasi kerja harian, bukan game: gerak secukupnya,
  tanpa efek pamer.
- **Suasana:** ruang biru-hitam khas PS5 dengan cahaya biru PlayStation; latar sorotan
  diwarnai alat yang sedang difokus.

## Dial (Design Read)

`Dial: ENERGY 2 / RHYTHM 2 / MOTION 2`

- **ENERGY 2:** kanvas gelap, satu cahaya teal, fokus diberi cincin terang. Tidak ada efek lain.
- **RHYTHM 2:** Beranda punya tiga lapis berbeda (sorotan, rail, kartu ringkasan); halaman kerja
  (tool, Catatan, Invoice) lebih tenang: kepala halaman + panel.
- **MOTION 2:** fokus tile membesar 180 ms, cahaya latar bergeser 400 ms, transisi hover. Tanpa
  animasi berulang. `prefers-reduced-motion` mematikan skala dan pergeseran.

## Palet

| Peran | Nilai | Alasan |
|---|---|---|
| Dasar halaman | `#070d1c` | Biru-hitam khas PS5; tema gelap = metafora layar konsol yang dipilih pemilik (R-21) |
| Permukaan (kartu, panel) | `#0f1a30` | Satu tingkat di atas dasar, membedakan wadah tanpa bayangan |
| Permukaan terangkat / hover | `#16253f` | Penanda interaksi |
| Garis | `#22334d` (dekoratif), `#5b7088` (tepi input, ≥3:1) | |
| Teks utama / kedua / redup | `#e6edf5` / `#b4c2d1` / `#9aabbe` | Semua ≥4,5:1 di atas permukaan |
| **Biru PlayStation** (`ps`) | `#0070D1`, hover `#005BB5`, teks putih (4,95:1) | Tombol utama, tab aktif, cahaya latar |
| Biru PS terang (`blue`) | `#62abff` dst. | Tautan, tint, ikon aktif (≥7:1 di latar gelap) |
| **Warna tile** | 1 warna per alat (mis. Catatan `#e09f3e`, Invoice `#3fa66b`, Kompres PDF `#d64545`) | Hanya untuk wajah tile yang difokus dan latar sorotan, maks. 38% agar teks tetap ≥4,5:1 |
| Status | merah, kuning, hijau | Hanya untuk status (lewat tempo, hari ini, lunas), tidak untuk dekorasi |

Tema dibuat lewat **token Tailwind** di `static/theme.js` (`tailwind.config`): skala
`slate` dipetakan ulang menjadi skala netral gelap dengan aturan **angka besar = lebih menonjol**
(`slate-900` = teks terkuat, `slate-100` = dasar halaman, `white` = permukaan kartu). Token
`ps` (`bg-ps hover:bg-ps-hover text-ps-on`) untuk tombol utama; warna status dan `blue`
diatur ulang agar kontrasnya lolos di latar gelap. Dengan
begitu kelas yang sudah ada (termasuk HTML yang dibangun JavaScript) tetap konsisten.

## Tipografi

`"Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif`. Alasan: font bawaan Windows
(aplikasi ini aplikasi desktop Windows, harus jalan tanpa internet), dan varian Light/Semilight-nya
memberi judul sorotan yang besar dan ringan seperti layar konsol. Judul sorotan 28-36 px ringan;
teks isi 14-16 px.

## Motif identitas

**Cincin fokus.** Apa pun yang sedang difokus (tile, tombol, tab, kartu desain) diberi cincin
putih 2 px dengan sedikit cahaya teal. Ini metafora konsol ("fokus adalah bintangnya") dan
sekaligus memenuhi kebutuhan navigasi keyboard (R-32).

## Ikon

Tabler Icons (MIT, disimpan lokal di `static/vendor/tabler-sprite.svg`). Alasan: garisnya
konsisten dan terbaca di ukuran tile, bisa offline, dan menggantikan emoji yang sebelumnya
menjadi dekorasi (audit no. 24). Satu ikon = satu makna di seluruh aplikasi.

## Navigasi

- Panah kiri/kanan memindah fokus di rail; Enter membuka; Esc kembali ke Beranda (tidak aktif
  saat mengetik di input, textarea, atau kanvas). Tab tetap berfungsi seperti biasa.
- Tile terakhir yang dibuka diingat, sehingga kembali ke Beranda mengembalikan fokus ke sana.
- Nama tile: tile terfokus putih tebal; tile lain tampil samar (#b4c2d1, tetap >= 4,5:1 di atas
  latar sorotan) sebagai pratinjau isi rail (permintaan pemilik, v1.4.0).
- Ponsel: rail bisa digeser dengan jari (scroll-snap), nama tile selalu tampil, target sentuh ≥44 px.

## Suara

Klik halus buatan Web Audio (bukan suara PlayStation). Berbunyi saat kursor atau panah berpindah
ke tile lain (sekali per tile, dibatasi agar tidak bertumpuk) dan saat membuka. **Menyala secara
bawaan** (permintaan pemilik, v1.2.1), bisa dimatikan dari tombol speaker di bilah atas; pilihan
diingat per perangkat. Di aplikasi desktop (WebView2) langsung berbunyi; di browser biasa baru
berbunyi setelah klik pertama karena kebijakan autoplay browser.

## Keputusan desain (satu baris per keputusan, R-31)

- **Tema gelap tetap, tanpa toggle:** konsep konsol yang dipilih pemilik; satu tema yang dirawat
  dengan baik lebih baik daripada dua yang setengah jadi.
- **Cahaya biru PS di sudut kanan atas + latar sorotan per tile:** dua gradien yang memberi titik
  fokus pada kanvas gelap; latar sorotan berganti warna (450 ms) seperti layar beranda PS5.
- **Tile seragam di rail:** tile adalah pilihan setara di menu konsol; hierarki datang dari fokus,
  bukan ukuran tetap.
- **Kartu ringkasan Beranda** hanya berisi data nyata (pengingat jatuh tempo, invoice belum lunas),
  tidak ada angka karangan.
- **Radius:** 6 px kontrol, 10 px tile, 12 px panel; tombol "Buka" di sorotan berbentuk pil seperti tombol konsol.
- **Kartu Catatan dilipat:** isi panjang tampil 2 baris dengan tombol Selengkapnya/Tutup; daftar dua kolom di layar lebar agar kartu tidak terlalu lebar.
- **Footer:** hak cipta © 2026 Fajar Santoso, lisensi AGPL-3.0, kode sumber, dan Instagram @fajar_snts.
- **Tanpa bayangan** kecuali toast (melayang di atas konten).
- **Kategori Catatan dibedakan ikon, chip netral:** warna merah/kuning/hijau khusus status jatuh tempo, agar satu warna tidak bermakna ganda.
- **Prioritas = ikon bendera + label:** hanya "Tinggi" berwarna (ungu, tidak dipakai status); Sedang/Rendah chip netral, jadi makna tidak bergantung pada warna.
- **Checklist diedit di tempat:** item dicentang dan diketik langsung di kartu dan sticky (seperti kertas), tombol prioritas/hapus/pegangan muncul saat baris disorot atau difokus (selalu tampil di layar sentuh); keyboard setara mouse (Enter, Tab, Alt+↑/↓), dan klik pegangan membuka menu pindah sebagai pengganti seret (WCAG 2.5.7).
- **Prioritas di sticky sempit:** label disingkat T/S/R; Rendah berbingkai, Sedang berlatar, Tinggi warna terbalik, jadi ketiganya beda tanpa bergantung pada warna.
- **Hapus tanpa dialog, dengan Urungkan:** dialog konfirmasi diganti toast "Urungkan" 8 detik (juga Ctrl+Z), berlaku juga untuk Arsipkan dan selesai pada tugas berulang.
- **Pratinjau desain invoice tetap putih:** menggambarkan kertas PDF, bukan bagian tema.
