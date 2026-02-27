@echo off
REM Script para crear .exe de TallerApp

echo Instalando PyInstaller...
pip install pyinstaller

echo.
echo Creando ejecutable...
pyinstaller --onefile --noconsole --name "TallerApp"  main.py

echo.
echo ========================================
echo Listo! Ejecutable creado en carpeta dist
echo ========================================
pause
