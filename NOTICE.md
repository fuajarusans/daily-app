# Hak Cipta & Lisensi Daily App

**Daily App**
Hak cipta © 2026 Fajar Santoso. Seluruh kode, desain antarmuka, dan logo Daily App
dibuat oleh dan milik Fajar Santoso.

- Instagram: https://www.instagram.com/fajar_snts
- Kode sumber: https://github.com/fuajarusans/daily-app

## Lisensi

Daily App adalah perangkat lunak bebas: Anda boleh membagikan dan/atau mengubahnya menurut
ketentuan **GNU Affero General Public License versi 3** (AGPL-3.0) sebagaimana diterbitkan
Free Software Foundation. Teks lengkapnya ada di berkas `LICENSE`.

Daily App dibagikan dengan harapan bermanfaat, tetapi **tanpa jaminan apa pun**, termasuk
jaminan tersirat mengenai kelayakan untuk diperdagangkan atau kesesuaian untuk tujuan
tertentu. Lihat AGPL-3.0 untuk detailnya.

Mengapa AGPL-3.0: installer Daily App membawa komponen berlisensi AGPL-3.0 (PyMuPDF) dan
GPL (libx265 dari pillow-heif), sehingga keseluruhan aplikasi yang dibagikan harus mengikuti
lisensi yang kompatibel. Hak cipta atas kode Daily App tetap milik Fajar Santoso.

Bila Anda membagikan ulang Daily App (asli atau yang telah diubah), sertakan pemberitahuan
hak cipta ini, berkas `LICENSE`, dan sediakan kode sumbernya.

## Komponen pihak ketiga

Daily App memakai komponen sumber terbuka berikut. Hak cipta masing-masing tetap milik
pembuatnya, di bawah lisensinya sendiri.

| Komponen | Lisensi | Dipakai untuk |
|---|---|---|
| PyMuPDF (Artifex) | AGPL-3.0 | Membaca PDF (PDF ke Word) |
| pdf2docx | MIT | PDF ke Word |
| pillow-heif (+ libheif, libx265) | BSD-3-Clause; libheif LGPL-3.0; libx265 GPL-2.0-or-later | Gambar HEIC |
| fpdf2 | LGPL-3.0 | Membuat PDF invoice |
| pikepdf (+ qpdf) | MPL-2.0 (qpdf: Apache-2.0) | Kompres PDF |
| Pillow | MIT-CMU (HPND) | Olah gambar |
| OpenCV (opencv-python-headless) | Apache-2.0 | Hapus watermark |
| ONNX Runtime | MIT | Model AI (rembg, LaMa) |
| rembg, pymatting | MIT | Hapus background |
| python-docx | MIT | Dokumen Word |
| qrcode | BSD | QR code |
| NumPy, SciPy, scikit-image, Numba, pooch | BSD | Komputasi pendukung |
| FastAPI, Starlette, Uvicorn, Jinja2 | MIT / BSD | Server & template lokal |
| pywebview | BSD-3-Clause | Jendela aplikasi |
| pythonnet | MIT | Jembatan ke WebView2 |
| Tailwind CSS 3.4.17 | MIT | Gaya tampilan |
| Tabler Icons 3.31.0 | MIT | Ikon (`static/vendor/tabler-icons-LICENSE.txt`) |
| Python 3.12 | PSF License | Runtime |

Model AI yang diunduh saat dipakai (tidak ikut installer): U²-Net untuk rembg (Apache-2.0)
dan LaMa (Apache-2.0).

Program luar yang tidak ikut installer dan dipasang sendiri oleh pengguna: LibreOffice (MPL-2.0)
dan Ghostscript (AGPL-3.0).

"PlayStation" adalah merek dagang Sony Interactive Entertainment. Daily App hanya terinspirasi
tata letak layar berandanya dan tidak memakai logo, ikon, font, atau suara milik Sony.
