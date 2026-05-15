import os
import sys
from dotenv import load_dotenv

# ==============================================================================
# ⚙️ PUSAT KOMANDO (CENTRAL CONFIG)
# ==============================================================================

# --- Resolusi Path (Supaya jalan di Script maupun .EXE) ---
if getattr(sys, 'frozen', False):
    # Jika dijalankan sebagai .EXE (PyInstaller)
    BASE_PATH = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Jika dijalankan sebagai Script (.py)
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BASE_PATH

# Muat file .env dari dalam paket EXE atau folder source code
env_path = os.path.join(BASE_PATH, '.env')
load_dotenv(dotenv_path=env_path)

# --- Folder & File ---
TEMP_FOLDER = os.path.join(APP_DIR, "temp_screenshots")
LOG_FILE    = "mrtg_process.log"

# --- Parameter Operasional ---
MAX_RETRIES  = 5
MAX_GRAPH_RETRIES = 5 # Retry khusus jika dapet gambar placeholder (Graph Not Available)
WAIT_TIMEOUT = 10    # Timeout standar buat WebDriverWait
LONG_TIMEOUT = 15    # Timeout buat proses yang agak lama (Filter/Loading)
LOGIN_WAIT   = 15    # Waktu tunggu buat elemen login muncul

# --- Konfigurasi Target TelkomCare ---
CONFIG = {
    "sid": {
        "file": os.path.join(APP_DIR, "SID-MRTG.txt"),
        "output": os.path.join(APP_DIR, "output_mrtg_sid"),
        "url": os.getenv("BASE_URL_SID", ""),
        "input_name": "sid",
        "prefix": "SID : ",
        "label": "SID",
    },
    "graphtitle": {
        "file": os.path.join(APP_DIR, "GRAPH-TITLE-MRTG.txt"),
        "output": os.path.join(APP_DIR, "output_mrtg_graphtitle"),
        "url": os.getenv("BASE_URL_GRAPH", ""),
        "input_name": "graphtitle",
        "prefix": "Graph-title : ",
        "label": "Graph Title",
    },
}

# --- Konfigurasi Logging ---
LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Warna Terminal (ANSI) ---
ANSI = {
    "CYAN": "\033[1;36m",
    "GREEN": "\033[1;32m",
    "RED": "\033[1;31m",
    "YELLOW": "\033[1;33m",
    "DIM": "\033[2m",
    "RESET": "\033[0m"
}
