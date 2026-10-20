# Skripsi — LaTeX

Naskah skripsi dalam LaTeX yang meniru *02. Template dan Format Penulisan Skripsi V. 2024.10*
(Departemen Informatika FSM UNDIP).

## Build

```bash
cd tex
make            # xelatex -> biber -> xelatex -> xelatex  => skripsi.pdf
```

- Perlu **XeLaTeX** dan **biber** (sudah ada di MacTeX / TeX Live penuh).
- **Overleaf:** Menu → Compiler: *XeLaTeX*. Biber dipakai otomatis.
- `make dark` → `skripsi-dark.pdf` (latar gelap, teks terang; untuk membaca di layar).
- `make docx` → `skripsi.docx` (versi Word yang dapat diedit; perlu pandoc dan python-docx).
  Saat dibuka, Word menanyakan pembaruan *field*: pilih **Yes** agar daftar isi, daftar tabel, dan daftar gambar terisi.
- Fontasi: Times New Roman jika terpasang (Mac/Windows), selain itu TeX Gyre Termes (tampilan hampir sama).

## Struktur

| File | Isi |
|---|---|
| `skripsi.tex` | Berkas utama: data skripsi (judul, nama, NIM, pembimbing) dan urutan bab |
| `undipskripsi.sty` | Seluruh aturan format template |
| `front/` | Sampul, pernyataan keaslian, pengesahan, kata pengantar, persetujuan publikasi, abstrak, abstract |
| `bab/bab1.tex` … `bab5.tex` | Bab I–III sudah ditulis; Bab IV–V masih kerangka |
| `bab/lampiran.tex` | Lampiran |
| `references.bib` | Daftar pustaka (APA 7th) |

## Aturan template yang sudah diterapkan

- A4; margin atas 3 cm, kiri 3 cm, kanan 2,5 cm, bawah 2,5 cm.
- Times New Roman 12 pt, spasi 1,5, indentasi baris pertama 1 cm, tanpa *space before/after*.
- Judul bab "BAB I / PENDAHULUAN" rata tengah dan tebal; sub bab sampai 1.1.1.1 dengan *space before* 12 pt.
- Setiap bab dibuka paragraf yang menyebut isi sub babnya.
- Pemerian memakai nomor/huruf (`enumerate`), bukan *bullet*.
- Tabel: caption di atas, isi satu spasi, header abu-abu 25 %, kolom **No** (`\hdr`, `\hrow`, `\tabsetup`).
- Gambar: caption di bawah, tanpa garis tepi; nomor per bab (Tabel 2.1, Gambar 3.2).
- Persamaan rata kiri, nomor (3.1) di kanan, diikuti lingkungan `keterangan`.
- *Source code*: kotak 2 baris 1 kolom, Courier New 10 pt (`\begin{sourcecode}{judul}{label}`).
- Halaman awal bernomor romawi kecil, isi mulai angka 1, nomor di kanan bawah.
- Daftar isi, daftar tabel, daftar gambar, dan daftar pustaka dibuat otomatis.

## Yang masih perlu diisi / dikonfirmasi

Cari `TODO` di berkas `.tex`:

1. NIM, gelar dan NIP pembimbing, pembimbing 2.
2. Kepanjangan SA, MTU, dan UPA pada alur status surat E-Office.
3. Kesamaan 7 SOP persuratan E-Office dengan korpus paper.
4. Jadwal penelitian (sesuaikan dengan tanggal seminar proposal).
5. Spesifikasi perangkat keras server lokal (Tabel 3.7).
6. Bab IV–V dan lampiran setelah implementasi dan evaluasi.
