@echo off
cd /d "%~dp0"
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "VideoToGif" --collect-all customtkinter --add-data "bin;bin" app.py
echo.
echo Готово! Исполняемый файл: dist\VideoToGif.exe
pause