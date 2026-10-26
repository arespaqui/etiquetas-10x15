@echo off
rem ---------------------------------------------------------------
rem  Arrastra uno o mas PDFs sobre este archivo.
rem  Genera <nombre>_10x15.pdf listo para imprimir en Etiquetas 100x150.
rem ---------------------------------------------------------------
chcp 65001 >nul
setlocal
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"

if "%~1"=="" (
    echo.
    echo   Arrastra uno o mas PDFs sobre este archivo.
    echo.
    goto :end
)

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo.
        echo   ERROR: no se encontro Python en el PATH.
        echo.
        goto :end
    )
    py "etiqueta_10x15.py" %*
    goto :result
)

python "etiqueta_10x15.py" %*

:result
if errorlevel 1 echo.& echo   Hubo errores. Lee los mensajes de arriba.

:end
echo.
pause
