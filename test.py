import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. BIKIN FOLDER PENYIMPANAN
folder_output = "output_gambar_mrtg"
if not os.path.exists(folder_output):
    os.makedirs(folder_output)
    print(f"Folder '{folder_output}' berhasil dibuat.")

# 2. BUKA BROWSER CHROME
print("Membuka browser...")
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("http://telkomcare.telkom.co.id/mrtgnetcare2/graph/monitoring")

# 3. INTERVENSI LOGIN & PILIH SID MANUAL
print("\n" + "="*60)
print("ACTION REQUIRED: LAKUKAN INI DI BROWSER:")
print("1. Login dan selesaikan Captcha.")
print("2. Masukkan SID secara manual dan biarkan grafik awalnya muncul.")
print("="*60)
input("JIKA GRAFIK MUNCUL DI LAYAR, TEKAN ENTER DI SINI... ")
print("\nMulai mengambil data otomatis 1 bulan...\n")

# 4. SETTING TARGET
sid_target = "4700001-0021497479" # Ganti sesuai SID yang lagi dikerjain
bulan = "01"
tahun = "2026"

# 5. LOOPING TANGGAL 1 SAMPAI 31
for hari in range(1, 32):
    tgl_str = f"{hari:02d}/{bulan}/{tahun}"
    waktu_awal = f"{tgl_str} 00:00"
    waktu_akhir = f"{tgl_str} 23:55"
    
    try:
        # A. Bypass Kolom Tanggal
        inputs_tanggal = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Filter')]/preceding::input[not(@type='hidden')]")
        
        if len(inputs_tanggal) >= 2:
            input_start = inputs_tanggal[-2]
            input_end = inputs_tanggal[-1]
            driver.execute_script("arguments[0].value = arguments[1];", input_start, waktu_awal)
            driver.execute_script("arguments[0].value = arguments[1];", input_end, waktu_akhir)
        else:
            print(f" -> [WARNING] Kolom kalender tidak ditemukan untuk tanggal {tgl_str}")
            continue

        # B. Klik tombol Filter
        tombol_filter = driver.find_element(By.XPATH, "//button[contains(normalize-space(), 'Filter')]")
        driver.execute_script("arguments[0].click();", tombol_filter)
        
        print(f"[{hari}/31] Meminta data tanggal {tgl_str} ke server...")

        # C. Tunggu gambar grafik spesifik muncul (Maksimal nunggu 15 detik)
        grafik_img = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'graph.php') and contains(@src, 'local_graph_id')]"))
        )
        
        # ---> INI OBATNYA: SCROLL GAMBAR KE TENGAH LAYAR BIAR FULL <---
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", grafik_img)
        
        # D. Jeda sejenak biar browser selesai nge-scroll dan gambar kerender 100%
        time.sleep(2)
        
        # E. "Save Image As"
        nama_file = f"{folder_output}/MRTG_{sid_target}_{tahun}{bulan}{hari:02d}.png"
        grafik_img.screenshot(nama_file)
        print(f" -> Sukses save grafik: {nama_file}")
        
    except Exception as e:
        print(f" -> [ERROR] Gagal memproses tanggal {tgl_str}. Timeout atau grafik kosong.")

print("\nSEMUA PROSES SELESAI! Cek folder:", folder_output)