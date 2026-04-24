# 📊 MRTG Automation Tool for TelkomCare

**Otomatis screenshot grafik MRTG dari TelkomCare untuk banyak SID atau Graph Title, dengan validasi OCR dan retry otomatis.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-green)](https://selenium.dev)
[![Tesseract](https://img.shields.io/badge/Tesseract-5.x-orange)](https://github.com/UB-Mannheim/tesseract)

---

## 📌 Fitur Utama

- ✅ **Multi SID & Graph Title** – Baca daftar dari file teks.
- ✅ **Rentang tanggal fleksibel** – Input manual mulai dan akhir.
- ✅ **Validasi gambar dengan OCR** – Deteksi "Graph not available" dengan Tesseract dan memvalidasi resolusi gambar.
- ✅ **Retry otomatis** – Jika gagal, ulang hingga 2 kali.
- ✅ **Group by tanggal** – Output folder `YYYYMMDD/MRTG_<ID>.png`.
- ✅ **Optimasi kecepatan** – Ganti SID/title sekali, lalu loop tanggal.
- ✅ **Handle modal popup** – Khusus untuk Graph Title.
- ✅ **Login manual satu kali** – Aman untuk CAPTCHA dan MFA.

---

## 🛠️ Prasyarat

| Software | Keterangan |
|----------|-------------|
| **Python 3.8+** | [Download](https://www.python.org/downloads/) |
| **Google Chrome** | Browser terbaru |
| **Tesseract OCR** | [Download](https://github.com/UB-Mannheim/tesseract/wiki) – pilih `tesseract-ocr-w64-setup-5.5.0.20241111.exe`, **centang "Add to PATH"** |
| **Internet** | Akses ke `telkomcare.telkom.co.id` |

### Environment Variables (PATH)
```
C:\Users\<username>\AppData\Local\Python\bin
C:\Users\<username>\AppData\Local\Python\pythoncore-3.14-64\Scripts
C:\Program Files\Tesseract-OCR
```
> Pastikan `tesseract.exe` bisa diakses dari command line dengan `tesseract --version`.

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
   pip install selenium webdriver-manager pillow pytesseract
   ```

4. **Pastikan Tesseract terdeteksi**  
   Edit baris berikut di kedua script jika path Anda berbeda:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

---

## 📁 Persiapan File Input

### Untuk SID – `SID-MRTG.txt`
Buat file dengan format satu baris:
```
SID : 4700001-0021497479
SID : 4700001-0020265222
SID : 2007544330
...
```

### Untuk Graph Title – `GRAPH-TITLE-MRTG.txt`
Buat file dengan format:
```
Graph-title : 3598
Graph-title : 3784
```

> Letakkan file-file ini di folder yang sama dengan script.

---

## 🚀 Cara Penggunaan

### 1. Script untuk SID (menggunakan `mrtg_telkomcare_sid.py`)

```bash
python mrtg_telkomcare_sid.py
```

**Alur:**
- Masukkan rentang tanggal di terminal (contoh: `1 1 2026` dan `31 1 2026`).
- Browser terbuka → Login manual + CAPTCHA + MFA.
- Setelah berhasil login, tekan Enter di terminal untuk memulai proses otomatisasi.
- Script akan:
  - Membaca semua SID dari file.
  - Untuk setiap SID: ganti SID → loop tanggal → filter → screenshot → simpan.
- Output folder: `output_mrtg_sid/YYYYMMDD/MRTG_<SID>.png`

### 2. Script untuk Graph Title (menggunakan `mrtg_telkomcare_graphtitle.py`)

```bash
python mrtg_telkomcare_graphtitle.py
```

**Alur:**
- Sama seperti SID, tapi menggunakan input `graphtitle` dan modal popup.
- Setelah selesai satu title, halaman di-refresh untuk membersihkan state.
- Output folder: `output_mrtg_graphtitle/YYYYMMDD/MRTG_<title>_YYYYMMDD.png`

> **Catatan:** Untuk Graph Title, karena modal tidak bisa di-reset sempurna, script akan refresh halaman setiap berganti title. Ini memastikan gambar yang diambil sesuai.

---

## 📂 Struktur Output

```
output_mrtg_sid/                   # Untuk SID
├── 20260101/
│   ├── MRTG_4700001-0021497479.png
│   ├── MRTG_4700001-0020265222.png
│   └── ...
├── 20260102/
│   └── ...
└── ...

output_mrtg_graphtitle/            # Untuk Graph Title
├── 20260101/
│   ├── MRTG_3598_20260101.png
│   └── MRTG_3784_20260101.png
├── 20260102/
│   └── ...
└── ...
```

---

## 🧪 Contoh Penggunaan (Terminal)

```
============================================================
AUTOMATED MRTG - OPTIMIZED (per SID loop tanggal)
============================================================

Ditemukan 18 SID unik

Masukkan rentang tanggal (contoh: 1 1 2026 untuk 01/01/2026)
==================================================
Tanggal mulai (DD MM YYYY): 1 1 2026
Tanggal akhir (DD MM YYYY): 2 1 2026

Membuka browser...

============================================================
⚠️ LOGIN MANUAL, ISI CAPTCHA, LALU ENTER
============================================================
TEKAN ENTER SETELAH LOGIN...

==================================================
📁 PROSES SID 1/18: 4700001-0021497479
==================================================
   → Tekan Enter untuk SID 4700001-0021497479
   → Klik tombol grafik untuk SID 4700001-0021497479
   → Mengambil gambar untuk 01/01/2026
     [OK] 01/01/2026
     ✅ Tersimpan: output_mrtg_sid/20260101/MRTG_4700001-0021497479.png
   → Mengambil gambar untuk 02/01/2026
     [OK] 02/01/2026
     ✅ Tersimpan: output_mrtg_sid/20260102/MRTG_4700001-0021497479.png
✅ SID 4700001-0021497479: 2/2 gambar berhasil
...
🎉 SELESAI! Total gambar berhasil: 36
```

---

## ⚙️ Konfigurasi Lanjutan

| Variabel (di dalam script) | Default | Keterangan |
|----------------------------|---------|-------------|
| `MAX_RETRIES` | 2 | Jumlah percobaan ulang jika gambar gagal |
| `FOLDER_OUTPUT` | `output_mrtg_sid` / `output_mrtg_graphtitle` | Folder hasil |
| `SID_FILE` / `GRAPH_TITLE_FILE` | `SID-MRTG.txt` / `GRAPH-TITLE-MRTG.txt` | Nama file input |

---

## 🐛 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `TesseractNotFoundError` | Pastikan path tesseract sudah benar di script dan Tesseract terinstal. Cek dengan `tesseract --version` di CMD. |
| Alert `DataTables warning` | SID tidak valid. Script akan skip otomatis. |
| Gambar ganda atau salah title | Untuk Graph Title, script sudah melakukan refresh antar title. Pastikan file `GRAPH-TITLE-MRTG.txt` berisi title yang benar. |
| Modal tidak terbuka | Periksa apakah tombol `a.btn-graph` masih ada. Bisa juga coba manual melalui browser. |
| Stale element reference | Script sudah menggunakan JavaScript dan loop pencarian ulang. Jika masih terjadi, coba tambah `time.sleep()` di beberapa bagian. |

---

**Selamat mencoba dan semoga membantu pekerjaan monitoring MRTG! 🚀**