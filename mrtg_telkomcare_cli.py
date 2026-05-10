import time
import os
import sys
import shutil
import ctypes
import logging
import traceback
from datetime import datetime, timedelta

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
    StaleElementReferenceException,
    WebDriverException,
    NoSuchWindowException
)

from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tqdm import tqdm
from config import CONFIG, MAX_RETRIES, MAX_GRAPH_RETRIES, LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT, ANSI, WAIT_TIMEOUT, LONG_TIMEOUT, TEMP_FOLDER

# ========== KONFIGURASI UI & LOGGING ==========
console = Console()

ANSI_CYAN   = ANSI["CYAN"]
ANSI_GREEN  = ANSI["GREEN"]
ANSI_RED    = ANSI["RED"]
ANSI_YELLOW = ANSI["YELLOW"]
ANSI_DIM    = ANSI["DIM"]
ANSI_RESET  = ANSI["RESET"]

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8')],
)
logger = logging.getLogger(__name__)

def log_separator(title=""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        if not title: f.write("\n" + "="*80 + "\n\n")
        else:
            padding = (78 - len(title)) // 2
            f.write("\n" + "="*padding + f" {title} " + "="*padding + "\n")

def log_blank():
    with open(LOG_FILE, "a", encoding="utf-8") as f: f.write("\n")

# ========== HELPER UTILITY ==========
def baca_item_dari_file(filepath, prefix):
    items = []
    if not os.path.exists(filepath): return []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(prefix):
                item = line.replace(prefix, "").strip(); items.append(item)
    return list(dict.fromkeys(items))

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
    except:
        return False

# ========== MRTG BOT CLASS ==========
class MRTGBot:
    def __init__(self, mode):
        self.mode = mode
        self.cfg = CONFIG[mode]
        self.driver = None
        self.pbar = None
        self.total_sukses = 0
        self.total_gagal = 0

    def setup_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # ==============================================================================
    # 🔄 FUNGSI RECOVERY - REFRESH BROWSER + RE-INPUT
    # ==============================================================================
    def recover_graph_not_loaded(self, target, tanggal):
        """
        Kalau graph belum load, recovery dengan:
        Refresh -> Re-input SID -> Re-input tanggal -> Filter
        """
        tgl_str = tanggal.strftime("%d/%m/%Y")
        w_start, w_end = f"{tgl_str} 00:00", f"{tgl_str} 23:55"
        
        logger.info(f"   🔄 Melakukan recovery untuk {target} [{tgl_str}]...")
        
        try:
            self.driver.refresh()
            time.sleep(3)
            
            # Tunggu dan navigasi ulang ke menu filter jika perlu
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, "//a[@data-id='2']"))).click()
            time.sleep(1)
            nav = "//a[contains(@href, '/mrtgnetcare2/graph/monitoring')]" if self.mode == "sid" else "//a[@data-id='1' and contains(@href, '/mrtgnetcare2/graph')]"
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, nav))).click()
            time.sleep(2)

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
            logger.error(f"   ❌ Recovery gagal: {e}")
            return False

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
        except: pass

    def handle_alerts(self):
        try:
            alert = self.driver.switch_to.alert
            logger.warning(f"Alert terdeteksi & ditutup: {alert.text}")
            alert.accept()
            return True
        except NoAlertPresentException: return False

    def ensure_page_active(self):
        try:
            _ = self.driver.current_url; return True
        except UnexpectedAlertPresentException:
            self.handle_alerts(); return True
        except Exception as e:
            logger.warning(f"   ⚠️ Halaman tidak aktif, mencoba reload... ({str(e)[:50]})")
            try: 
                self.driver.get(self.cfg["url"])
                time.sleep(7)
                return True
            except: 
                logger.error("   ❌ Gagal me-reload halaman TelkomCare.")
                return False

    def wait_for_loading_and_kill_it(self):
        try:
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".blockUI, .loading, .spinner, .ajax-loader"))
            )
            js_kill = "document.querySelectorAll('.blockUI, .blockOverlay, .blockMsg, .loading').forEach(el => el.remove());"
            self.driver.execute_script(js_kill)
        except: pass

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
                target.style.setProperty('margin', '0', 'important');
                target.style.setProperty('padding', '0', 'important');
                target.style.setProperty('z-index', '99999999', 'important');
                window.scrollTo(0, 0);
            """
            self.driver.execute_script(js_isolate, img_el)
        except: pass

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
        except: pass

    def ganti_target_with_retry(self, target_value):
        input_name = self.cfg["input_name"]
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if not self.ensure_page_active(): continue
                input_elem = WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.NAME, input_name)))
                input_elem.clear(); input_elem.send_keys(target_value); time.sleep(0.5); input_elem.send_keys(Keys.ENTER); time.sleep(2)
                btn = WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn-graph")))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(1); self.driver.execute_script("arguments[0].click();", btn)
                return True
            except (UnexpectedAlertPresentException, StaleElementReferenceException, Exception) as e:
                self.handle_alerts()
                err_msg = str(e).split('\n')[0]
                logger.error(f"FAIL pada {target_value} (Attempt {attempt}): {err_msg}")
                if attempt < MAX_RETRIES:
                    logger.info(f"RETRY {attempt}/{MAX_RETRIES} untuk {target_value}...")
                    self.pbar.write(f"  {ANSI_YELLOW}⚠️  Retry {attempt}/{MAX_RETRIES} untuk {target_value}...{ANSI_RESET}")
                    # REVISI: Refresh dan tunggu sebentar agar DOM stabil
                    try: 
                        self.driver.refresh()
                        time.sleep(10) # Kasih waktu ekstra setelah error JSON/Server
                    except: pass
        
        logger.error(f"   ❌ Gagal memproses {target_value} setelah {MAX_RETRIES} kali percobaan.")
        return False

    def ambil_gambar_logic(self, target, tanggal):
        tgl_str = tanggal.strftime("%d/%m/%Y")
        w_start, w_end = f"{tgl_str} 00:00", f"{tgl_str} 23:55"
        
        # Simpan di folder temp khusus
        os.makedirs(TEMP_FOLDER, exist_ok=True)
        temp_file = os.path.join(TEMP_FOLDER, f"temp_{target}_{tanggal.strftime('%Y%m%d')}.png")

        try:
            logger.info(f"Mulai ambil gambar: {target} [{tgl_str}]")
            
            # --- INPUT TANGGAL (Hanya dilakukan di awal, recovery punya input sendiri) ---
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
            logger.error(f"ERROR pada {target} [{tgl_str}]: {str(e).split('\\n')[0]}")
            self.handle_alerts()
            if 'temp_file' in locals() and os.path.exists(temp_file):
                try: os.remove(temp_file)
                except: pass
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
                logger.warning(f"   ⚠️ Grafik tidak muncul. Mencoba RECOVERY {graph_attempt}/{MAX_GRAPH_RETRIES}...")
                self.recover_graph_not_loaded(target, tanggal)
                continue # Coba capture lagi setelah recovery
            
            self.isolate_image_for_capture(img_el)
            time.sleep(3) # Tunggu render matang
            img_el.screenshot(temp_file)
            self.restore_ui_after_capture(img_el)

            # --- CEK APAKAH PLACEHOLDER? ---
            if is_graph_placeholder(temp_file):
                logger.warning(f"   ⚠️ Graph terdeteksi ZONK (placeholder), recovery {graph_attempt}/{MAX_GRAPH_RETRIES}...")
                if os.path.exists(temp_file): os.remove(temp_file)
                self.recover_graph_not_loaded(target, tanggal)
                continue # Coba capture lagi setelah recovery
            
            # --- CEK KUALITAS NORMAL ---
            if check_image_quality(temp_file):
                logger.info(f"BERHASIL: {target} [{tgl_str}]")
                return temp_file
            else:
                logger.warning(f"   ⚠️ Kualitas rendah tapi bukan placeholder. Simpan untuk audit.")
                return None
        
        return None

    def run(self, items, start_date, end_date):
        log_separator(f"START {self.cfg['label']} SESSION")
        total_hari = (end_date - start_date).days + 1
        self.pbar = tqdm(total=len(items)*total_hari, bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}]")

        try:
            for idx, item in enumerate(items, start=1):
                log_blank()
                logger.info(f"=== PROSES ITEM {idx}/{len(items)}: {item} ===")
                if not self.ganti_target_with_retry(item):
                    self.total_gagal += total_hari; self.pbar.update(total_hari); continue
                
                current = start_date
                consecutive_fails = 0
                while current <= end_date:
                    tgl_fmt = current.strftime('%d/%m/%Y')
                    
                    # Ambil gambar (Logic internal sudah handle retry/recovery)
                    temp_file = self.ambil_gambar_logic(item, current)
                    
                    if temp_file:
                        consecutive_fails = 0 # Reset counter
                        folder_tgl = os.path.join(self.cfg["output"], current.strftime("%Y%m%d"))
                        os.makedirs(folder_tgl, exist_ok=True)
                        fname = f"MRTG_{item}.png" if self.mode == "sid" else f"MRTG_{item}_{current.strftime('%Y%m%d')}.png"
                        os.replace(temp_file, os.path.join(folder_tgl, fname))
                        self.total_sukses += 1
                        self.pbar.write(f"  {ANSI_GREEN}✅{ANSI_RESET} {item} [{tgl_fmt}]")
                    else:
                        self.total_gagal += 1
                        consecutive_fails += 1
                        self.pbar.write(f"  {ANSI_RED}❌{ANSI_RESET} {item} [{tgl_fmt}]")
                        
                        # SKIP LOGIC: Jika gagal 3x berturut-turut untuk SID ini
                        if consecutive_fails >= 3:
                            sisa_hari = (end_date - current).days
                            if sisa_hari > 0:
                                logger.warning(f"SKIP SID {item}: Gagal 3x berturut-turut. Melewati sisa {sisa_hari} hari.")
                                self.pbar.write(f"  {ANSI_YELLOW}⏭️  Skip sisanya ({sisa_hari} hari) karena gagal 3x...{ANSI_RESET}")
                                self.total_gagal += sisa_hari
                                self.pbar.update(sisa_hari)
                                break # Keluar dari loop 'while current'
                    
                    self.pbar.set_description(f"Progres: {ANSI_GREEN}✅ {self.total_sukses}{ANSI_RESET} | {ANSI_RED}❌ {self.total_gagal}{ANSI_RESET}")
                    self.pbar.update(1)
                    current += timedelta(days=1)
                
                try: self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE); time.sleep(1)
                except: pass
        except KeyboardInterrupt:
            self._handle_interrupt()
        finally:
            self.pbar.close(); log_separator("END SESSION")

    def _handle_interrupt(self):
        log_blank(); logger.warning("!!! USER INTERRUPT (CTRL+C) !!!")
        self.pbar.write(f"\n{ANSI_YELLOW}⚠️  PROSES DIHENTIKAN PAKSA (Ctrl+C).{ANSI_RESET}")

    def display_summary(self):
        total_total = self.total_sukses + self.total_gagal
        if total_total == 0: return
        success_rate = (self.total_sukses / total_total * 100)
        summary_table = Table(title="📊 RINGKASAN PROSES", border_style="cyan")
        summary_table.add_column("Keterangan", style="bold white")
        summary_table.add_column("Jumlah", justify="right")
        summary_table.add_row("Total Gambar Diproses", str(total_total))
        summary_table.add_row("Total [green]SUKSES[/green]", f"[bold green]{self.total_sukses}[/bold green]")
        summary_table.add_row("Total [red]GAGAL[/red]", f"[bold red]{self.total_gagal}[/bold red]")
        summary_table.add_row("Success Rate", f"{success_rate:.1f}%")
        console.print("\n"); console.print(summary_table)

def main():
    bot = None
    try:
        # Pastikan folder temp bersih di awal
        if os.path.exists(TEMP_FOLDER): shutil.rmtree(TEMP_FOLDER, ignore_errors=True)
        os.makedirs(TEMP_FOLDER, exist_ok=True)
        
        console.print(Panel.fit("[bold cyan]AUTOMATED MRTG SCREENSHOT - TELKOMCARE[/bold cyan]", border_style="cyan"))
        table = Table(show_header=False, box=None)
        table.add_row("[1]", "SID Mode"); table.add_row("[2]", "Graph Title Mode")
        console.print(table)
        pilihan = console.input("\n>> Pilihan (1/2): ").strip()
        mode = "sid" if pilihan == "1" else "graphtitle" if pilihan == "2" else None
        if not mode: return
        
        bot = MRTGBot(mode)
        items = baca_item_dari_file(bot.cfg["file"], bot.cfg["prefix"])
        start_date, end_date = input_tanggal_range()
        if not start_date: return
        
        bot.setup_browser()
        bot.driver.get(bot.cfg["url"])
        console.print(Panel.fit("[bold yellow]LOGIN MANUAL LALU ENTER DI SINI...[/bold yellow]", border_style="yellow"))
        input()
        
        WebDriverWait(bot.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, "//a[@data-id='2']"))).click()
        time.sleep(1)
        target = "//a[contains(@href, '/mrtgnetcare2/graph/monitoring')]" if mode == "sid" else "//a[@data-id='1' and contains(@href, '/mrtgnetcare2/graph')]"
        WebDriverWait(bot.driver, WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, target))).click()
        time.sleep(2)
        
        bot.hide_browser_gaib()
        bot.run(items, start_date, end_date)
        bot.display_summary()
        
    except KeyboardInterrupt:
        if bot: bot._handle_interrupt()
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]"); logger.error(traceback.format_exc())
    finally:
        if bot and bot.driver:
            try: bot.driver.quit()
            except: pass

def input_tanggal_range():
    console.print("\n📅 Format: DD MM YYYY")
    try:
        t_start = console.input("Mulai: ").strip().split()
        t_end = console.input("Akhir: ").strip().split()
        return datetime(int(t_start[2]), int(t_start[1]), int(t_start[0])), datetime(int(t_end[2]), int(t_end[1]), int(t_end[0]))
    except: return None, None

if __name__ == "__main__":
    main()
