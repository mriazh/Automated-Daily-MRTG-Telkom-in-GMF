# 🚀 MRTG TelkomCare Screenshot Bot

Bot otomatisasi untuk mengambil screenshot grafik MRTG dari portal TelkomCare secara massal. Dirancang untuk keandalan tinggi, batch processing multi-tanggal, dan hasil gambar presisi.

---

## ✨ Fitur Utama

*   **🎯 Nuclear Isolation Protocol**: Mengisolasi elemen grafik ke koordinat (0,0) secara total sebelum screenshot. Menjamin hasil bersih dan presisi tanpa gangguan elemen UI lain.
*   **🔄 Self-Healing & Auto-Recovery**: Logika retry otomatis untuk menangani kendala server TelkomCare (JSON Error, Stale Element, atau Graph Not Available) hingga 5x percobaan.
*   **👻 Mode Gaib (Stealth Mode)**: Setelah proses login manual, jendela browser akan disamarkan dan disembunyikan agar tidak mengganggu aktivitas kerja di layar.
*   **🖥️ Dual Interface**: Mendukung penggunaan lewat **CLI (Command Line)** untuk performa stabil dan **GUI (Desktop App)** untuk kemudahan penggunaan.
*   **📅 Multi-Date Batching**: Mendukung pengambilan data batch untuk rentang tanggal tertentu dalam satu kali sesi.
*   **🕵️ Audit Trail**: Pencatatan detail setiap aktivitas (Sukses, Retry, atau Gagal) ke dalam file `mrtg_process.log`.

---

## 🛠️ Persiapan & Instalasi

### 1. Prasyarat Sistem
*   Pastikan **Python 3.10** atau versi terbaru sudah terinstall di sistem Anda.
*   Saat instalasi Python, pastikan opsi **"Add Python to PATH"** sudah dicentang.

### 2. Instalasi Dependencies
Buka terminal atau Command Prompt di dalam direktori folder bot ini, kemudian jalankan perintah berikut:
```bash
pip install -r requirements.txt
```

---

## 🚀 Panduan Penggunaan

### Langkah 1: Konfigurasi Daftar Target
Siapkan daftar target yang ingin diproses pada file teks berikut:
*   `SID-MRTG.txt`: Untuk daftar SID (Format: `SID : 4700001-xxxxxxx`)
*   `GRAPH-TITLE-MRTG.txt`: Untuk daftar Judul Grafik (Format: `Graph-title : Judul_Grafik`)

### Langkah 2: Menjalankan Bot
Pilih salah satu metode berikut:
*   **Mode CLI**: Jalankan perintah `python mrtg_telkomcare_cli.py`
*   **Mode GUI**: Jalankan perintah `python mrtg_telkomcare_gui.py`

### Langkah 3: Alur Kerja Proses
1.  **Pilih Mode**: Masukkan pilihan mode (1 untuk SID, 2 untuk Graph Title).
2.  **Rentang Tanggal**: Masukkan tanggal mulai dan akhir proses (Format: `DD MM YYYY`).
3.  **Manual Login**: Browser akan terbuka, silakan lakukan login ke portal TelkomCare.
4.  **Eksekusi**: Setelah berhasil login, tekan **Enter** di terminal (CLI) atau klik tombol **Lanjutkan** (GUI).
5.  **Monitoring**: Bot akan berjalan secara otomatis di latar belakang. Pantau progres hingga mencapai 100%.

---

## 📁 Struktur Output
Hasil screenshot akan disimpan secara otomatis pada folder berikut:
*   `output_mrtg_sid/` (Mode SID)
*   `output_mrtg_graphtitle/` (Mode Graph Title)
*   Gambar dikelompokkan ke dalam sub-folder berdasarkan tanggal (Contoh: `20260401/`).

---

## ⚙️ Konfigurasi Lanjutan (`config.py`)
Anda dapat menyesuaikan parameter operasional pada file `config.py`:
*   `MAX_RETRIES`: Jumlah percobaan ulang jika gagal input target (Default: 5).
*   `MAX_GRAPH_RETRIES`: Jumlah percobaan recovery jika grafik belum ter-render (Default: 5).
*   `WAIT_TIMEOUT`: Durasi tunggu loading elemen halaman (detik).

---

## ⚠️ Troubleshooting
*   **Browser Muncul Kembali**: Bot melakukan re-hide otomatis setiap kali melakukan refresh halaman. Jika browser muncul, tunggu beberapa saat hingga bot menyembunyikannya kembali.
*   **Grafik Kosong/Zonk**: Biasanya disebabkan data pada tanggal tersebut belum tersedia di server TelkomCare. Bot akan mencoba recovery otomatis sebelum menandainya sebagai gagal.
*   **Gagal Me-load Halaman**: Pastikan koneksi internet stabil karena bot bergantung pada respon AJAX dari server.

---
**Dibuat untuk Efisiensi Kerja Tim Telkom - GMF AeroAsia.** 🍻