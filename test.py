import time
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
import pytesseract
from PIL import Image

# ========== KONFIGURASI TESSERACT ==========
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ========== KONFIGURASI UMUM ==========
FOLDER_OUTPUT = "output_mrtg_sid"
SID_FILE = "SID-MRTG.txt"
MAX_RETRIES = 2  # Maks percobaan per (SID, tanggal)

# ========== BACA SID DARI FILE ==========
def baca_sid_dari_file(filepath):
    sid_list = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("SID : "):
                sid = line.replace("SID : ", "").strip()
                if sid:
                    sid_list.append(sid)
    # hilangkan duplikat
    seen = set()
    unik = []
    for s in sid_list:
        if s not in seen:
            seen.add(s)
            unik.append(s)
    return unik

# ========== FUNGSI TUTUP ALERT ==========
def tutup_alert_jika_ada(driver):
    try:
        alert = driver.switch_to.alert
        print(f"     → Alert: {alert.text[:50]}")
        alert.accept()
        time.sleep(1)
        return True
    except NoAlertPresentException:
        return False

# ========== RESET HALAMAN (F5) ==========
def reset_halaman(driver):
    print("     → Refresh halaman...")
    driver.refresh()
    time.sleep(5)
    tutup_alert_jika_ada(driver)
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "sid")))
        return True
    except:
        return False

# ========== GANTI SID (sekali untuk satu SID) ==========
def ganti_sid(driver, sid):
    try:
        input_sid = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "sid")))
        input_sid.clear()
        input_sid.send_keys(sid)
        time.sleep(0.5)
        input_sid.send_keys(Keys.ENTER)
        print(f"   → Tekan Enter untuk SID {sid}")

        time.sleep(2)
        if tutup_alert_jika_ada(driver):
            print(f"   → Alert muncul, SID {sid} tidak valid")
            return False

        tombol_grafik = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-graph")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tombol_grafik)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", tombol_grafik)
        print(f"   → Klik tombol grafik untuk SID {sid}")
        time.sleep(3)
        return True
    except UnexpectedAlertPresentException:
        tutup_alert_jika_ada(driver)
        return False
    except Exception as e:
        print(f"   → ERROR ganti SID: {str(e)[:80]}")
        return False

# ========== VALIDASI GAMBAR DENGAN OCR ==========
def is_graph_not_available(image_path):
    try:
        img = Image.open(image_path)
        img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
        text = pytesseract.image_to_string(img)
        if "Graph not available" in text or "not available" in text.lower():
            return True
        if img.width < 50 or img.height < 50:
            return True
        return False
    except Exception as e:
        print(f"     → OCR error: {e}")
        return False

# ========== AMBIL GAMBAR UNTUK SATU SID PADA SATU TANGGAL (tanpa ganti SID ulang) ==========
def ambil_gambar_tanggal(driver, sid, tanggal):
    """
    tanggal: datetime object
    return: path file sementara jika sukses (gambar valid), None jika gagal
    """
    tgl_str = tanggal.strftime("%d/%m/%Y")
    tahun = tanggal.strftime("%Y")
    bulan = tanggal.strftime("%m")
    hari = tanggal.strftime("%d")
    waktu_awal = f"{tgl_str} 00:00"
    waktu_akhir = f"{tgl_str} 23:55"
    temp_file = f"temp_{sid}_{tahun}{bulan}{hari}.png"

    for percobaan in range(1, MAX_RETRIES + 1):
        try:
            # Isi input tanggal (masih pakai elemen yang sama)
            inputs_tanggal = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Filter')]/preceding::input[not(@type='hidden')]")
            if len(inputs_tanggal) >= 2:
                input_start = inputs_tanggal[-2]
                input_end = inputs_tanggal[-1]
                driver.execute_script("arguments[0].value = arguments[1];", input_start, waktu_awal)
                driver.execute_script("arguments[0].value = arguments[1];", input_end, waktu_akhir)
            else:
                print(f"     [SKIP] Kolom tanggal tidak ditemukan")
                return None

            # Klik Filter
            tombol_filter = driver.find_element(By.XPATH, "//button[contains(normalize-space(), 'Filter')]")
            driver.execute_script("arguments[0].click();", tombol_filter)

            # Tunggu gambar grafik
            grafik_img = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'graph.php')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", grafik_img)
            time.sleep(2)

            # Screenshot
            grafik_img.screenshot(temp_file)

            # Validasi OCR
            if is_graph_not_available(temp_file):
                print(f"     [GAGAL] {tgl_str} - Graph not available")
                os.remove(temp_file)
                raise Exception("Graph not available")

            print(f"     [OK] {tgl_str}")
            return temp_file

        except Exception as e:
            print(f"     [PERCOBAAN {percobaan}] {sid} - {tgl_str} gagal: {str(e)[:60]}")
            if percobaan < MAX_RETRIES:
                # Jika gagal, coba refresh halaman dan ganti SID lagi? 
                # Tapi ini akan mengganggu loop tanggal. Alternatif: reset halaman dan ganti SID ulang.
                # Namun karena kita masih dalam satu SID, lebih baik refresh dan ganti SID lagi.
                reset_halaman(driver)
                if not ganti_sid(driver, sid):
                    return None
                time.sleep(2)
            else:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return None
    return None

# ========== PROSES SATU SID UNTUK SEMUA TANGGAL ==========
def proses_sid_untuk_range(driver, sid, start_date, end_date):
    """
    Loop tanggal dari start_date sampai end_date.
    Untuk setiap tanggal, ambil gambar dan simpan ke folder YYYYMMDD.
    return: jumlah sukses
    """
    sukses = 0
    current_date = start_date
    while current_date <= end_date:
        tgl_str = current_date.strftime("%Y%m%d")
        folder_tanggal = os.path.join(FOLDER_OUTPUT, tgl_str)
        os.makedirs(folder_tanggal, exist_ok=True)

        print(f"   → Mengambil gambar untuk {current_date.strftime('%d/%m/%Y')}")
        temp_file = ambil_gambar_tanggal(driver, sid, current_date)
        if temp_file and os.path.exists(temp_file):
            final_name = os.path.join(folder_tanggal, f"MRTG_{sid}.png")
            os.rename(temp_file, final_name)
            print(f"     ✅ Tersimpan: {final_name}")
            sukses += 1
        else:
            print(f"     ❌ Gagal untuk tanggal {current_date.strftime('%d/%m/%Y')}")

        current_date += timedelta(days=1)
        time.sleep(1)  # jeda antar tanggal
    return sukses

# ========== INPUT RENTANG TANGGAL DARI USER ==========
def input_tanggal_range():
    print("\nMasukkan rentang tanggal (contoh: 1 1 2026 untuk 01/01/2026)")
    print("=" * 50)
    tgl_mulai = input("Tanggal mulai (DD MM YYYY): ").strip().split()
    tgl_akhir = input("Tanggal akhir (DD MM YYYY): ").strip().split()
    
    if len(tgl_mulai) != 3 or len(tgl_akhir) != 3:
        print("Format salah! Gunakan: DD MM YYYY (pisah spasi)")
        return None, None
    
    try:
        start = datetime(int(tgl_mulai[2]), int(tgl_mulai[1]), int(tgl_mulai[0]))
        end = datetime(int(tgl_akhir[2]), int(tgl_akhir[1]), int(tgl_akhir[0]))
        if start > end:
            print("Tanggal mulai harus lebih awal dari tanggal akhir")
            return None, None
        return start, end
    except ValueError:
        print("Tanggal tidak valid")
        return None, None

# ========== MAIN ==========
def main():
    print("=" * 60)
    print("AUTOMATED MRTG - OPTIMIZED (per SID loop tanggal)")
    print("=" * 60)
    
    # Baca SID
    sid_list = baca_sid_dari_file(SID_FILE)
    if not sid_list:
        print("Tidak ada SID ditemukan di file", SID_FILE)
        return
    print(f"\nDitemukan {len(sid_list)} SID unik")
    
    # Input rentang tanggal
    start_date, end_date = input_tanggal_range()
    if not start_date or not end_date:
        return
    
    # Setup browser
    print("\nMembuka browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("http://telkomcare.telkom.co.id/mrtgnetcare2/graph/monitoring")
    
    print("\n" + "=" * 60)
    print("⚠️ LOGIN MANUAL, ISI CAPTCHA, LALU ENTER")
    print("=" * 60)
    input("TEKAN ENTER SETELAH LOGIN...")
    
    total_sukses = 0
    for idx, sid in enumerate(sid_list, start=1):
        print(f"\n{'='*50}")
        print(f"📁 PROSES SID {idx}/{len(sid_list)}: {sid}")
        print(f"{'='*50}")
        
        # Ganti SID sekali untuk SID ini
        if not ganti_sid(driver, sid):
            print(f"❌ Skip SID {sid} (gagal ganti SID)")
            reset_halaman(driver)
            continue
        
        # Proses semua tanggal untuk SID ini
        sukses = proses_sid_untuk_range(driver, sid, start_date, end_date)
        total_sukses += sukses
        print(f"✅ SID {sid}: {sukses}/{ (end_date - start_date).days + 1 } gambar berhasil")
        
        # Jeda antar SID
        print("   → Jeda 3 detik sebelum SID berikutnya...")
        time.sleep(3)
    
    print("\n" + "=" * 60)
    print(f"🎉 SELESAI! Total gambar berhasil: {total_sukses}")
    print(f"📁 Folder output: {FOLDER_OUTPUT}")
    print("=" * 60)
    driver.quit()

if __name__ == "__main__":
    main()