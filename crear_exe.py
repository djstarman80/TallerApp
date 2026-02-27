# Script para crear .exe con PyInstaller

# Instalación de dependencias
# pip install pyinstaller

# Comando para crear el ejecutable
# pyinstaller --onefile --noconsole --name "TallerApp" main.py

# Opciones adicionales:
# --onefile: Crea un solo archivo .exe
# --noconsole: No muestra la consola al ejecutar
# --name: Nombre del ejecutable
# --icon: Icono personalizado (ej: --icon=icono.ico)
# --add-data: Archivos adicionales (ej: --add-data="client_secret.json;.")


# Ejemplo completo con icono:
# pyinstaller --onefile --noconsole --name "TallerApp" --icon=icono.ico --add-data="client_secret.json;." main.py


# ============================================
# SCRIPT AUTOMÁTICO
# ============================================

import subprocess
import sys
import os

def install_pyinstaller():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_exe():
    # Crear spec file personalizado
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('client_secret.json', '.')],
    hiddenimports=['PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TallerApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('build.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    # Ejecutar PyInstaller
    subprocess.check_call(['pyinstaller', 'build.spec', '--clean'])
    
    print("\n=== Ejecutable creado en carpeta 'dist' ===")

if __name__ == '__main__':
    try:
        import pyinstaller
    except ImportError:
        print("Instalando PyInstaller...")
        install_pyinstaller()
    
    print("Creando ejecutable...")
    build_exe()
    print("\nListo! Ejecutable: dist/TallerApp.exe")
