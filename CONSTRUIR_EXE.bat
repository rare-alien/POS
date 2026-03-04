@echo off
title Construccion del Ejecutable - Punto de Venta

echo.
echo ================================================
echo   CONSTRUCCION DEL EJECUTABLE .EXE
echo   Punto de Venta
echo ================================================
echo.

REM -- Verificar Python --
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo.
    echo Solucion:
    echo   1. Descarga Python desde https://python.org
    echo   2. Durante la instalacion marca "Add Python to PATH"
    echo   3. Reinicia esta ventana y vuelve a ejecutar
    echo.
    pause
    exit /b 1
)

echo [OK] Python encontrado:
python --version
echo.

REM -- Verificar que existe el archivo .py --
if not exist "punto_de_venta.py" (
    echo [ERROR] No se encontro "punto_de_venta.py" en esta carpeta.
    echo.
    echo Asegurate de que este .bat y el .py esten en la misma carpeta.
    echo.
    pause
    exit /b 1
)

echo [OK] Archivo punto_de_venta.py encontrado.
echo.

REM -- Instalar PyInstaller --
echo [1/3] Instalando PyInstaller...
pip install --upgrade pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de PyInstaller.
    echo Intenta ejecutar este archivo como Administrador.
    pause
    exit /b 1
)
echo [OK] PyInstaller listo.
echo.

REM -- Construir el ejecutable --
echo [2/3] Construyendo el ejecutable...
echo        Este paso puede tardar entre 1 y 3 minutos.
echo.

pyinstaller --onefile --windowed --name "PuntoDeVenta" punto_de_venta.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller encontro un problema al construir.
    echo Revisa los mensajes de arriba para identificar la causa.
    pause
    exit /b 1
)

REM -- Limpiar archivos temporales --
echo.
echo [3/3] Limpiando archivos temporales...
if exist "build" rmdir /s /q "build"
if exist "PuntoDeVenta.spec" del /q "PuntoDeVenta.spec"
echo [OK] Listo.

echo.
echo ================================================
echo   EJECUTABLE CREADO CORRECTAMENTE
echo.
echo   Archivo: dist\PuntoDeVenta.exe
echo.
echo   Lee las INSTRUCCIONES para mover el .exe
echo   y la ventas.db a la carpeta de produccion.
echo ================================================
echo.
echo Presiona cualquier tecla para abrir la carpeta dist...
pause >nul
explorer dist
