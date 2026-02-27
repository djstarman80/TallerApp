@echo off
set GH=C:\Program Files\GitHub CLI\gh.exe
set REPO=djstarman80/TallerApp
set VERSION=1.1

echo ======================================
echo Crear Release en GitHub
echo ======================================

echo Verificando autenticación...
%GH% auth status
if errorlevel 1 (
    echo Primero debés autenticarte con github_login.bat
    pause
    exit /b 1
)

echo.
echo Verificando si el repositorio existe...
%GH% repo view %REPO%
if errorlevel 1 (
    echo Error: No se pudo acceder al repositorio %REPO%
    echo Asegurate de que el repositorio exista y tengas acceso
    pause
    exit /b 1
)

echo.
echo Buscando archivo TallerApp.exe en dist/...
if not exist "dist\TallerApp.exe" (
    echo Error: No se encontró dist\TallerApp.exe
    echo Primero ejecutá crear_exe.bat para generar el exe
    pause
    exit /b 1
)

echo.
echo Creando release v%VERSION%...
%GH% release create v%VERSION% ^
    --title "Versión %VERSION%" ^
    --notes "Nueva versión del sistema de pedidos Taller" ^
    "dist\TallerApp.exe"

if errorlevel 1 (
    echo Error al crear el release
    pause
    exit /b 1
)

echo.
echo ======================================
echo Release creado exitosamente!
echo.
echo Recordá actualizar la versión en Google Sheets:
echo   - Hoja CONFIG, columna E (VERSION)
echo   - Cambiar el valor a: %VERSION%
echo ======================================
pause
