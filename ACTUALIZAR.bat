@echo off
chcp 65001 >nul
title Actualizacion del Punto de Venta (conserva la base de datos)

REM ============================================================
REM  ACTUALIZADOR DEL PUNTO DE VENTA  (Windows 10)
REM
REM  Reconstruye el .exe con los ultimos cambios del codigo
REM  y lo instala en la carpeta de produccion SIN tocar ventas.db.
REM
REM  IMPORTANTE: coloca este .bat junto a:
REM    - punto_de_venta.py
REM    - repositorio_pos.py
REM ============================================================

echo.
echo ================================================
echo   ACTUALIZACION DEL PUNTO DE VENTA
echo   (la base de datos ventas.db NO se modifica)
echo ================================================
echo.

REM ------------------------------------------------------------
REM  CONFIGURACION: carpeta donde vive el programa en produccion
REM  Cambia esta ruta si tu carpeta de produccion es distinta.
REM ------------------------------------------------------------
set "CARPETA_PROD=C:\PuntoDeVenta"

REM ------------------------------------------------------------
REM  1. Verificar Python
REM ------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo         Instala Python desde https://python.org marcando
    echo         "Add Python to PATH" y vuelve a ejecutar.
    echo.
    pause
    exit /b 1
)
echo [OK] Python encontrado: 
python --version
echo.

REM ------------------------------------------------------------
REM  2. Verificar archivos necesarios
REM ------------------------------------------------------------
if not exist "punto_de_venta.py" (
    echo [ERROR] No se encontro "punto_de_venta.py" en esta carpeta.
    pause
    exit /b 1
)
if not exist "repositorio_pos.py" (
    echo [ERROR] No se encontro "repositorio_pos.py" en esta carpeta.
    echo         Copia tambien este archivo antes de actualizar.
    pause
    exit /b 1
)
echo [OK] Archivos del codigo fuente encontrados.
echo.

REM ------------------------------------------------------------
REM  3. Instalar PyInstaller
REM ------------------------------------------------------------
echo [1/4] Preparando PyInstaller...
pip install --upgrade pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de PyInstaller.
    echo         Intenta ejecutar como Administrador.
    pause
    exit /b 1
)
echo [OK] PyInstaller listo.
echo.

REM ------------------------------------------------------------
REM  4. Construir el nuevo ejecutable
REM ------------------------------------------------------------
echo [2/4] Construyendo el ejecutable (1 a 3 minutos)...
pyinstaller --onefile --windowed --name "PuntoDeVenta" punto_de_venta.py
if errorlevel 1 (
    echo [ERROR] PyInstaller encontro un problema al construir.
    echo         Revisa los mensajes de arriba.
    pause
    exit /b 1
)
echo [OK] Ejecutable creado en dist\PuntoDeVenta.exe
echo.

REM ------------------------------------------------------------
REM  5. Respaldo de seguridad de la base de datos actual
REM ------------------------------------------------------------
echo [3/4] Respaldo de seguridad de la base de datos...

set "FECHA=%date:~-4%%date:~3,2%%date:~0,2%"
set "HORA=%time:~0,2%%time:~3,2%%time:~6,2%"
set "HORA=%HORA: =0%"
set "RESPALDO=ventas_backup_%FECHA%_%HORA%.db"

if exist "%CARPETA_PROD%\ventas.db" (
    copy /Y "%CARPETA_PROD%\ventas.db" "%CARPETA_PROD%\%RESPALDO%" >nul
    echo [OK] Respaldo creado: %CARPETA_PROD%\%RESPALDO%
) else (
    if exist "ventas.db" (
        copy /Y "ventas.db" "%CARPETA_PROD%\%RESPALDO%" >nul
        echo [AVISO] No se encontro ventas.db en %CARPETA_PROD%.
        echo         Se respaldo la base local: %RESPALDO%
    ) else (
        echo [AVISO] No se encontro ventas.db. Se creara una nueva al iniciar.
    )
)
echo.

REM ------------------------------------------------------------
REM  6. Instalar el ejecutable en produccion (SIN tocar ventas.db)
REM ------------------------------------------------------------
echo [4/4] Instalando en la carpeta de produccion...

if not exist "%CARPETA_PROD%" (
    echo [AVISO] La carpeta "%CARPETA_PROD%" no existe. Creandola...
    mkdir "%CARPETA_PROD%" >nul 2>&1
)

copy /Y "dist\PuntoDeVenta.exe" "%CARPETA_PROD%\PuntoDeVenta.exe" >nul
if errorlevel 1 (
    echo [ERROR] No se pudo copiar el ejecutable a "%CARPETA_PROD%".
    echo         Verifica que la carpeta no este protegida o en uso.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   ACTUALIZACION COMPLETADA
echo.
echo   Programa:  %CARPETA_PROD%\PuntoDeVenta.exe
echo   Base de datos: %CARPETA_PROD%\ventas.db  (INTACTA)
echo   Respaldo:  %CARPETA_PROD%\%RESPALDO%
echo ================================================
echo.
echo Presiona cualquier tecla para abrir la carpeta de produccion...
pause >nul
explorer "%CARPETA_PROD%"
