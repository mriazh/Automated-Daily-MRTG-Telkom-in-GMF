# 🚀 MRTG TelkomCare Screenshot Bot

> Bot otomatisasi untuk mengambil screenshot grafik MRTG dari portal TelkomCare secara massal. Dirancang untuk keandalan tinggi, batch processing multi-tanggal, dan hasil gambar presisi.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python) ![Selenium](https://img.shields.io/badge/Selenium-4.x-green) ![PySide6](https://img.shields.io/badge/PySide6-GUI-orange) ![PyInstaller](https://img.shields.io/badge/PyInstaller-.exe-red) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Fitur Utama

- **🎯 Nuclear Isolation Protocol** — Mengisolasi elemen grafik ke koordinat (0,0) secara total sebelum screenshot. Menjamin hasil bersih dan presisi tanpa gangguan elemen UI lain.
- **🔄 Self-Healing & Auto-Recovery** — Logika retry otomatis untuk menangani kendala server TelkomCare (JSON Error, Stale Element, atau Graph Not Available) hingga 5x percobaan.
- **👻 Stealth Mode** — Setelah proses login manual, jendela browser akan disembunyikan otomatis agar tidak mengganggu aktivitas kerja di layar.
- **🖥️ Dual Interface** — Mendukung penggunaan lewat **CLI (Command Line)** untuk performa stabil dan **GUI (Desktop App)** untuk kemudahan penggunaan non-teknis.
- **📅 Multi-Date Batching** — Mendukung pengambilan data batch untuk rentang tanggal tertentu dalam satu kali sesi.
- **🕵️ Audit Trail** — Pencatatan detail setiap aktivitas (Sukses, Retry, atau Gagal) ke dalam file `mrtg_process.log`.

---

## 🏗️ Arsitektur

```
Automated-Daily-MRTG-Telkom-in-GMF/
├── mrtg_telkomcare_cli.py   ← Entry point mode CLI (Command Line)
├── mrtg_telkomcare_gui.py   ← Entry point mode GUI (Desktop App)
├── config.py                ← Konfigurasi terpusat (timeout, retry, path)
├── SID-MRTG.txt             ← Daftar SID target (Mode SID)
├── GRAPH-TITLE-MRTG.txt     ← Daftar Graph Title target (Mode Graph Title)
├── requirements.txt         ← Dependencies Python
├── MRTG_TelkomCare_Bot.spec ← PyInstaller spec file (build .exe)
├── build_exe.bat            ← Script build otomatis (Windows)
├── output_mrtg_sid/         ← Hasil screenshot Mode SID (otomatis dibuat)
├── output_mrtg_graphtitle/  ← Hasil screenshot Mode Graph Title (otomatis dibuat)
├── temp_screenshots/        ← Folder cache sementara (otomatis dibuat)
├── mrtg_process.log         ← Log aktivitas (otomatis dibuat)
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🛠️ Instalasi

### 1. Prasyarat Sistem

| Software | Keterangan |
|----------|------------|
| **Python 3.10+** | [Download di sini](https://www.python.org/downloads/) |
| **Google Chrome** | Browser versi terbaru |
| **Internet** | Akses ke `telkomcare.telkom.co.id` |

Saat instalasi Python, pastikan opsi **"Add Python to PATH"** sudah dicentang.

### 2. Clone Repository

```bash
git clone https://github.com/AdimasP/Automated-Daily-MRTG-Telkom-in-GMF.git
cd Automated-Daily-MRTG-Telkom-in-GMF
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Konfigurasi

### File `SID-MRTG.txt`

Isi file ini dengan daftar SID yang ingin diambil datanya. Satu SID per baris.

```text
SID : 4700001-0021497479
SID : 4700001-0020265222
SID : 2007544330
```

### File `GRAPH-TITLE-MRTG.txt`

Isi file ini dengan daftar Graph Title. Satu Graph Title per baris.

```text
Graph-title : 3598
Graph-title : 3784
```

### File `config.py` (Konfigurasi Lanjutan)

Edit file ini untuk menyesuaikan parameter operasional:

| Parameter | Default | Keterangan |
|-----------|---------|------------|
| `MAX_RETRIES` | `5` | Jumlah percobaan ulang jika gagal input target |
| `MAX_GRAPH_RETRIES` | `5` | Jumlah percobaan recovery jika grafik belum ter-render |
| `WAIT_TIMEOUT` | `10` | Timeout standar tunggu elemen (detik) |
| `LONG_TIMEOUT` | `15` | Timeout untuk proses loading yang lebih lama (detik) |
| `LOGIN_WAIT` | `15` | Waktu tunggu untuk elemen login muncul (detik) |

---

## 🚀 Cara Penggunaan

### Langkah 1: Siapkan Daftar Target

Pilih salah satu mode dan isi file teks yang sesuai (lihat bagian Konfigurasi di atas):
- **Mode SID** → Edit `SID-MRTG.txt`
- **Mode Graph Title** → Edit `GRAPH-TITLE-MRTG.txt`

### Langkah 2: Jalankan Bot

Pilih salah satu interface sesuai kebutuhan:

```bash
# Mode CLI (Command Line Interface) — lebih stabil dan ringan
python mrtg_telkomcare_cli.py

# Mode GUI (Graphical User Interface) — lebih mudah untuk pengguna non-teknis
python mrtg_telkomcare_gui.py
```

### Langkah 3: Ikuti Alur Kerja

1. **Pilih Mode** — Masukkan angka `1` untuk Mode SID atau `2` untuk Mode Graph Title.
2. **Masukkan Rentang Tanggal** — Format input: `DD MM YYYY` (contoh: `01 05 2026`).
3. **Login Manual** — Browser Chrome akan terbuka otomatis. Lakukan login ke portal TelkomCare menggunakan akun Anda.
4. **Mulai Proses** — Setelah berhasil login:
   - **CLI**: Tekan **Enter** di terminal.
   - **GUI**: Klik tombol **Lanjutkan**.
5. **Tunggu Selesai** — Bot berjalan otomatis di latar belakang. Chrome akan tersembunyi. Pantau progres di terminal atau GUI hingga mencapai 100%.

### Langkah 4: Ambil Hasil

Screenshot tersimpan di folder berikut (dikelompokkan per tanggal):

```
output_mrtg_sid/
└── 20260501/
    ├── 4700001-0021497479.png
    └── 4700001-0020265222.png

output_mrtg_graphtitle/
└── 20260501/
    ├── 3598.png
    └── 3784.png
```

---

## 🔨 Build ke .exe (Opsional)

Untuk membuat file `.exe` portable agar bisa dijalankan tanpa install Python:

```bash
# Jalankan build script otomatis (Windows)
build_exe.bat
```

Atau jalankan manual:

```bash
pip install pyinstaller
pyinstaller MRTG_TelkomCare_Bot.spec --noconfirm
```

Hasil build tersedia di folder `dist\`.

---

## ⚠️ Troubleshooting

**Q: Browser Chrome muncul kembali padahal harusnya tersembunyi?**
> A: Bot melakukan re-hide otomatis setiap kali refresh halaman. Jika browser sesekali muncul, tunggu beberapa saat — bot akan menyembunyikannya kembali secara otomatis.

**Q: Grafik bertuliskan "Graph Not Available" atau hasilnya kosong?**
> A: Biasanya data pada tanggal tersebut belum tersedia di server TelkomCare. Bot akan mencoba recovery otomatis (hingga 5x) sebelum menandainya sebagai gagal di log.

**Q: Bot gagal me-load halaman / timeout terus-menerus?**
> A: Pastikan koneksi internet stabil karena bot bergantung pada respons AJAX dari server TelkomCare. Coba naikkan nilai `WAIT_TIMEOUT` dan `LONG_TIMEOUT` di `config.py`.

**Q: Bagaimana cara cek log error secara detail?**
> A: Buka file `mrtg_process.log` di folder utama. Semua aktivitas (Sukses, Retry, Gagal) tercatat lengkap beserta timestamp.

---

## 📄 License

[MIT License](LICENSE)