@echo off
rem ---------------------------------------------------------------
rem  Abre la ventana para convertir rotulos a etiquetas 10 x 15.
rem  Doble clic y listo. No abre consola.
rem ---------------------------------------------------------------
cd /d "%~dp0"

where pythonw >nul 2>&1
if not errorlevel 1 (
    start "" pythonw "%~dp0app_etiquetas.pyw"
    goto :eof
)

where pyw >nul 2>&1
if not errorlevel 1 (
    start "" pyw "%~dp0app_etiquetas.pyw"
    goto :eof
)

rem Ultimo recurso: con consola, para que se vea cualquier error.
python "%~dp0app_etiquetas.pyw"
if errorlevel 1 pause
