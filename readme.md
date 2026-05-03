# 📊 MRTG Automation Tool for TelkomCare

**Aplikasi Desktop (GUI) & Terminal (CLI) untuk otomatisasi pengunduhan grafik MRTG dari TelkomCare berdasarkan SID atau Graph Title. Dilengkapi dengan validasi gambar (YCbCr), auto-navigasi, dan retry otomatis.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-green)](https://selenium.dev)
[![PySide6](https://img.shields.io/badge/PySide6-Qt-yellow)](https://doc.qt.io/qtforpython/)

---

## 📌 Fitur Utama

- 💻 **Antarmuka Desktop (GUI)** – Tampilan GUI modern menggunakan PySide6 dengan fitur *Live Log*, Kalender (*Date Picker*), dan mode Dark/Light.
- ⚙️ **Dua Mode Eksekusi** – Bisa dieksekusi secara interaktif melalui **GUI** atau secara tradisional melalui **CLI** (*Command Line*).
- 🔄 **Unified Scraping Engine** – Pencarian berdasarkan **SID** maupun **Graph Title** kini tergabung dalam satu aplikasi.
- 🎨 **Validasi Gambar YCbCr** – Logika tingkat lanjut untuk membedakan gambar grafik yang kosong (0 bps) dengan gambar *Error / No Graph* berdasarkan analisis warna, mencegah data yang sah terhapus otomatis.
- 🧭 **Navigasi Sidebar Otomatis** – Setelah *login manual* sukses, bot akan otomatis mencarikan menu "Graph" dan masuk ke "Monitor Graph" atau "List Graph".
- ✅ **Retry otomatis** – Fitur otomatis memuat ulang halaman (*refresh*) jika data tabel/grafik gagal dimuat (*Stale Element*).
- 📂 **Group by Tanggal** – Output diorganisir rapi ke folder `YYYYMMDD/MRTG_<ID>.png`.

---

## 🛠️ Prasyarat

| Software | Keterangan |
|----------|-------------|
| **Python 3.8+** | [Download](https://www.python.org/downloads/) |
| **Google Chrome** | Browser terbaru |
| **Tesseract OCR (Opsional)**| [Download](https://github.com/UB-Mannheim/tesseract/wiki) – untuk fallback validasi teks jika gambar dirasa blur. |
| **Internet** | Akses ke `telkomcare.telkom.co.id` |

---

## 📦 Instalasi

1. **Clone repository** (atau download zip)
   ```bash
   git clone https://github.com/username/mrtg-automation.git
   cd mrtg-automation
   ```

2. **Buat virtual environment (opsional tapi disarankan)**
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   ```

3. **Install library Python**
   ```bash
   pip install selenium webdriver-manager pillow pytesseract PySide6
   ```

---

## 📁 Persiapan File Input

Buat dua file teks di folder yang sama dengan script:

### 1. Untuk mode SID (`SID-MRTG.txt`)
```text
SID : 4700001-0021497479
SID : 4700001-0020265222
SID : 2007544330
```

### 2. Untuk mode Graph Title (`GRAPH-TITLE-MRTG.txt`)
```text
Graph-title : 3598
Graph-title : 3784
```

---

## 🚀 Cara Penggunaan

### Opsi 1: Mode GUI (Sangat Direkomendasikan)
Menjalankan aplikasi versi Desktop yang ramah pengguna.
```bash
python mrtg_telkomcare_gui.py
```
**Alur:**
1. Pilih **Mode Pencarian** (SID atau Graph Title).
2. Atur **Rentang Tanggal** melalui kalender.
3. Klik tombol **"▶ Mulai Scraping"**. Browser Chrome akan terbuka.
4. Lakukan **Login Manual** di browser (isi Username, Password, Captcha).
5. Setelah berhasil login, klik tombol hijau **"✅ Lanjutkan (Sudah Login)"** di aplikasi.
6. Bot akan berjalan otomatis. Kamu bisa pantau prosesnya secara live di kotak *Proses Log*.

### Opsi 2: Mode CLI (Terminal / Backup)
Menjalankan script klasik berbasis terminal.
```bash
python mrtg_telkomcare_cli.py
```
**Alur:**
1. Script akan menanyakan opsi `1` (SID) atau `2` (Graph Title).
2. Masukkan tanggal mulai dan akhir dengan format `DD MM YYYY` (contoh: `1 1 2026`).
3. Lakukan **Login Manual** di Chrome.
4. Setelah masuk ke halaman depan web, buka terminal lagi lalu tekan **`ENTER`**.
5. Bot akan otomatis navigasi ke menu grafik dan memulai *scraping*.

---

## 📂 Struktur Output

Hasil *screenshot* akan otomatis disimpan dengan struktur hierarki seperti ini (agar mudah dicari):

```
output_mrtg_sid/                   # Untuk hasil pencarian SID
├── 20260101/
│   ├── MRTG_4700001-0021497479.png
│   ├── MRTG_2007544330.png
├── 20260102/
│   └── ...

output_mrtg_graphtitle/            # Untuk hasil pencarian Graph Title
├── 20260101/
│   ├── MRTG_3598_20260101.png
│   └── MRTG_3784_20260101.png
├── 20260102/
│   └── ...
```

---

## 🐛 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| **GUI Freeze / Not Responding** | Pastikan kamu menjalankan `mrtg_telkomcare_gui.py`. (Script ini sudah mendukung multithreading sehingga dipastikan aman dari freeze). |
| **Gambar kosong/0 bps terhapus** | Algoritma `YCbCr` terbaru sudah mendeteksi perbedaan *blank error* vs *data nol*. Namun, jika server TelkomCare down dan mengembalikan gambar *pure grayscale*, gambar akan tetap dibuang. |
| **Gagal Navigasi Sidebar** | Bot gagal ngeklik menu "Graph". Biasanya karena koneksi internet lambat setelah login. Bot akan tetap melanjutkan eksekusi jika gagal, tapi kamu harus menavigasinya secara manual jika ini terjadi. |
| **TesseractNotFoundError** | Cek kembali *path* Tesseract di file `mrtg_telkomcare_gui.py` baris instalasi (`pytesseract.tesseract_cmd`). |

---

*Dikembangkan untuk kemudahan otomasi & monitoring trafik operasional harian! 🚀*