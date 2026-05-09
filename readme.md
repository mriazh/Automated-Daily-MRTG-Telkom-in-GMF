# 🚀 MRTG TelkomCare Screenshot Bot (PRO VERSION)

Bot otomatisasi super presisi untuk mengambil screenshot grafik MRTG dari portal TelkomCare. Dirancang untuk keandalan tinggi, batch processing multi-tanggal, dan hasil gambar pixel-perfect.

---

## ✨ Fitur Unggulan

- **🎯 Nuclear Isolation Protocol**: Mengisolasi elemen grafik ke koordinat (0,0) secara total sebelum screenshot. Menjamin hasil **Pixel-Perfect** dan bebas dari gangguan sidebar/navbar yang "mencong".
- **👻 Gaib Mode (Hidden Browser)**: Browser berjalan secara otomatis di latar belakang (background) setelah proses login manual, sehingga tidak mengganggu aktivitas kerja Anda di layar.
- **🔄 Smart Auto-Recovery**: Dilengkapi logika retry pintar untuk menangani *Stale Element Reference* dan *DataTables JSON Error* secara otomatis.
- **🖥️ Dual Mode Interface**: 
  - **CLI Mode**: Super cepat dan ringan untuk power users.
  - **GUI Mode**: Berbasis PySide6 yang modern dengan tombol **STOP** darurat dan indikator warna yang informatif.
- **📅 Multi-Date Batching**: Masukkan rentang tanggal, dan bot akan mengambil semua data secara urut tanpa intervensi manual.
- **📑 Detailed Audit Logging**: Semua aktivitas (Sukses, Gagal, Retry) dicatat secara mendetail di `mrtg_process.log`.

---

## 🛠️ Persiapan & Instalasi

1.  **Install Python**: Pastikan Python 3.10+ sudah terinstall.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Setup Tesseract (Opsional)**: Pastikan Tesseract OCR terinstall jika ingin menggunakan fitur validasi teks gambar.
4.  **Input Data**:
    - Isi file `SID-MRTG.txt` dengan format `SID : <nomor_sid>`
    - Isi file `GRAPH-TITLE-MRTG.txt` dengan format `Graph-title : <judul_grafik>`

---

## 🚀 Cara Menjalankan

### Versi CLI (Command Line)
Sangat cocok untuk pemrosesan cepat.
```bash
python mrtg_telkomcare_cli.py
```

### Versi GUI (Desktop App)
Sangat cocok untuk penggunaan harian yang praktis.
```bash
python mrtg_telkomcare_gui.py
```

---

## 📝 Alur Kerja Bot
1.  **Login Manual**: Browser akan terbuka, silakan lakukan login manual (input CAPTCHA jika ada).
2.  **Lanjutkan**: Klik tombol "Lanjutkan" di GUI atau tekan Enter di CLI.
3.  **Gaib Mode**: Browser akan menghilang secara otomatis dan bekerja "di bawah tanah".
4.  **Monitoring**: Pantau progres lewat Progress Bar (CLI) atau Log Viewer (GUI).
5.  **Output**: Hasil gambar akan tersimpan di folder `output_mrtg_sid` atau `output_mrtg_graphtitle` sesuai tanggal.

---

## 📁 Struktur Folder
```text
.
├── mrtg_telkomcare_cli.py    # Mesin utama (CLI)
├── mrtg_telkomcare_gui.py    # Aplikasi Desktop (GUI)
├── SID-MRTG.txt              # Input SID
├── GRAPH-TITLE-MRTG.txt      # Input Judul Grafik
├── mrtg_process.log          # File Audit Trail
└── output_mrtg_xxx/          # Hasil Screenshot (Per Tanggal)
```

---

## ⚠️ Catatan Penting
- **Windows DPI Scaling**: Bot ini sudah dioptimalkan untuk Windows dengan scaling di atas 100%.
- **Stable Connection**: Gunakan koneksi yang stabil karena bot sangat bergantung pada respon AJAX dari server TelkomCare.

---
**Dibuat dengan ❤️ untuk efisiensi kerja tim Telkom-GMF.**