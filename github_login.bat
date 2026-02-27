@echo off
set GH="C:\Program Files\GitHub CLI\gh.exe"

echo ======================================
echo Configuración de GitHub CLI
echo ======================================

echo.
echo Iniciando sesión en GitHub...
echo Seleccioná las opciones:
echo   - GitHub.com
echo   - HTTPS  
echo   - Y (yes) para authenticate with web browser
echo.
echo Presiona una tecla para continuar...
pause >nul

%GH% auth login --web

echo.
echo Verificando...
%GH% auth status

echo.
echo Listo! Ahora podés crear releases.
pause
