#Requires -Version 5.1
<#
    Construye el ejecutable de Windows de "Etiquetas 10x15" con PyInstaller.

    Reglas que este script respeta (no las rompas):

      1. El entorno virtual y el árbol de trabajo de PyInstaller se crean FUERA
         del repositorio, en la carpeta temporal del sistema. Nunca aparece un
         venv/, un build/ ni un .spec dentro del paquete público.
      2. PyInstaller, pyinstaller-hooks-contrib y todo lo que sólo sirve para
         compilar son herramientas de desarrollo: viven en ese entorno temporal y
         NO se agregan a requirements.txt, que es para correr desde el código
         fuente (pymupdf + pillow).
      3. Se compila --onedir (una carpeta), NO --onefile. Con --onefile el
         ejecutable se descomprime en una carpeta temporal en cada arranque:
         tarda más y, en una descarga pública, dispara más falsos positivos de
         antivirus.
      4. Versiones fijas de punta a punta: mismas versiones, mismo tamaño y mismo
         comportamiento. (El SHA-256 del .exe igual cambia entre corridas, porque
         PyInstaller le mete marcas de tiempo: el hash sirve para verificar una
         descarga puntual, no para comparar dos compilaciones.)

    Uso:

        powershell -NoProfile -ExecutionPolicy Bypass -File empaquetar\construir.ps1

    Opciones:

        -ConservarEntorno    no borra la carpeta temporal al terminar (para depurar)

    Salida esperada:

        dist\Etiquetas 10x15\Etiquetas 10x15.exe      (una carpeta, con _internal\)
#>
[CmdletBinding()]
param(
    [string]$Pymupdf = "2.0",
    [string]$Pillow = "12.2.0",
    [string]$PyInstaller = "6.22.3",
    [string]$Hooks = "2026.9",
    [switch]$ConservarEntorno
)

$ErrorActionPreference = "Stop"

$appName = "Etiquetas 10x15"
$repo = Split-Path -Parent $PSScriptRoot
$entrada = Join-Path $repo "app_etiquetas.pyw"
$distPath = Join-Path $repo "dist"
$tempRoot = [System.IO.Path]::GetTempPath()
$stamp = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$buildRoot = Join-Path $tempRoot "etiquetas-10x15-build-$stamp"
$venvPath = Join-Path $buildRoot "venv"
$workPath = Join-Path $buildRoot "work"
$specPath = Join-Path $buildRoot "spec"
$exePath = Join-Path (Join-Path $distPath $appName) "$appName.exe"

function Paso($texto) { Write-Host "==> $texto" -ForegroundColor Cyan }

function Morir($texto) {
    Write-Host "ERROR: $texto" -ForegroundColor Red
    exit 1
}

# Se calcula con .NET y no con Get-FileHash: hay instalaciones de Windows donde
# ese cmdlet no esta disponible y el build no tiene por que fallar por eso.
function HashSha256($ruta) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($ruta)
    try { $hash = $sha.ComputeHash($stream) } finally { $stream.Dispose(); $sha.Dispose() }
    return (($hash | ForEach-Object { $_.ToString("x2") }) -join "")
}

if (-not (Test-Path -LiteralPath $entrada)) {
    Morir "No encontre $entrada. Corré el script desde empaquetar\ dentro del paquete publico."
}
$pythonBase = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonBase) {
    Morir "No encontre Python 3 en el PATH. Instalalo desde python.org y volvé a intentar."
}

Paso "Python base: $(& $pythonBase.Source --version)"
Paso "Carpeta temporal fuera del repo: $buildRoot"

try {
    Paso "Creando el entorno virtual temporal (nada de esto entra al repo)"
    & $pythonBase.Source -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { Morir "Fallo la creacion del entorno virtual (exit $LASTEXITCODE)." }

    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    $venvPyInstaller = Join-Path $venvPath "Scripts\pyinstaller.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) { Morir "El entorno virtual no tiene python.exe." }

    Paso "Instalando dependencias fijas (con reintentos: esta red ya fallo antes)"
    & $venvPython -m pip install --retries 5 --timeout 60 `
        "pymupdf==$Pymupdf" `
        "pillow==$Pillow" `
        "pyinstaller==$PyInstaller" `
        "pyinstaller-hooks-contrib==$Hooks"
    if ($LASTEXITCODE -ne 0) {
        Morir "Fallo pip (exit $LASTEXITCODE). Sin dependencias no hay build: revisá la salida de arriba."
    }

    Paso "Versiones realmente instaladas"
    & $venvPython -c "from importlib.metadata import version; [print('   ', p, version(p)) for p in ('pymupdf','pillow','pyinstaller','pyinstaller-hooks-contrib')]"
    if ($LASTEXITCODE -ne 0) { Morir "No pude leer las versiones instaladas (exit $LASTEXITCODE)." }

    New-Item -ItemType Directory -Force -Path $workPath, $specPath | Out-Null

    Paso "Compilando con PyInstaller (--onedir --windowed, sin consola)"
    # --add-data: LEEME.md viaja como data para que el .exe lleve sus instrucciones.
    # LICENSE y NOTICE viajan porque el binario distribuido usa PyMuPDF/MuPDF (AGPL-3.0).
    # --exclude-module pymupdf.layout: pymupdf 2.0 importa pymupdf.layout al cargar, y
    #   ese subpaquete necesita modelos ONNX en disco que PyInstaller no recolecta
    #   (sin excluirlo, el bundle falla con FileNotFoundError al importar pymupdf).
    #   Este conversor no usa analisis de layout: se excluye, y pymupdf cae a su
    #   camino normal. De paso se van onnxruntime y numpy (~70 MB menos).
    $argumentos = @(
        "--noconfirm", "--clean",
        "--onedir", "--windowed",
        "--name", $appName,
        "--distpath", $distPath,
        "--workpath", $workPath,
        "--specpath", $specPath,
        "--add-data", "$repo\LEEME.md;.",
        "--add-data", "$repo\LICENSE;.",
        "--add-data", "$repo\NOTICE;.",
        # El isotipo de Ardamir que muestra la ventana. Si falta, la app degrada a texto.
        "--add-data", "$repo\docs\marca\marca.png;docs\marca",
        "--paths", $repo,
        "--exclude-module", "pymupdf.layout",
        "--exclude-module", "onnxruntime",
        "--exclude-module", "numpy",
        $entrada
    )
    & $venvPyInstaller @argumentos
    if ($LASTEXITCODE -ne 0) { Morir "Fallo PyInstaller (exit $LASTEXITCODE). El ejecutable no se genero." }

    if (-not (Test-Path -LiteralPath $exePath)) { Morir "PyInstaller termino pero no encuentro $exePath." }

    $carpeta = Split-Path -Parent $exePath
    $bytes = 0
    Get-ChildItem -LiteralPath $carpeta -Recurse -File | ForEach-Object { $bytes += $_.Length }
    $hash = HashSha256 $exePath

    Write-Host ""
    Write-Host "LISTO" -ForegroundColor Green
    Write-Host "  ejecutable : $exePath"
    Write-Host ("  carpeta    : {0} ({1:N1} MiB, {2} archivos)" -f $carpeta, ($bytes / 1MB), (Get-ChildItem -LiteralPath $carpeta -Recurse -File).Count)
    Write-Host ("  exe        : {0:N0} bytes  sha256 {1}" -f (Get-Item -LiteralPath $exePath).Length, $hash)
    Write-Host ""
    Write-Host "  Probalo antes de publicarlo: empaquetar\README.md, seccion 'Como verificar el ejecutable'."
}
finally {
    if ($ConservarEntorno) {
        Write-Host "Entorno conservado para depurar: $buildRoot" -ForegroundColor Yellow
    }
    elseif (Test-Path -LiteralPath $buildRoot) {
        # Sólo se borra la carpeta temporal que este script acaba de crear.
        $esTemporal = $buildRoot.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)
        $esPropia = (Split-Path -Leaf $buildRoot).StartsWith("etiquetas-10x15-build-")
        if ($esTemporal -and $esPropia) {
            Remove-Item -LiteralPath $buildRoot -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "Carpeta temporal borrada: $buildRoot"
        }
    }
}
