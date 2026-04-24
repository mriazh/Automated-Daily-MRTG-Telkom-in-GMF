import time
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pytesseract
from PIL import Image

# ========== KONFIGURASI ==========
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
FOLDER_OUTPUT = "output_mrtg_graphtitle"
MAX_RETRIES = 2
GRAPH_TITLE_FILE = "GRAPH-TITLE-MRTG.txt"

def baca_graph_title(filepath):
    titles = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("Graph-title : "):
                title = line.replace("Graph-title : ", "").strip()
                if title:
                    titles.append(title)
    return list(dict.fromkeys(titles))

def input_tanggal_range():
    print("\nMasukkan rentang tanggal (DD MM YYYY):")
    tgl_mulai = input("Tanggal mulai: ").strip().split()
    tgl_akhir = input("Tanggal akhir: ").strip().split()
    if len(tgl_mulai) != 3 or len(tgl_akhir) != 3:
        print("Format salah! Gunakan: DD MM YYYY (pisah spasi)")
        return None, None
    try:
        start = datetime(int(tgl_mulai[2]), int(tgl_mulai[1]), int(tgl_mulai[0]))
        end = datetime(int(tgl_akhir[2]), int(tgl_akhir[1]), int(tgl_akhir[0]))
        if start > end:
            print("Tanggal mulai harus lebih awal")
            return None, None
        return start, end
    except ValueError:
        print("Tanggal tidak valid")
        return None, None

def is_graph_not_available(image_path):
    try:
        img = Image.open(image_path)
        img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
        text = pytesseract.image_to_string(img)
        return "Graph not available" in text or "not available" in text.lower()
    except:
        return False

def ambil_gambar_tanggal(driver, tanggal):
    tgl_str = tanggal.strftime("%d/%m/%Y")
    waktu_awal = f"{tgl_str} 00:00"
    waktu_akhir = f"{tgl_str} 23:55"
    
    for percobaan in range(1, MAX_RETRIES + 1):
        try:
            # Set nilai startdate dan enddate via JavaScript
            driver.execute_script(f"document.getElementById('startdate').value = '{waktu_awal}';")
            driver.execute_script(f"document.getElementById('enddate').value = '{waktu_akhir}';")
            driver.execute_script("document.getElementById('startdate').dispatchEvent(new Event('change'));")
            driver.execute_script("document.getElementById('enddate').dispatchEvent(new Event('change'));")
            time.sleep(0.5)
            
            # Klik filter
            driver.execute_script("document.getElementById('graphfilter').click();")
            
            # Tunggu gambar termuat
            time.sleep(5)
            
            # Scroll ke bawah
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Cari elemen gambar
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
            
            # Scroll ke gambar
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", gambar)
            time.sleep(1)
            
            # Screenshot
            temp_file = f"temp_{tanggal.strftime('%Y%m%d')}.png"
            gambar.screenshot(temp_file)
            
            # Validasi OCR
            if is_graph_not_available(temp_file):
                os.remove(temp_file)
                raise Exception("Graph not available")
            
            return temp_file
            
        except Exception as e:
            print(f"     [Percobaan {percobaan}] Gagal: {str(e)[:100]}")
            if percobaan == MAX_RETRIES:
                return None
            time.sleep(2)
    return None

def proses_graph_title(driver, graph_title, start_date, end_date):
    try:
        # Input graph title
        input_title = driver.find_element(By.NAME, "graphtitle")
        input_title.clear()
        input_title.send_keys(graph_title)
        time.sleep(0.5)
        input_title.send_keys(Keys.ENTER)
        print(f"   → Tekan Enter untuk graph title: {graph_title}")
        time.sleep(2)
        
        # Klik tombol grafik (buka modal)
        tombol_grafik = driver.find_element(By.CSS_SELECTOR, "a.btn-graph")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tombol_grafik)
        time.sleep(0.5)
        tombol_grafik.click()
        print("   → Klik tombol grafik, menunggu modal...")
        
        # Tunggu modal terbuka
        for _ in range(30):
            try:
                driver.find_element(By.ID, "graphfilter")
                break
            except:
                time.sleep(0.5)
        print("   → Modal terbuka")
        
        # Loop tanggal
        sukses = 0
        current = start_date
        while current <= end_date:
            tgl_str = current.strftime("%Y%m%d")
            folder_tgl = os.path.join(FOLDER_OUTPUT, tgl_str)
            os.makedirs(folder_tgl, exist_ok=True)
            
            print(f"   → Mengambil gambar untuk {current.strftime('%d/%m/%Y')}")
            temp_file = ambil_gambar_tanggal(driver, current)
            if temp_file:
                final_name = os.path.join(folder_tgl, f"MRTG_{graph_title}_{current.strftime('%Y%m%d')}.png")
                os.rename(temp_file, final_name)
                print(f"     ✅ Berhasil")
                sukses += 1
            else:
                print(f"     ❌ Gagal")
            
            current += timedelta(days=1)
            time.sleep(1)
        
        # Tutup modal
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

def main():
    print("=" * 60)
    print("MRTG GRAPH TITLE - DENGAN REFRESH ANTAR TITLE")
    print("=" * 60)
    
    titles = baca_graph_title(GRAPH_TITLE_FILE)
    if not titles:
        print(f"Tidak ada graph title ditemukan di {GRAPH_TITLE_FILE}")
        return
    print(f"\nDitemukan {len(titles)} graph title: {titles}")
    
    start_date, end_date = input_tanggal_range()
    if not start_date or not end_date:
        return
    
    print("\nMembuka browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception as e:
        print(f"\n[WARNING] Download ChromeDriver otomatis diblokir jaringan. Mencoba fallback...")
        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e2:
            print("\n[ERROR FATAL] Gagal membuka Chrome. Silakan letakkan file 'chromedriver.exe' secara manual di folder ini.")
            import sys; sys.exit(1)
            
    driver.get("https://telkomcare.telkom.co.id/mrtgnetcare2/graph")
    
    print("\n" + "=" * 60)
    print("⚠️ LOGIN MANUAL, ISI CAPTCHA, LALU ENTER")
    print("=" * 60)
    input("TEKAN ENTER SETELAH LOGIN...")
    
    os.makedirs(FOLDER_OUTPUT, exist_ok=True)
    total_sukses = 0
    total_hari = (end_date - start_date).days + 1
    
    for idx, title in enumerate(titles, 1):
        print(f"\n{'='*50}")
        print(f"📁 PROSES GRAPH TITLE {idx}/{len(titles)}: {title}")
        print(f"{'='*50}")
        
        sukses = proses_graph_title(driver, title, start_date, end_date)
        total_sukses += sukses
        print(f"✅ Graph title {title}: {sukses}/{total_hari} gambar berhasil")
        
        # === PERBAIKAN: REFRESH HALAMAN SETELAH SETIAP TITLE ===
        if idx < len(titles):  # Jangan refresh setelah title terakhir
            print("   → Refresh halaman untuk mempersiapkan title berikutnya...")
            driver.refresh()
            time.sleep(5)
            # Tunggu hingga halaman siap (input graphtitle muncul)
            for _ in range(20):
                try:
                    driver.find_element(By.NAME, "graphtitle")
                    break
                except:
                    time.sleep(0.5)
            print("   → Halaman siap")
        
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print(f"🎉 SELESAI! Total gambar berhasil: {total_sukses}")
    print(f"📁 Folder output: {FOLDER_OUTPUT}")
    print("=" * 60)
    driver.quit()

if __name__ == "__main__":
    main()