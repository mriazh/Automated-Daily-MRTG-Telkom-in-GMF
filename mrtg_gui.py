import sys
import os
import time
import threading
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QRadioButton, QButtonGroup, QLabel, QDateEdit,
    QTextEdit, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QDate
from PySide6.QtGui import QFont, QTextCursor, QIcon

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

# ========== KONFIGURASI ==========
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
MAX_RETRIES = 3

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


class WorkerSignals(QObject):
    log_msg = Signal(str)
    login_ready = Signal()
    finished = Signal()


class ScraperWorker(QThread):
    def __init__(self, mode, start_date, end_date):
        super().__init__()
        self.mode = mode
        self.start_date = start_date
        self.end_date = end_date
        self.signals = WorkerSignals()
        self.login_event = threading.Event()
        self.is_running = True

    def log(self, text):
        self.signals.log_msg.emit(text)

    def baca_item_dari_file(self, filepath, prefix):
        items = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(prefix):
                        item = line.replace(prefix, "").strip()
                        if item:
                            items.append(item)
        except Exception as e:
            self.log(f"[ERROR] Gagal membaca file {filepath}: {e}")
        return list(dict.fromkeys(items))

    def setup_browser(self):
        self.log("\nMembuka browser Chrome...")
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception:
            self.log("\n[WARNING] Download ChromeDriver otomatis diblokir jaringan. Mencoba fallback...")
            try:
                driver = webdriver.Chrome(options=options)
            except Exception:
                self.log("\n[ERROR FATAL] Gagal membuka Chrome. Silakan letakkan file 'chromedriver.exe' secara manual.")
                return None
        return driver

    def tutup_alert_jika_ada(self, driver):
        try:
            alert = driver.switch_to.alert
            self.log(f"     → Alert: {alert.text[:50]}")
            alert.accept()
            time.sleep(1)
            return True
        except NoAlertPresentException:
            return False

    def is_graph_not_available(self, image_path):
        try:
            img = Image.open(image_path)
            if img.width < 50 or img.height < 50:
                return True

            ycbcr = img.convert("YCbCr")
            extrema = ycbcr.getextrema()
            cb_diff = extrema[1][1] - extrema[1][0]
            cr_diff = extrema[2][1] - extrema[2][0]

            if cb_diff < 15 and cr_diff < 15:
                self.log(f"     → Terdeteksi blank/error (gambar tidak berwarna: cb_diff={cb_diff}, cr_diff={cr_diff})")
                return True

            try:
                img_resized = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
                text = pytesseract.image_to_string(img_resized).lower()
                error_keywords = ["no graph", "graph not available", "not available", "no data"]
                for keyword in error_keywords:
                    if keyword in text:
                        return True
            except Exception:
                pass 

            return False
        except Exception as e:
            self.log(f"     → Validasi error: {e}")
            return False

    # ========== SID MODE FUNCTIONS ==========
    def ganti_sid(self, driver, sid):
        try:
            input_sid = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "sid")))
            input_sid.clear()
            input_sid.send_keys(sid)
            time.sleep(0.5)
            input_sid.send_keys(Keys.ENTER)
            self.log(f"   → Tekan Enter untuk SID {sid}")

            time.sleep(5)
            if self.tutup_alert_jika_ada(driver):
                self.log(f"   → Alert muncul, SID {sid} tidak valid")
                return False

            tombol_grafik = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-graph")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tombol_grafik)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", tombol_grafik)
            self.log(f"   → Klik tombol grafik untuk SID {sid}")
            time.sleep(3)
            return True
        except UnexpectedAlertPresentException:
            self.tutup_alert_jika_ada(driver)
            return False
        except Exception as e:
            self.log(f"   → ERROR ganti SID: {str(e)[:80]}")
            return False

    def reset_halaman_sid(self, driver):
        self.log("     → Refresh halaman...")
        driver.refresh()
        time.sleep(5)
        self.tutup_alert_jika_ada(driver)
        try:
            for _ in range(20):
                try:
                    driver.find_element(By.NAME, "sid")
                    return True
                except:
                    time.sleep(0.5)
            return False
        except:
            return False

    def ambil_gambar_tanggal_sid(self, driver, sid, tanggal):
        tgl_str = tanggal.strftime("%d/%m/%Y")
        tahun = tanggal.strftime("%Y")
        bulan = tanggal.strftime("%m")
        hari = tanggal.strftime("%d")
        waktu_awal = f"{tgl_str} 00:00"
        waktu_akhir = f"{tgl_str} 23:55"
        temp_file = f"temp_{sid}_{tahun}{bulan}{hari}.png"

        for percobaan in range(1, MAX_RETRIES + 1):
            if not self.is_running: break
            try:
                inputs_tanggal = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Filter')]/preceding::input[not(@type='hidden')]")
                if len(inputs_tanggal) >= 2:
                    input_start = inputs_tanggal[-2]
                    input_end = inputs_tanggal[-1]
                    driver.execute_script("arguments[0].value = arguments[1];", input_start, waktu_awal)
                    driver.execute_script("arguments[0].value = arguments[1];", input_end, waktu_akhir)
                else:
                    self.log(f"     [SKIP] Kolom tanggal tidak ditemukan")
                    return None

                tombol_filter = driver.find_element(By.XPATH, "//button[contains(normalize-space(), 'Filter')]")
                driver.execute_script("arguments[0].click();", tombol_filter)

                grafik_img = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'graph.php')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", grafik_img)
                time.sleep(2)

                grafik_img.screenshot(temp_file)

                if self.is_graph_not_available(temp_file):
                    self.log(f"     [GAGAL] {tgl_str} - Graph not available")
                    os.remove(temp_file)
                    raise Exception("Graph not available")

                self.log(f"     [OK] {tgl_str}")
                return temp_file

            except Exception as e:
                self.log(f"     [PERCOBAAN {percobaan}] {sid} - {tgl_str} gagal: {str(e)[:60]}")
                if percobaan < MAX_RETRIES:
                    self.reset_halaman_sid(driver)
                    if not self.ganti_sid(driver, sid):
                        return None
                    time.sleep(2)
                else:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return None
        return None

    def run_mode_sid(self, driver, items, cfg):
        total_sukses = 0
        total_hari = (self.end_date - self.start_date).days + 1
        for idx, sid in enumerate(items, start=1):
            if not self.is_running: break
            self.log(f"\n{'='*50}")
            self.log(f"📁 PROSES SID {idx}/{len(items)}: {sid}")
            self.log(f"{'='*50}")

            if not self.ganti_sid(driver, sid):
                self.log(f"❌ Skip SID {sid} (gagal ganti SID)")
                self.reset_halaman_sid(driver)
                continue

            sukses = 0
            current_date = self.start_date
            while current_date <= self.end_date:
                if not self.is_running: break
                tgl_str = current_date.strftime("%Y%m%d")
                folder_tanggal = os.path.join(cfg["output"], tgl_str)
                os.makedirs(folder_tanggal, exist_ok=True)

                self.log(f"   → Mengambil gambar untuk {current_date.strftime('%d/%m/%Y')}")
                temp_file = self.ambil_gambar_tanggal_sid(driver, sid, current_date)
                if temp_file and os.path.exists(temp_file):
                    final_name = os.path.join(folder_tanggal, f"MRTG_{sid}.png")
                    os.replace(temp_file, final_name)
                    self.log(f"     ✅ Tersimpan: {final_name}")
                    sukses += 1
                else:
                    self.log(f"     ❌ Gagal untuk tanggal {current_date.strftime('%d/%m/%Y')}")

                current_date += timedelta(days=1)
                time.sleep(1)

            total_sukses += sukses
            self.log(f"✅ SID {sid}: {sukses}/{total_hari} gambar berhasil")
            self.log("   → Jeda 3 detik sebelum SID berikutnya...")
            time.sleep(3)
        return total_sukses

    # ========== GRAPH TITLE MODE FUNCTIONS ==========
    def ambil_gambar_tanggal_graphtitle(self, driver, graph_title, tanggal):
        tgl_str = tanggal.strftime("%d/%m/%Y")
        waktu_awal = f"{tgl_str} 00:00"
        waktu_akhir = f"{tgl_str} 23:55"

        for percobaan in range(1, MAX_RETRIES + 1):
            if not self.is_running: break
            try:
                driver.execute_script(f"document.getElementById('startdate').value = '{waktu_awal}';")
                driver.execute_script(f"document.getElementById('enddate').value = '{waktu_akhir}';")
                driver.execute_script("document.getElementById('startdate').dispatchEvent(new Event('change'));")
                driver.execute_script("document.getElementById('enddate').dispatchEvent(new Event('change'));")
                time.sleep(0.5)

                driver.execute_script("document.getElementById('graphfilter').click();")
                time.sleep(5)

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

                if self.is_graph_not_available(temp_file):
                    os.remove(temp_file)
                    raise Exception("Graph not available")

                return temp_file

            except Exception as e:
                self.log(f"     [Percobaan {percobaan}] Gagal: {str(e)[:100]}")
                if percobaan < MAX_RETRIES:
                    self.log("     → Refresh halaman dan buka ulang modal...")
                    driver.refresh()
                    time.sleep(5)
                    for _ in range(20):
                        try:
                            driver.find_element(By.NAME, "graphtitle")
                            break
                        except:
                            time.sleep(0.5)
                    try:
                        input_title = driver.find_element(By.NAME, "graphtitle")
                        input_title.clear()
                        input_title.send_keys(graph_title)
                        time.sleep(0.5)
                        input_title.send_keys(Keys.ENTER)
                        time.sleep(5)
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
                        self.log(f"     → Gagal reopen modal: {ex}")
                else:
                    return None
        return None

    def proses_graph_title(self, driver, graph_title, folder_output):
        try:
            input_title = driver.find_element(By.NAME, "graphtitle")
            input_title.clear()
            input_title.send_keys(graph_title)
            time.sleep(0.5)
            input_title.send_keys(Keys.ENTER)
            self.log(f"   → Tekan Enter untuk graph title: {graph_title}")
            time.sleep(5)

            tombol_grafik = driver.find_element(By.CSS_SELECTOR, "a.btn-graph")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tombol_grafik)
            time.sleep(0.5)
            tombol_grafik.click()
            self.log("   → Klik tombol grafik, menunggu modal...")

            for _ in range(30):
                try:
                    driver.find_element(By.ID, "graphfilter")
                    break
                except:
                    time.sleep(0.5)
            self.log("   → Modal terbuka")

            sukses = 0
            current = self.start_date
            while current <= self.end_date:
                if not self.is_running: break
                tgl_str = current.strftime("%Y%m%d")
                folder_tgl = os.path.join(folder_output, tgl_str)
                os.makedirs(folder_tgl, exist_ok=True)

                self.log(f"   → Mengambil gambar untuk {current.strftime('%d/%m/%Y')}")
                temp_file = self.ambil_gambar_tanggal_graphtitle(driver, graph_title, current)
                if temp_file and os.path.exists(temp_file):
                    final_name = os.path.join(folder_tgl, f"MRTG_{graph_title}_{current.strftime('%Y%m%d')}.png")
                    os.replace(temp_file, final_name)
                    self.log(f"     ✅ Berhasil")
                    sukses += 1
                else:
                    self.log(f"     ❌ Gagal")

                current += timedelta(days=1)
                time.sleep(1)

            try:
                close_btn = driver.find_element(By.ID, "modalclose")
                close_btn.click()
                self.log("   → Modal ditutup")
            except:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(2)
            return sukses

        except Exception as e:
            self.log(f"   → ERROR: {e}")
            return 0

    def run_mode_graphtitle(self, driver, items, cfg):
        total_sukses = 0
        total_hari = (self.end_date - self.start_date).days + 1

        for idx, title in enumerate(items, 1):
            if not self.is_running: break
            self.log(f"\n{'='*50}")
            self.log(f"📁 PROSES GRAPH TITLE {idx}/{len(items)}: {title}")
            self.log(f"{'='*50}")

            sukses = self.proses_graph_title(driver, title, cfg["output"])
            total_sukses += sukses
            self.log(f"✅ Graph title {title}: {sukses}/{total_hari} gambar berhasil")

            if idx < len(items) and self.is_running:
                self.log("   → Refresh halaman untuk mempersiapkan title berikutnya...")
                driver.refresh()
                time.sleep(5)
                for _ in range(20):
                    try:
                        driver.find_element(By.NAME, "graphtitle")
                        break
                    except:
                        time.sleep(0.5)
                self.log("   → Halaman siap")

            time.sleep(2)

        return total_sukses

    def run(self):
        self.log("=" * 60)
        self.log("    AUTOMATED MRTG SCREENSHOT - TELKOMCARE")
        self.log("=" * 60)

        cfg = CONFIG[self.mode]
        self.log(f"\n→ Mode: {cfg['label']}")
        self.log(f"→ File: {cfg['file']}")

        if not os.path.exists(cfg["file"]):
            self.log(f"\n[ERROR] File '{cfg['file']}' tidak ditemukan!")
            self.signals.finished.emit()
            return

        items = self.baca_item_dari_file(cfg["file"], cfg["prefix"])
        if not items:
            self.log(f"Tidak ada {cfg['label']} ditemukan di file {cfg['file']}")
            self.signals.finished.emit()
            return
        self.log(f"→ Ditemukan {len(items)} {cfg['label']} unik")

        driver = self.setup_browser()
        if not driver:
            self.signals.finished.emit()
            return

        driver.get("http://telkomcare.telkom.co.id/mrtgnetcare2/")

        self.log("\n" + "=" * 60)
        self.log("⚠️  SILAKAN LOGIN MANUAL DI BROWSER YANG TERBUKA")
        self.log("⚠️  SETELAH BERHASIL LOGIN, KLIK TOMBOL 'Lanjutkan Scraping'")
        self.log("=" * 60)
        
        self.signals.login_ready.emit()
        
        # Pause thread sampai event diset (via GUI button)
        self.login_event.wait()
        
        if not self.is_running:
            driver.quit()
            return

        self.log("\n   → Melakukan navigasi otomatis ke halaman grafik...")
        try:
            menu_graph = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@data-id='2']"))
            )
            menu_graph.click()
            time.sleep(1.5)

            if self.mode == "sid":
                submenu = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/mrtgnetcare2/graph/monitoring')]"))
                )
                submenu.click()
            else:
                submenu = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@data-id='1' and contains(@href, '/mrtgnetcare2/graph')]"))
                )
                submenu.click()
            
            self.log("   ✅ Navigasi berhasil")
            time.sleep(3)
        except Exception as e:
            self.log(f"   ❌ Gagal navigasi otomatis (lanjut memproses): {str(e)[:80]}")

        os.makedirs(cfg["output"], exist_ok=True)

        if self.mode == "sid":
            total_sukses = self.run_mode_sid(driver, items, cfg)
        else:
            total_sukses = self.run_mode_graphtitle(driver, items, cfg)

        self.log("\n" + "=" * 60)
        self.log(f"🎉 SELESAI! Total gambar berhasil: {total_sukses}")
        self.log(f"📁 Folder output: {cfg['output']}")
        self.log("=" * 60)
        
        driver.quit()
        self.signals.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MRTG TelkomCare Scraper")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "app_icon.png")))
        self.resize(750, 600)
        self.theme_state = 0 # 0: System, 1: Dark, 2: Light
        
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header Theme Toggle
        theme_layout = QHBoxLayout()
        theme_layout.addStretch()
        self.btn_theme = QPushButton("🖥️ Theme: System")
        self.btn_theme.setFixedWidth(140)
        self.btn_theme.clicked.connect(self.toggle_theme)
        theme_layout.addWidget(self.btn_theme)
        main_layout.addLayout(theme_layout)

        # Mode Selection
        mode_group = QGroupBox("Mode Pencarian")
        mode_layout = QHBoxLayout()
        self.radio_sid = QRadioButton("SID (SID-MRTG.txt)")
        self.radio_graph = QRadioButton("Graph Title (GRAPH-TITLE-MRTG.txt)")
        self.radio_sid.setChecked(True)
        mode_layout.addWidget(self.radio_sid)
        mode_layout.addWidget(self.radio_graph)
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        # Date Pickers
        date_group = QGroupBox("Rentang Tanggal")
        date_layout = QHBoxLayout()
        
        self.date_start = QDateEdit()
        self.date_start.setDisplayFormat("dd/MM/yyyy")
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate())
        
        self.date_end = QDateEdit()
        self.date_end.setDisplayFormat("dd/MM/yyyy")
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())

        date_layout.addWidget(QLabel("Mulai:"))
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("Akhir:"))
        date_layout.addWidget(self.date_end)
        date_group.setLayout(date_layout)
        main_layout.addWidget(date_group)

        # Log Window
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Consolas", 10))
        main_layout.addWidget(QLabel("Proses Log:"))
        main_layout.addWidget(self.log_viewer)

        # Control Buttons
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Mulai Scraping")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet("font-weight: bold;")
        self.btn_start.clicked.connect(self.start_scraping)
        
        self.btn_continue = QPushButton("✅ Lanjutkan (Sudah Login)")
        self.btn_continue.setMinimumHeight(40)
        self.btn_continue.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white;")
        self.btn_continue.setEnabled(False)
        self.btn_continue.clicked.connect(self.continue_scraping)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_continue)
        main_layout.addLayout(btn_layout)

        self.apply_theme()
        self.worker = None

    def apply_theme(self):
        if self.theme_state == 1: # Dark
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; }
                QGroupBox { border: 1px solid #45475a; margin-top: 10px; padding-top: 10px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #b4befe; }
                QTextEdit { background-color: #11111b; color: #a6e3a1; border: 1px solid #45475a; }
                QPushButton { background-color: #313244; border: 1px solid #45475a; padding: 5px; border-radius: 4px; }
                QPushButton:hover { background-color: #45475a; }
                QDateEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; padding: 3px; }
            """)
            self.btn_theme.setText("🌙 Theme: Dark")
        elif self.theme_state == 2: # Light
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f8f9fa; color: #212529; }
                QGroupBox { border: 1px solid #dee2e6; margin-top: 10px; padding-top: 10px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #0d6efd; }
                QTextEdit { background-color: #ffffff; color: #198754; border: 1px solid #dee2e6; }
                QPushButton { background-color: #e9ecef; border: 1px solid #ced4da; padding: 5px; border-radius: 4px; }
                QPushButton:hover { background-color: #dee2e6; }
                QDateEdit { background-color: #ffffff; color: #212529; border: 1px solid #ced4da; padding: 3px; }
            """)
            self.btn_theme.setText("☀️ Theme: Light")
        else: # System
            self.setStyleSheet("") # Hapus custom style untuk menggunakan tema bawaan OS
            self.btn_theme.setText("🖥️ Theme: System")
        
        # Override btn_continue specifically
        if not self.btn_continue.isEnabled():
            self.btn_continue.setStyleSheet("font-weight: bold; background-color: #6c757d; color: white;")
        else:
            self.btn_continue.setStyleSheet("font-weight: bold; background-color: #198754; color: white;")

    def toggle_theme(self):
        self.theme_state = (self.theme_state + 1) % 3
        self.apply_theme()

    def append_log(self, text):
        self.log_viewer.append(text)
        self.log_viewer.moveCursor(QTextCursor.End)

    def enable_continue_button(self):
        self.btn_continue.setEnabled(True)
        self.btn_continue.setStyleSheet("font-weight: bold; background-color: #198754; color: white;")
        self.btn_start.setEnabled(False)

    def start_scraping(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Warning", "Proses sedang berjalan!")
            return

        self.log_viewer.clear()
        
        mode = "sid" if self.radio_sid.isChecked() else "graphtitle"
        start_date = self.date_start.date().toPython()
        end_date = self.date_end.date().toPython()

        if start_date > end_date:
            QMessageBox.critical(self, "Error", "Tanggal mulai tidak boleh lebih besar dari tanggal akhir!")
            return

        self.btn_start.setEnabled(False)
        
        self.worker = ScraperWorker(mode, start_date, end_date)
        self.worker.signals.log_msg.connect(self.append_log)
        self.worker.signals.login_ready.connect(self.enable_continue_button)
        self.worker.signals.finished.connect(self.on_scraping_finished)
        self.worker.start()

    def continue_scraping(self):
        if self.worker:
            self.btn_continue.setEnabled(False)
            self.btn_continue.setStyleSheet("font-weight: bold; background-color: #6c757d; color: white;")
            self.append_log("\n[INFO] Melanjutkan proses scraping...")
            self.worker.login_event.set()

    def on_scraping_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_continue.setEnabled(False)
        self.btn_continue.setStyleSheet("font-weight: bold; background-color: #6c757d; color: white;")
        if self.worker:
            self.worker.is_running = False

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.is_running = False
            self.worker.login_event.set() # Release wait if paused
            self.worker.quit()
            self.worker.wait(1000)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
