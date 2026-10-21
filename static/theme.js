// Token warna tema konsol (lihat DESIGN.md). Dimuat tepat setelah Tailwind.
//
// Palet bawaan Tailwind dipetakan ulang ke tema gelap dengan aturan "angka besar = lebih
// menonjol": slate-900 = teks terkuat, slate-100 = dasar halaman, white = permukaan kartu.
// Dengan begitu kelas yang sudah ada di template & JS tetap konsisten tanpa ditulis ulang.
// Warna khas PlayStation (pilihan pemilik): "ps" = biru PlayStation untuk tombol utama
// (teks putih), "blue" = biru PS versi terang untuk tautan, tint, dan cincin fokus.
// Semua pasangan teks/latar yang dipakai sudah dicek >= 4,5:1.
tailwind.config = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Segoe UI Variable Display"', '"Segoe UI Variable Text"', '"Segoe UI"', "system-ui", "sans-serif"]
      },
      colors: {
        white: "#0f1a30",
        ps: { DEFAULT: "#0070D1", hover: "#005BB5", on: "#ffffff" },
        slate: {
          50: "#16253f", 100: "#070d1c", 200: "#22334d", 300: "#5b7088", 400: "#7f93a9",
          500: "#9aabbe", 600: "#b4c2d1", 700: "#cdd8e3", 800: "#e6edf5", 900: "#f4f7fb", 950: "#ffffff"
        },
        blue: {
          50: "#0c1f3d", 100: "#102a52", 200: "#1a4378", 300: "#2c66b0", 400: "#3d8be6",
          500: "#4f9cf0", 600: "#62abff", 700: "#82bdff", 800: "#b0d4ff", 900: "#d8eaff"
        },
        red: {
          50: "#2a1519", 100: "#3a1a20", 200: "#6b2a35", 300: "#a8464f", 400: "#e26b73",
          500: "#f17f86", 600: "#f69ba1", 700: "#fbb4b8", 800: "#fdd0d2", 900: "#fee7e8"
        },
        green: {
          50: "#11261d", 100: "#153124", 200: "#22513a", 300: "#2f7a52", 400: "#4fbf83",
          500: "#62c993", 600: "#7ad3a4", 700: "#97dfb8", 800: "#bdeccf", 900: "#dcf6e6"
        },
        amber: {
          50: "#2a2111", 100: "#3a2c12", 200: "#6b5220", 300: "#a77d2c", 400: "#e0b04f",
          500: "#f0bf5c", 600: "#f5cb74", 700: "#f8d78f", 800: "#fbe6b8", 900: "#fdf2da"
        },
        yellow: {
          50: "#29260f", 100: "#363112", 200: "#665b1f", 300: "#a3922f", 400: "#e3cf4f",
          500: "#ebd967", 600: "#efe07d", 700: "#f3e48a", 800: "#f8efb8", 900: "#fcf7dc"
        },
        purple: {
          50: "#1f1830", 100: "#2a2140", 200: "#45366b", 300: "#7059a8", 400: "#a48ae0",
          500: "#b49ce8", 600: "#c2adee", 700: "#cbb8f5", 800: "#ddd0f8", 900: "#eee8fc"
        },
        pink: {
          50: "#2a1420", 100: "#3a1a2c", 200: "#6b2a4c", 300: "#a84679", 400: "#e26ba5",
          500: "#ee86b6", 600: "#f29fc4", 700: "#f5b3d2", 800: "#f9d0e3", 900: "#fce7f1"
        }
      }
    }
  }
};
