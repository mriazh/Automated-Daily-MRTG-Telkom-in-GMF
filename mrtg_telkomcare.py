import time
import os
import sys
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

# ========== KONFIGURASI ==========
MAX_RETRIES = 2

CONFIG = {
    "sid": {
        "file": "SID-MRTG.txt",
        "output": "output_mrtg_sid",
        "url": "http://telkomcare.telkom.co.id/mrtgnetcare2/graph/monitoring",
        "input_name": "sid",
        "prefix": "SID : ",
        "label": "SID"
    },
    "graphtitle": {
        "file": "GRAPH-TITLE-MRTG.txt",
        "output": "output_mrtg_graphtitle",
        "url": "https://telkomcare.telkom.co.id/mrtgnetcare2/graph",
        "input_name": "graphtitle",
        "prefix": "Graph-title : ",
        "label": "Graph Title"
    }
}

# ========== BACA ITEM DARI FILE ==========
def baca_item_dari_file(filepath, prefix):
    items = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(prefix):
                item = line.replace(prefix, "").strip()
                if item:
                    items.append(item)
    return list(dict.fromkeys(items))  # hapus duplikat, jaga urutan

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
def reset_halaman(driver, input_name):
    print("     → Refresh halaman...")
    driver.refresh()
    time.sleep(5)
    tutup_alert_jika_ada(driver)
    try:
        for _ in range(20):
            try:
                driver.find_element(By.NAME, input_name)
                return True
            except:
                time.sleep(0.5)
        return False
    except:
        return False

# ========== VALIDASI GAMBAR DENGAN OCR ==========
def is_graph_not_available(image_path):
    try:
        img = Image.open(image_path)

        # Cek ukuran terlalu kecil
        if img.width < 50 or img.height < 50:
            return True

        # Fallback visual check (berjalan meski tanpa Tesseract)
        grayscale = img.convert("L")
        pixels = list(grayscale.tobytes())
        if len(pixels) > 0:
            avg_brightness = sum(pixels) / len(pixels)
            # Hitung variance (seberapa seragam warnanya)
            variance = sum((p - avg_brightness) ** 2 for p in pixels) / len(pixels)

            # Gambar "No graph" = hampir seluruhnya abu/putih dengan variance rendah
            if avg_brightness > 200 and variance < 1500:
                print(f"     → Terdeteksi blank/error (brightness={avg_brightness:.0f}, variance={variance:.0f})")
                return True

        # OCR check (jika Tesseract terinstall)
        try:
            img_resized = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            text = pytesseract.image_to_string(img_resized).lower()
            error_keywords = ["no graph", "graph not available", "not available", "no data"]
            for keyword in error_keywords:
                if keyword in text:
                    return True
        except Exception:
            pass  # Tesseract tidak terinstall, lanjut pakai visual check saja

        return False
    except Exception as e:
        print(f"     → Validasi error: {e}")
        return False

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

# ========== SETUP BROWSER ==========
def setup_browser():
    print("\nMembuka browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception:
        print(f"\n[WARNING] Download ChromeDriver otomatis diblokir jaringan. Mencoba fallback...")
        try:
            driver = webdriver.Chrome(options=options)
        except Exception:
            print("\n[ERROR FATAL] Gagal membuka Chrome. Silakan letakkan file 'chromedriver.exe' secara manual di folder ini.")
            sys.exit(1)
    return driver


# =====================================================================
# MODE SID
# =====================================================================

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

def ambil_gambar_tanggal_sid(driver, sid, tanggal):
    tgl_str = tanggal.strftime("%d/%m/%Y")
    tahun = tanggal.strftime("%Y")
    bulan = tanggal.strftime("%m")
    hari = tanggal.strftime("%d")
    waktu_awal = f"{tgl_str} 00:00"
    waktu_akhir = f"{tgl_str} 23:55"
    temp_file = f"temp_{sid}_{tahun}{bulan}{hari}.png"

    for percobaan in range(1, MAX_RETRIES + 1):
        try:
            inputs_tanggal = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Filter')]/preceding::input[not(@type='hidden')]")
            if len(inputs_tanggal) >= 2:
                input_start = inputs_tanggal[-2]
                input_end = inputs_tanggal[-1]
                driver.execute_script("arguments[0].value = arguments[1];", input_start, waktu_awal)
                driver.execute_script("arguments[0].value = arguments[1];", input_end, waktu_akhir)
            else:
                print(f"     [SKIP] Kolom tanggal tidak ditemukan")
                return None

            tombol_filter = driver.find_element(By.XPATH, "//button[contains(normalize-space(), 'Filter')]")
            driver.execute_script("arguments[0].click();", tombol_filter)

            grafik_img = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'graph.php')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", grafik_img)
            time.sleep(2)

            grafik_img.screenshot(temp_file)

            if is_graph_not_available(temp_file):
                print(f"     [GAGAL] {tgl_str} - Graph not available")
                os.remove(temp_file)
                raise Exception("Graph not available")

            print(f"     [OK] {tgl_str}")
            return temp_file

        except Exception as e:
            print(f"     [PERCOBAAN {percobaan}] {sid} - {tgl_str} gagal: {str(e)[:60]}")
            if percobaan < MAX_RETRIES:
                reset_halaman(driver, "sid")
                if not ganti_sid(driver, sid):
                    return None
                time.sleep(2)
            else:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return None
    return None

def run_mode_sid(driver, sid_list, start_date, end_date, folder_output):
    total_sukses = 0
    for idx, sid in enumerate(sid_list, start=1):
        print(f"\n{'='*50}")
        print(f"📁 PROSES SID {idx}/{len(sid_list)}: {sid}")
        print(f"{'='*50}")

        if not ganti_sid(driver, sid):
            print(f"❌ Skip SID {sid} (gagal ganti SID)")
            reset_halaman(driver, "sid")
            continue

        sukses = 0
        current_date = start_date
        while current_date <= end_date:
            tgl_str = current_date.strftime("%Y%m%d")
            folder_tanggal = os.path.join(folder_output, tgl_str)
            os.makedirs(folder_tanggal, exist_ok=True)

            print(f"   → Mengambil gambar untuk {current_date.strftime('%d/%m/%Y')}")
            temp_file = ambil_gambar_tanggal_sid(driver, sid, current_date)
            if temp_file and os.path.exists(temp_file):
                final_name = os.path.join(folder_tanggal, f"MRTG_{sid}.png")
                os.replace(temp_file, final_name)
                print(f"     ✅ Tersimpan: {final_name}")
                sukses += 1
            else:
                print(f"     ❌ Gagal untuk tanggal {current_date.strftime('%d/%m/%Y')}")

            current_date += timedelta(days=1)
            time.sleep(1)

        total_sukses += sukses
        total_hari = (end_date - start_date).days + 1
        print(f"✅ SID {sid}: {sukses}/{total_hari} gambar berhasil")

        print("   → Jeda 3 detik sebelum SID berikutnya...")
        time.sleep(3)

    return total_sukses


# =====================================================================
# MODE GRAPH TITLE
# =====================================================================

def ambil_gambar_tanggal_graphtitle(driver, graph_title, tanggal):
    tgl_str = tanggal.strftime("%d/%m/%Y")
    waktu_awal = f"{tgl_str} 00:00"
    waktu_akhir = f"{tgl_str} 23:55"

    for percobaan in range(1, MAX_RETRIES + 1):
        try:
            driver.execute_script(f"document.getElementById('startdate').value = '{waktu_awal}';")
            driver.execute_script(f"document.getElementById('enddate').value = '{waktu_akhir}';")
            driver.execute_script("document.getElementById('startdate').dispatchEvent(new Event('change'));")
            driver.execute_script("document.getElementById('enddate').dispatchEvent(new Event('change'));")
            time.sleep(0.5)

            driver.execute_script("document.getElementById('graphfilter').click();")
            
            # Tambah waktu tunggu karena kadang web server lemot nge-generate grafik baru
            time.sleep(8)

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            gambar = None
            for _ in range(20):
                try:
                    elems = driver.find_elements(By.XPATH, "//img[contains(@src, 'graph.php')]")
                    if elems and elems[0].is_displayed():
                        gambar = elems[0]
                        break
                except:
                    pass
                time.sleep(0.5)

            if not gambar:
                raise Exception("Gambar tidak ditemukan")

            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", gambar)
            time.sleep(1)

            temp_file = f"temp_{tanggal.strftime('%Y%m%d')}.png"
            gambar.screenshot(temp_file)

            if is_graph_not_available(temp_file):
                os.remove(temp_file)
                raise Exception("Graph not available")

            return temp_file

        except Exception as e:
            print(f"     [Percobaan {percobaan}] Gagal: {str(e)[:100]}")
            if percobaan < MAX_RETRIES:
                print("     → Refresh halaman dan buka ulang modal...")
                driver.refresh()
                time.sleep(5)
                # Tunggu siap
                for _ in range(20):
                    try:
                        driver.find_element(By.NAME, "graphtitle")
                        break
                    except:
                        time.sleep(0.5)
                # Input ulang title dan buka modal
                try:
                    input_title = driver.find_element(By.NAME, "graphtitle")
                    input_title.clear()
                    input_title.send_keys(graph_title)
                    time.sleep(0.5)
                    input_title.send_keys(Keys.ENTER)
                    time.sleep(2)
                    tombol_grafik = driver.find_element(By.CSS_SELECTOR, "a.btn-graph")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tombol_grafik)
                    time.sleep(0.5)
                    tombol_grafik.click()
                    for _ in range(30):
                        try:
                            driver.find_element(By.ID, "graphfilter")
                            break
                        except:
                            time.sleep(0.5)
                    time.sleep(2)
                except Exception as ex:
                    print(f"     → Gagal reopen modal: {ex}")
            else:
                return None
    return None

def proses_graph_title(driver, graph_title, start_date, end_date, folder_output):
    try:
        input_title = driver.find_element(By.NAME, "graphtitle")
        input_title.clear()
        input_title.send_keys(graph_title)
        time.sleep(0.5)
        input_title.send_keys(Keys.ENTER)
        print(f"   → Tekan Enter untuk graph title: {graph_title}")
        time.sleep(2)

        tombol_grafik = driver.find_element(By.CSS_SELECTOR, "a.btn-graph")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tombol_grafik)
        time.sleep(0.5)
        tombol_grafik.click()
        print("   → Klik tombol grafik, menunggu modal...")

        for _ in range(30):
            try:
                driver.find_element(By.ID, "graphfilter")
                break
            except:
                time.sleep(0.5)
        print("   → Modal terbuka")

        sukses = 0
        current = start_date
        while current <= end_date:
            tgl_str = current.strftime("%Y%m%d")
            folder_tgl = os.path.join(folder_output, tgl_str)
            os.makedirs(folder_tgl, exist_ok=True)

            print(f"   → Mengambil gambar untuk {current.strftime('%d/%m/%Y')}")
            temp_file = ambil_gambar_tanggal_graphtitle(driver, graph_title, current)
            if temp_file and os.path.exists(temp_file):
                final_name = os.path.join(folder_tgl, f"MRTG_{graph_title}_{current.strftime('%Y%m%d')}.png")
                os.replace(temp_file, final_name)
                print(f"     ✅ Berhasil")
                sukses += 1
            else:
                print(f"     ❌ Gagal")

            current += timedelta(days=1)
            time.sleep(1)

        try:
            close_btn = driver.find_element(By.ID, "modalclose")
            close_btn.click()
            print("   → Modal ditutup")
        except:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(2)
        return sukses

    except Exception as e:
        print(f"   → ERROR: {e}")
        return 0

def run_mode_graphtitle(driver, titles, start_date, end_date, folder_output):
    total_sukses = 0
    total_hari = (end_date - start_date).days + 1

    for idx, title in enumerate(titles, 1):
        print(f"\n{'='*50}")
        print(f"📁 PROSES GRAPH TITLE {idx}/{len(titles)}: {title}")
        print(f"{'='*50}")

        sukses = proses_graph_title(driver, title, start_date, end_date, folder_output)
        total_sukses += sukses
        print(f"✅ Graph title {title}: {sukses}/{total_hari} gambar berhasil")

        if idx < len(titles):
            print("   → Refresh halaman untuk mempersiapkan title berikutnya...")
            driver.refresh()
            time.sleep(5)
            for _ in range(20):
                try:
                    driver.find_element(By.NAME, "graphtitle")
                    break
                except:
                    time.sleep(0.5)
            print("   → Halaman siap")

        time.sleep(2)

    return total_sukses


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 60)
    print("    AUTOMATED MRTG SCREENSHOT - TELKOMCARE")
    print("=" * 60)

    print("\nPilih mode pencarian:")
    print("  [1] SID         → Cari berdasarkan SID (file: SID-MRTG.txt)")
    print("  [2] Graph Title → Cari berdasarkan Graph Title (file: GRAPH-TITLE-MRTG.txt)")
    print()

    pilihan = input("Masukkan pilihan (1/2): ").strip()
    if pilihan == "1":
        mode = "sid"
    elif pilihan == "2":
        mode = "graphtitle"
    else:
        print("Pilihan tidak valid! Gunakan 1 atau 2.")
        return

    cfg = CONFIG[mode]
    print(f"\n→ Mode: {cfg['label']}")
    print(f"→ File: {cfg['file']}")

    # Baca item dari file
    if not os.path.exists(cfg["file"]):
        print(f"\n[ERROR] File '{cfg['file']}' tidak ditemukan!")
        return

    items = baca_item_dari_file(cfg["file"], cfg["prefix"])
    if not items:
        print(f"Tidak ada {cfg['label']} ditemukan di file {cfg['file']}")
        return
    print(f"→ Ditemukan {len(items)} {cfg['label']} unik")

    # Input rentang tanggal
    start_date, end_date = input_tanggal_range()
    if not start_date or not end_date:
        return

    # Setup browser
    driver = setup_browser()
    driver.get(cfg["url"])

    print("\n" + "=" * 60)
    print("⚠️  LOGIN MANUAL, ISI CAPTCHA, LALU ENTER")
    print("=" * 60)
    input("TEKAN ENTER SETELAH LOGIN...")

    os.makedirs(cfg["output"], exist_ok=True)

    # Jalankan sesuai mode
    if mode == "sid":
        total_sukses = run_mode_sid(driver, items, start_date, end_date, cfg["output"])
    else:
        total_sukses = run_mode_graphtitle(driver, items, start_date, end_date, cfg["output"])

    print("\n" + "=" * 60)
    print(f"🎉 SELESAI! Total gambar berhasil: {total_sukses}")
    print(f"📁 Folder output: {cfg['output']}")
    print("=" * 60)
    driver.quit()

if __name__ == "__main__":
    main()
