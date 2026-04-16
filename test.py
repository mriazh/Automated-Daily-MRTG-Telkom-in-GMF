import time
import os
import io
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
# Sesuaikan path jika perlu (default install di C:\Program Files\Tesseract-OCR\tesseract.exe)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ========== KONFIGURASI SCRIPT ==========
FOLDER_OUTPUT = "output_mrtg_all_sid"
BULAN = "01"
TAHUN = "2026"
TANGGAL_MULAI = 1
TANGGAL_AKHIR = 31
MAX_RETRIES = 2  # Maksimal percobaan ulang per tanggal
SID_FILE = "SID-MRTG.txt"

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
    # Hilangkan duplikat
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
        print(f"     → Alert terdeteksi: {alert.text[:80]}")
        alert.accept()
        time.sleep(1)
        return True
    except NoAlertPresentException:
        return False

# ========== RESET HALAMAN (F5) ==========
def reset_halaman(driver):
    print("     → Melakukan refresh halaman (F5)...")
    driver.refresh()
    time.sleep(5)
    tutup_alert_jika_ada(driver)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "sid"))
        )
        return True
    except:
        return False

# ========== GANTI SID (INPUT + ENTER + KLIK TOMBOL GRAFIK) ==========
def ganti_sid(driver, sid):
    try:
        input_sid = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "sid"))
        )
        input_sid.clear()
        input_sid.send_keys(sid)
        time.sleep(0.5)
        input_sid.send_keys(Keys.ENTER)
        print(f"   → Tekan Enter untuk SID {sid}")

        time.sleep(2)
        if tutup_alert_jika_ada(driver):
            print(f"   → Alert muncul, SID {sid} mungkin tidak valid")
            return False

        tombol_grafik = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-graph"))
        )
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
    """
    Membaca teks dari gambar menggunakan OCR.
    Return True jika ditemukan kata "Graph not available", else False.
    """
    try:
        img = Image.open(image_path)
        # Resize sedikit agar OCR lebih akurat (opsional)
        img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
        text = pytesseract.image_to_string(img)
        # Cek berbagai kemungkinan variasi
        if "Graph not available" in text or "not available" in text.lower():
            return True
        # Cek juga jika gambar terlalu kecil atau kosong
        if img.width < 50 or img.height < 50:
            return True
        return False
    except Exception as e:
        print(f"     → OCR error: {e}")
        # Jika OCR gagal, fallback ke ukuran file (opsional)
        return False

# ========== AMBIL GAMBAR UNTUK SATU TANGGAL DENGAN RETRY & OCR ==========
def ambil_gambar_tanggal(driver, sid, folder_target, tahun, bulan, hari):
    tgl_str = f"{hari:02d}/{bulan}/{tahun}"
    waktu_awal = f"{tgl_str} 00:00"
    waktu_akhir = f"{tgl_str} 23:55"
    nama_file = f"{folder_target}/MRTG_{sid}_{tahun}{bulan}{hari:02d}.png"

    for percobaan in range(1, MAX_RETRIES + 1):
        try:
            # 1. Isi input tanggal
            inputs_tanggal = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Filter')]/preceding::input[not(@type='hidden')]")
            if len(inputs_tanggal) >= 2:
                input_start = inputs_tanggal[-2]
                input_end = inputs_tanggal[-1]
                driver.execute_script("arguments[0].value = arguments[1];", input_start, waktu_awal)
                driver.execute_script("arguments[0].value = arguments[1];", input_end, waktu_akhir)
            else:
                print(f"     [SKIP] Kolom tanggal tidak ditemukan")
                return False

            # 2. Klik tombol Filter
            tombol_filter = driver.find_element(By.XPATH, "//button[contains(normalize-space(), 'Filter')]")
            driver.execute_script("arguments[0].click();", tombol_filter)

            # 3. Tunggu gambar grafik muncul
            grafik_img = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'graph.php')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", grafik_img)
            time.sleep(2)

            # 4. Screenshot
            grafik_img.screenshot(nama_file)

            # 5. VALIDASI DENGAN OCR
            if is_graph_not_available(nama_file):
                print(f"     [GAGAL] {tgl_str} - Terdeteksi 'Graph not available' (OCR)")
                os.remove(nama_file)
                raise Exception("Graph not available")

            # 6. Jika valid, sukses
            print(f"     [OK] {tgl_str}")
            return True

        except Exception as e:
            print(f"     [PERCOBAAN {percobaan}/{MAX_RETRIES}] {tgl_str} gagal: {str(e)[:60]}")
            if percobaan < MAX_RETRIES:
                # Reset halaman dan ganti SID lagi
                reset_halaman(driver)
                if not ganti_sid(driver, sid):
                    return False
                time.sleep(2)
            else:
                # Hapus file jika masih error (biar gak numpuk)
                if os.path.exists(nama_file):
                    os.remove(nama_file)
                return False
    return False

# ========== AMBIL SEMUA TANGGAL UNTUK SATU SID ==========
def ambil_gambar_per_sid(driver, sid, folder_target):
    os.makedirs(folder_target, exist_ok=True)
    success_count = 0
    for hari in range(TANGGAL_MULAI, TANGGAL_AKHIR + 1):
        if ambil_gambar_tanggal(driver, sid, folder_target, TAHUN, BULAN, hari):
            success_count += 1
        else:
            print(f"     [WARNING] Gagal permanen untuk tanggal {hari:02d}")
        time.sleep(1)  # Jeda ringan
    return success_count

# ========== MAIN PROGRAM ==========
def main():
    print("=" * 60)
    print("AUTOMATED MRTG - VALIDASI OCR (TESSERACT)")
    print("=" * 60)

    # Baca daftar SID
    sid_list = baca_sid_dari_file(SID_FILE)
    print(f"\nDitemukan {len(sid_list)} SID unik:")
    for i, sid in enumerate(sid_list, 1):
        print(f"  {i}. {sid}")

    # Setup ChromeDriver
    print("\nMembuka browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("http://telkomcare.telkom.co.id/mrtgnetcare2/graph/monitoring")

    # Login manual
    print("\n" + "=" * 60)
    print("⚠️  ACTION REQUIRED:")
    print("   1. Login dan selesaikan CAPTCHA")
    print("   2. Biarkan halaman terbuka (jangan ditutup)")
    print("   3. Pastikan grafik default muncul")
    print("=" * 60)
    input("\n✅ TEKAN ENTER SETELAH LOGIN BERHASIL... ")

    # Buat folder utama
    os.makedirs(FOLDER_OUTPUT, exist_ok=True)

    total_sukses = 0
    for idx, sid in enumerate(sid_list, start=1):
        print(f"\n{'='*50}")
        print(f"📁 PROSES SID {idx}/{len(sid_list)}: {sid}")
        print(f"{'='*50}")

        if not ganti_sid(driver, sid):
            print(f"❌ Skip SID {sid} (gagal ganti SID)")
            reset_halaman(driver)
            continue

        folder_sid = os.path.join(FOLDER_OUTPUT, sid.replace("-", "_"))
        jumlah_berhasil = ambil_gambar_per_sid(driver, sid, folder_sid)
        total_sukses += jumlah_berhasil
        print(f"✅ SID {sid}: {jumlah_berhasil}/31 gambar valid")

        # Jeda antar SID biar server nggak kaget
        print("   → Jeda 3 detik sebelum ke SID berikutnya...")
        time.sleep(3)

    # Selesai
    print("\n" + "=" * 60)
    print(f"🎉 SELESAI! Total gambar valid: {total_sukses}")
    print(f"📁 Folder output: {FOLDER_OUTPUT}")
    print("=" * 60)

    driver.quit()

if __name__ == "__main__":
    main()