@echo off
echo ========================================================
echo   MRTG TELKOMCARE - EXE BUILDER (PYINSTALLER)
echo ========================================================
echo.
echo 1. Installing dependencies...
pip install -r requirements.txt

echo.
echo 2. Building EXE...
echo [INFO] Creating standalone executable for GUI version...
pyinstaller --noconfirm --onefile --windowed ^
 --name "MRTG_TelkomCare_Bot" ^
 --clean ^
 "mrtg_telkomcare_gui.py"

echo.
echo ========================================================
echo   BUILD SELESAI! 
echo   Cek folder "dist" untuk mengambil file .exe Anda.
echo ========================================================
pause
