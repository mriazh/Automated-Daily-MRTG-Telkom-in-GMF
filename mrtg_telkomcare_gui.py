import sys
import os
import time
import threading
import ctypes
import logging
import traceback
from datetime import datetime, timedelta
from PIL import Image

# FIX for PyInstaller --windowed mode deadlocks
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QRadioButton, QButtonGroup, QLabel, QDateEdit,
    QTextEdit, QGroupBox, QMessageBox, QStyle
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QDate
from PySide6.QtGui import QFont, QTextCursor, QIcon, QPalette, QColor

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    UnexpectedAlertPresentException, 
    NoAlertPresentException,
    TimeoutException,
    StaleElementReferenceException
)

from config import CONFIG, MAX_RETRIES, MAX_GRAPH_RETRIES, LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT, WAIT_TIMEOUT, LONG_TIMEOUT, TEMP_FOLDER

# ========== KONFIGURASI LOGGING (SAMA DENGAN CLI) ==========
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8')],
)
logger = logging.getLogger(__name__)

# ========== UTILITY: IMAGE QUALITY CHECK ==========
def check_image_quality(image_path):
    try:
        img = Image.open(image_path)
        # Cek Resolusi (Gambar error biasanya sangat kecil)
        if img.height < 100 or img.width < 100:
            logger.warning(f"   ⚠️  Kualitas Rendah: Resolusi terlalu kecil ({img.width}x{img.height})")
            return False
            
        if img.mode != 'RGB': img = img.convert('RGB')
        ycbcr = img.convert("YCbCr")
        extrema = ycbcr.getextrema()
        
        # Cek kontras (Gambar kosong/blank biasanya punya range warna sangat sempit)
        if (extrema[1][1] - extrema[1][0]) < 15 and (extrema[2][1] - extrema[2][0]) < 15:
            logger.warning(f"   ⚠️  Kualitas Rendah: Gambar terdeteksi kosong/blank (low contrast)")
            return False
            
        return True
    except Exception as e:
        logger.error(f"   ❌ Gagal memvalidasi gambar: {e}")
        return False

# ==============================================================================
# 🔍 FUNGSI DETEKSI GRAPH NOT AVAILABLE (PLACEHOLDER)
# ==============================================================================
def is_graph_placeholder(image_path):
    """
    Cek apakah gambar adalah 'graph not available' (belum load).
    Graph yang belum load biasanya berupa gambar solid dengan 1-2 warna saja.
    """
    try:
        img = Image.open(image_path)
        if img.height < 100 or img.width < 100:
            return True # Resolusi terlalu kecil = placeholder
        
        if img.mode != 'RGB': img = img.convert('RGB')
        ycbcr = img.convert("YCbCr")
        extrema = ycbcr.getextrema()
        
        # Kalau rentang warna sangat sempit (< 10), berarti placeholder image
        if (extrema[1][1] - extrema[1][0]) < 10 and (extrema[2][1] - extrema[2][0]) < 10:
            return True
            
        return False
    except Exception as e:
        logger.debug(f"is_graph_placeholder error: {e}")
        return False

class WorkerSignals(QObject):
    log_msg = Signal(str)
    login_ready = Signal()
    finished = Signal()

class ScraperWorker(QThread):
    def __init__(self, mode, start_date, end_date):
        super().__init__()
        self.mode = mode
        self.cfg = CONFIG[mode]
        self.start_date = start_date
        self.end_date = end_date
        self.signals = WorkerSignals()
        self.login_event = threading.Event()
        self.is_running = True
        self.driver = None
        self.total_sukses = 0
        self.total_gagal = 0
        self.total_retry = 0

    def log(self, text, level="info"):
        clean_text = text.strip()
        if clean_text:
            self.signals.log_msg.emit(text)
            if level == "info": logger.info(clean_text)
            elif level == "error": logger.error(clean_text)
            elif level == "warning": logger.warning(clean_text)

    def stop(self):
        self.is_running = False
        self.login_event.set()

    def hide_browser_gaib(self):
        try:
            self.driver.execute_script("document.title = 'BOT_MRTG_TELKOMCARE';")
            time.sleep(2)
            user32 = ctypes.windll.user32
            target_title = "BOT_MRTG_TELKOMCARE"
            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            def enum_cb(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        if target_title in buf.value:
                            user32.ShowWindow(hwnd, 0)
                return True
            user32.EnumWindows(enum_cb, 0)
        except Exception as e:
            logger.debug(f"hide_browser_gaib error: {e}")

    def handle_alerts(self):
        try:
            alert = self.driver.switch_to.alert
            self.log(f"⚠️  Alert terdeteksi: {alert.text[:50]}...", "warning")
            alert.accept()
            return True
        except NoAlertPresentException: return False
    
    def ensure_page_active(self):
        try:
            _ = self.driver.current_url; return True
        except UnexpectedAlertPresentException:
            self.handle_alerts(); return True
        except Exception as e:
            self.log(f"   ⚠️ Halaman tidak aktif, reload... ({str(e)[:50]})", "warning")
            self.total_retry += 1
            try: 
                self.driver.get(self.cfg["url"])
                time.sleep(7)
                self.hide_browser_gaib() # Sembunyiin lagi
                return True
            except Exception as e2: 
                self.log(f"   ❌ Gagal me-reload halaman: {e2}", "error")
                return False

    def wait_for_loading_and_kill_it(self):
        try:
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".blockUI, .loading, .spinner, .ajax-loader"))
            )
            self.driver.execute_script("document.querySelectorAll('.blockUI, .blockOverlay, .blockMsg, .loading').forEach(el => el.remove());")
        except Exception as e:
            logger.debug(f"wait_for_loading_and_kill_it: {e}")

    def isolate_image_for_capture(self, img_el):
        try:
            js_isolate = """
                var target = arguments[0];
                window._hidden_elements = [];
                var ancestors = [];
                var curr = target;
                while (curr) { ancestors.push(curr); curr = curr.parentNode; }
                document.body.querySelectorAll('*').forEach(el => {
                    if (el.style.display !== 'none' && !ancestors.includes(el)) {
                        window._hidden_elements.push({el: el, display: el.style.display});
                        el.style.setProperty('display', 'none', 'important');
                    }
                });
                document.documentElement.style.setProperty('overflow', 'hidden', 'important');
                document.body.style.setProperty('overflow', 'hidden', 'important');
                document.body.style.setProperty('margin', '0', 'important');
                document.body.style.setProperty('padding', '0', 'important');
                document.body.style.setProperty('background', 'white', 'important');
                target.style.setProperty('display', 'block', 'important');
                target.style.setProperty('visibility', 'visible', 'important');
                target.style.setProperty('position', 'fixed', 'important');
                target.style.setProperty('top', '0', 'important');
                target.style.setProperty('left', '0', 'important');
                target.style.setProperty('width', target.naturalWidth + 'px', 'important');
                target.style.setProperty('height', target.naturalHeight + 'px', 'important');
                target.style.setProperty('z-index', '99999999', 'important');
                window.scrollTo(0, 0);
            """
            self.driver.execute_script(js_isolate, img_el)
        except Exception as e:
            logger.debug(f"isolate_image_for_capture error: {e}")

    def restore_ui_after_capture(self, img_el):
        try:
            js_restore = """
                var target = arguments[0];
                if (window._hidden_elements) {
                    window._hidden_elements.forEach(item => {
                        item.el.style.display = item.display;
                    });
                }
                document.documentElement.style.removeProperty('overflow');
                document.body.style.removeProperty('overflow');
                document.body.style.removeProperty('margin');
                document.body.style.removeProperty('padding');
                document.body.style.removeProperty('background');
                target.style.removeProperty('position');
                target.style.removeProperty('top');
                target.style.removeProperty('left');
                target.style.removeProperty('width');
                target.style.removeProperty('height');
                target.style.removeProperty('z-index');
            """
            self.driver.execute_script(js_restore, img_el)
        except Exception as e:
            logger.debug(f"restore_ui_after_capture error: {e}")

    def ganti_target_with_retry(self, target_value):
        input_name = self.cfg["input_name"]
        for attempt in range(1, MAX_RETRIES + 1):
            if not self.is_running: return False
            try:
                if not self.ensure_page_active(): continue
                input_elem = WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.NAME, input_name)))
                input_elem.clear()
                input_elem.send_keys(target_value)
                time.sleep(0.5); input_elem.send_keys(Keys.ENTER); time.sleep(2)
                btn = WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-graph")))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(1); self.driver.execute_script("arguments[0].click();", btn)
                return True
            except (UnexpectedAlertPresentException, StaleElementReferenceException, Exception) as e:
                self.handle_alerts()
                if attempt < MAX_RETRIES:
                    self.total_retry += 1
                    self.log(f"   ⚠️  Retry {attempt}/{MAX_RETRIES} untuk {target_value}...", "warning")
                    try: 
                        self.driver.refresh()
                        time.sleep(10)
                        self.hide_browser_gaib() # Sembunyiin lagi
                    except Exception as e:
                        logger.debug(f"Refresh during retry failed: {e}")
        self.log(f"   ❌ Gagal memproses {target_value} ({MAX_RETRIES}x retry).", "error")
        return False

    def ambil_gambar_logic(self, target, tanggal):
        tgl_str = tanggal.strftime("%d/%m/%Y")
        w_start, w_end = f"{tgl_str} 00:00", f"{tgl_str} 23:55"
        
        # Simpan di folder temp khusus
        os.makedirs(TEMP_FOLDER, exist_ok=True)
        temp_file = os.path.join(TEMP_FOLDER, f"temp_{target}_{tanggal.strftime('%Y%m%d')}.png")
        try:
            self.log(f"   Mulai ambil gambar: {target} [{tgl_str}]")
            
            # --- INPUT TANGGAL ---
            f_sel = By.CSS_SELECTOR if self.mode == "graphtitle" else By.XPATH
            f_val = "button#graphfilter" if self.mode == "graphtitle" else "//button[contains(normalize-space(), 'Filter')]"
            WebDriverWait(self.driver, LONG_TIMEOUT).until(EC.presence_of_element_located((f_sel, f_val)))
            
            if self.mode == "sid":
                inputs = self.driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Filter')]/preceding::input[not(@type='hidden')]")
                self.driver.execute_script("arguments[0].value = arguments[1];", inputs[-2], w_start)
                self.driver.execute_script("arguments[0].value = arguments[1];", inputs[-1], w_end)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", inputs[-2])
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", inputs[-1])
                btn_f = self.driver.find_element(By.XPATH, f_val)
                self.driver.execute_script("arguments[0].click();", btn_f)
            else:
                self.driver.execute_script(f"document.getElementById('startdate').value = '{w_start}';")
                self.driver.execute_script(f"document.getElementById('enddate').value = '{w_end}';")
                self.driver.execute_script("document.getElementById('startdate').dispatchEvent(new Event('change'));")
                self.driver.execute_script("document.getElementById('enddate').dispatchEvent(new Event('change'));")
                self.driver.execute_script("document.getElementById('graphfilter').click();")

            time.sleep(3); self.wait_for_loading_and_kill_it(); time.sleep(2)
            
            return self._internal_capture_logic(target, tanggal, tgl_str, temp_file)
        except Exception as e:
            self.log(f"   ❌ Error Ambil Gambar: {str(e)[:80]}", "error")
            self.handle_alerts()
            return None

    def _internal_capture_logic(self, target, tanggal, tgl_str, temp_file):
        """Internal loop untuk handle 'graph not available' dengan recovery"""
        for graph_attempt in range(1, MAX_GRAPH_RETRIES + 1):
            img_el = None
            for _ in range(15):
                imgs = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'graph.php')]")
                for img in imgs:
                    if int(img.get_attribute("naturalWidth") or 0) > 400:
                        img_el = img; break
                if img_el: break
                time.sleep(1)
            
            if not img_el:
                self.log(f"   ⚠️ Grafik tidak muncul. Mencoba RECOVERY {graph_attempt}/{MAX_GRAPH_RETRIES}...", "warning")
                self.recover_graph_not_loaded(target, tanggal)
                continue # Coba capture lagi

            self.isolate_image_for_capture(img_el)
            time.sleep(3) # Tunggu render matang
            img_el.screenshot(temp_file); self.restore_ui_after_capture(img_el)
            
            # --- CEK APAKAH PLACEHOLDER? ---
            if is_graph_placeholder(temp_file):
                self.log(f"   ⚠️ Graph ZONK (placeholder), recovery {graph_attempt}/{MAX_GRAPH_RETRIES}...", "warning")
                if os.path.exists(temp_file): os.remove(temp_file)
                self.recover_graph_not_loaded(target, tanggal)
                continue # Coba capture lagi
            
            # --- CEK KUALITAS NORMAL ---
            if check_image_quality(temp_file):
                return temp_file
            else:
                self.log(f"   ⚠️ Kualitas rendah tapi bukan placeholder. Simpan audit.", "warning")
                return None
        return None

    def recover_graph_not_loaded(self, target, tanggal):
        """Recovery: Refresh -> Re-input SID -> Re-input Tanggal"""
        tgl_str = tanggal.strftime("%d/%m/%Y")
        w_start, w_end = f"{tgl_str} 00:00", f"{tgl_str} 23:55"
        self.log(f"   🔄 Melakukan recovery untuk {target} [{tgl_str}]...")
        try:
            self.driver.refresh(); time.sleep(3)
            self.hide_browser_gaib() # Sembunyiin lagi
            # Re-input SID/Title
            input_name = self.cfg["input_name"]
            input_elem = WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.NAME, input_name)))
            input_elem.clear(); input_elem.send_keys(target); input_elem.send_keys(Keys.ENTER); time.sleep(2)
            btn = WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-graph")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(1); self.driver.execute_script("arguments[0].click();", btn)
            # Re-input Tanggal
            if self.mode == "sid":
                inputs = self.driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Filter')]/preceding::input[not(@type='hidden')]")
                self.driver.execute_script("arguments[0].value = arguments[1];", inputs[-2], w_start)
                self.driver.execute_script("arguments[0].value = arguments[1];", inputs[-1], w_end)
                btn_f = self.driver.find_element(By.XPATH, "//button[contains(normalize-space(), 'Filter')]")
                self.driver.execute_script("arguments[0].click();", btn_f)
            else:
                self.driver.execute_script(f"document.getElementById('startdate').value = '{w_start}';")
                self.driver.execute_script(f"document.getElementById('enddate').value = '{w_end}';")
                self.driver.execute_script("document.getElementById('graphfilter').click();")
            time.sleep(3); self.wait_for_loading_and_kill_it(); time.sleep(2)
            return True
        except Exception as e:
            self.log(f"   ❌ Recovery gagal: {e}", "error")
            self.total_retry += 1
            return False

    def run(self):
        try:
            # Pastikan folder temp bersih di awal
            if os.path.exists(TEMP_FOLDER):
                import shutil
                shutil.rmtree(TEMP_FOLDER, ignore_errors=True)
            os.makedirs(TEMP_FOLDER, exist_ok=True)

            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=webdriver.ChromeOptions())
            self.driver.get(self.cfg["url"])
            self.log("\n" + "="*50); self.log("⚠️  SILAKAN LOGIN MANUAL DI BROWSER..."); 
            self.log("✅ Klik tombol 'Lanjutkan' jika sudah login!"); self.log("="*50)
            self.signals.login_ready.emit()
            self.login_event.wait()
            if not self.is_running:
                if self.driver: self.driver.quit()
                self.signals.finished.emit(); return
            self.hide_browser_gaib()
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, "//a[@data-id='2']"))).click()
            time.sleep(1.5)
            target_nav = "//a[contains(@href, '/mrtgnetcare2/graph/monitoring')]" if self.mode == "sid" else "//a[@data-id='1' and contains(@href, '/mrtgnetcare2/graph')]"
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, target_nav))).click()
            time.sleep(2)
            items = []
            if os.path.exists(self.cfg["file"]):
                with open(self.cfg["file"], "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith(self.cfg["prefix"]):
                            items.append(line.replace(self.cfg["prefix"], "").strip())
            items = list(dict.fromkeys(items))
            total_sukses = 0
            for idx, item in enumerate(items, 1):
                if not self.is_running: break
                label = self.cfg["label"]
                self.log(f"\n=== PROSES {label} {idx}/{len(items)}: {item} ===")
                if not self.ganti_target_with_retry(item):
                    self.log(f"   ❌ Gagal memproses {item}", "error")
                    continue
                current = self.start_date
                while current <= self.end_date:
                    if not self.is_running: break
                    tgl_fmt = current.strftime('%d/%m/%Y')
                    
                    # Ambil gambar (Logic internal sudah handle retry/recovery)
                    temp = self.ambil_gambar_logic(item, current)
                    
                    if temp:
                        folder = os.path.join(self.cfg["output"], current.strftime("%Y%m%d"))
                        os.makedirs(folder, exist_ok=True)
                        fname = f"MRTG_{item}.png" if self.mode == "sid" else f"MRTG_{item}_{current.strftime('%Y%m%d')}.png"
                        os.replace(temp, os.path.join(folder, fname))
                        self.log(f"   ✅ Berhasil [{tgl_fmt}]")
                        self.total_sukses += 1
                    else:
                        self.log(f"   ❌ Gagal [{tgl_fmt}]", "error")
                        self.total_gagal += 1
                    current += timedelta(days=1)
            
            # Final Summary Table for GUI Log
            total_total = self.total_sukses + self.total_gagal
            success_rate = (self.total_sukses / total_total * 100) if total_total > 0 else 0
            self.log("\n" + "═"*50)
            self.log(f"📊  RINGKASAN PROSES AKHIR")
            self.log(f"   Total Diproses : {total_total}")
            self.log(f"   Total Berhasil : {self.total_sukses}")
            self.log(f"   Total Retry    : {self.total_retry}")
            self.log(f"   Total Gagal    : {self.total_gagal}")
            self.log(f"   Success Rate   : {success_rate:.1f}%")
            self.log("═"*50 + "\n")
        except Exception as e:
            self.log(f"\n[CRITICAL ERROR] {e}", "error")
        finally:
            if self.driver: self.driver.quit()
            self.signals.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MRTG TelkomCare Scraper - Pro Version")
        self.resize(750, 600)
        self.is_dark_mode = True
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        mode_group = QGroupBox("Mode Pencarian")
        mode_layout = QHBoxLayout(); self.radio_sid = QRadioButton("SID Mode"); self.radio_graph = QRadioButton("Graph Title Mode")
        self.radio_sid.setChecked(True); mode_layout.addWidget(self.radio_sid); mode_layout.addWidget(self.radio_graph)
        mode_group.setLayout(mode_layout); main_layout.addWidget(mode_group)
        date_group = QGroupBox("Rentang Tanggal")
        date_layout = QHBoxLayout(); self.date_start = QDateEdit(QDate.currentDate()); self.date_start.setCalendarPopup(True)
        self.date_end = QDateEdit(QDate.currentDate()); self.date_end.setCalendarPopup(True)
        date_layout.addWidget(QLabel("Mulai:")); date_layout.addWidget(self.date_start); date_layout.addWidget(QLabel("Akhir:")); date_layout.addWidget(self.date_end)
        date_group.setLayout(date_layout); main_layout.addWidget(date_group)
        self.log_viewer = QTextEdit(); self.log_viewer.setReadOnly(True); self.log_viewer.setFont(QFont("Consolas", 10))
        main_layout.addWidget(QLabel("Proses Log:")); main_layout.addWidget(self.log_viewer)
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Mulai Scraping"); self.btn_start.setMinimumHeight(45); self.btn_start.clicked.connect(self.start_scraping)
        self.btn_continue = QPushButton("✅ Lanjutkan"); self.btn_continue.setMinimumHeight(45); self.btn_continue.setEnabled(False); self.btn_continue.clicked.connect(self.continue_scraping)
        self.btn_stop = QPushButton("🛑 STOP"); self.btn_stop.setMinimumHeight(45); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_scraping)
        btn_layout.addWidget(self.btn_start); btn_layout.addWidget(self.btn_continue); btn_layout.addWidget(self.btn_stop); main_layout.addLayout(btn_layout)
        self.apply_theme(); self.update_button_styles(); self.worker = None

    def apply_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 46)); palette.setColor(QPalette.WindowText, QColor(205, 214, 244))
        palette.setColor(QPalette.Base, QColor(17, 17, 27)); palette.setColor(QPalette.Text, QColor(166, 227, 161))
        palette.setColor(QPalette.Button, QColor(49, 50, 68)); palette.setColor(QPalette.ButtonText, QColor(205, 214, 244))
        QApplication.instance().setPalette(palette)
        self.log_viewer.setStyleSheet("background-color: #11111b; color: #a6e22e; border: 1px solid #313244;")

    def update_button_styles(self):
        def get_style(color_hex, enabled):
            if not enabled: return "background-color: #45475a; color: #9399b2; border-radius: 5px; font-weight: bold;"
            return f"background-color: {color_hex}; color: white; border-radius: 5px; font-weight: bold;"
        
        self.btn_start.setStyleSheet(get_style("#2ecc71", self.btn_start.isEnabled()))
        self.btn_continue.setStyleSheet(get_style("#2ecc71", self.btn_continue.isEnabled()))
        self.btn_stop.setStyleSheet(get_style("#e74c3c", self.btn_stop.isEnabled()))

    def append_log(self, text):
        self.log_viewer.append(text); self.log_viewer.moveCursor(QTextCursor.End)

    def enable_continue(self):
        self.btn_continue.setEnabled(True); self.update_button_styles()

    def start_scraping(self):
        self.log_viewer.clear(); self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True); self.update_button_styles()
        self.worker = ScraperWorker("sid" if self.radio_sid.isChecked() else "graphtitle", self.date_start.date().toPython(), self.date_end.date().toPython())
        self.worker.signals.log_msg.connect(self.append_log); self.worker.signals.login_ready.connect(self.enable_continue)
        self.worker.signals.finished.connect(self.on_finished); self.worker.start()

    def continue_scraping(self):
        self.btn_continue.setEnabled(False); self.update_button_styles()
        if self.worker: self.worker.login_event.set()

    def stop_scraping(self):
        if self.worker: self.worker.stop(); self.append_log("\n⚠️  MENGHENTIKAN PROSES..."); self.btn_stop.setEnabled(False); self.update_button_styles()

    def on_finished(self):
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False); self.btn_continue.setEnabled(False); self.update_button_styles()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion"); window = MainWindow(); window.show(); sys.exit(app.exec())
