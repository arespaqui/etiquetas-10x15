# Empaquetar el ejecutable de Windows

Esta carpeta explica cómo se construye el `.exe` que se publica en Releases.
El script hace todo: crea un entorno virtual temporal, instala las versiones
fijadas y corre PyInstaller con las banderas exactas.

## Requisitos

- **Windows** (el resultado es un ejecutable de Windows de 64 bits).
- **Python 3.12 en el `PATH`** (`python --version`). Se usa sólo para crear el
  entorno virtual de compilación; el `.exe` final **no** necesita Python.
- Conexión a internet la primera vez (pip baja PyMuPDF, Pillow y PyInstaller).

## Un solo comando

Desde la raíz de `publico-10x15/`:

```
powershell -NoProfile -ExecutionPolicy Bypass -File empaquetar\construir.ps1
```

Tarda unos minutos. Si querés ver el detalle del build, agregá
`-ConservarEntorno` para que no borre la carpeta temporal al terminar.

## Qué hace el script, paso por paso

1. Crea `%TEMP%\etiquetas-10x15-build-<aleatorio>\venv`, **fuera del
   repositorio**. Ni el entorno virtual, ni el `build/`, ni el `.spec` de
   PyInstaller quedan dentro del paquete público: el único resultado que entra
   es `dist/` (que está en `.gitignore`).
2. Instala versiones fijas, con reintentos porque esta red ya falló antes:

   ```
   pip install --retries 5 --timeout 60 pymupdf==2.0 pillow==12.2.0 pyinstaller==6.22.3 pyinstaller-hooks-contrib==2026.9
   ```

   **PyInstaller y `pyinstaller-hooks-contrib` son herramientas de desarrollo.**
   No van a `requirements.txt`: ese archivo es para correr desde el código fuente
   y sólo lleva `pymupdf` y `pillow`. Si `pip` falla, el script corta con el
   código de error y no reintenta en bucle.
3. Corre PyInstaller:

   ```
   pyinstaller --noconfirm --clean --onedir --windowed
       --name "Etiquetas 10x15"
       --distpath <repo>\dist --workpath <temp>\work --specpath <temp>\spec
       --add-data <repo>\LEEME.md;.
       --add-data <repo>\LICENSE;.
       --add-data <repo>\NOTICE;.
       --paths <repo>
       --exclude-module pymupdf.layout --exclude-module onnxruntime --exclude-module numpy
       app_etiquetas.pyw
   ```
4. Imprime la ruta del ejecutable, el tamaño de la carpeta, el tamaño del `.exe`
   y su SHA-256 (para las notas de la versión).
5. Borra la carpeta temporal (sólo la que creó el propio script).

## Por qué `--onedir` y no `--onefile`

Con `--onefile` el `.exe` se descomprime en una carpeta temporal **en cada
arranque**: tarda varios segundos en abrir y, sobre todo, un binario que se
autoextrae se parece demasiado al patrón que buscan los antivirus. En una
descarga pública eso se traduce en falsos positivos y en gente que no puede
abrir la herramienta.

Con `--onedir` el `.exe` arranca rápido y no se autoextrae. Se paga con una
carpeta en vez de un archivo suelto: por eso el `.zip` de Releases se
descomprime **completo** y el `.exe` no se separa de su carpeta `_internal\`.

`--windowed` deja la aplicación sin ventana de consola (es una app de tkinter).
Los errores no se pierden: la app los muestra en pantalla y los escribe en
`errores.log`, **junto al `.exe`** (`dist\Etiquetas 10x15\errores.log`).
Empaquetada, `__file__` vive dentro de `_internal\`, así que un log escrito ahí
no lo encuentra nadie: por eso el log va al lado del ejecutable.

La variable de entorno `ETIQUETAS_10X15_LOG` **gana siempre**: si tiene una ruta,
la app escribe ahí y no junto al `.exe`. Sirve para mandar el log a otro lado
cuando la carpeta del ejecutable es de sólo lectura (por ejemplo, `Program
Files`) o cuando alguien quiere juntar los registros de varias corridas.

## Por qué se excluyen `pymupdf.layout`, `onnxruntime` y `numpy`

Medido: PyMuPDF 2.0 hace `import pymupdf.layout` al cargarse, y ese subpaquete
necesita modelos ONNX en disco (`pymupdf\layout\resources\onnx\*.onnx`,
`*.yaml`). PyInstaller **no** recolecta esos archivos de datos, así que un bundle
compilado sin exclusiones moría al importar PyMuPDF (reproducido con un build de
prueba del mismo motor, mismas versiones):

```
FileNotFoundError: ...\_internal\pymupdf\layout/resources/onnx/layout_rf2.4.1+imf1.yaml
```

Este conversor no usa análisis de layout (no llama a `get_layout()` ni a las
tablas), así que se excluye ese subpaquete y PyMuPDF cae a su camino normal
(`try: import pymupdf.layout / except ImportError: pass`).
Efectos medidos en el build de la app: el import funciona dentro del bundle y la
carpeta baja de ~147 MB a 77,4 MiB, porque se van también `onnxruntime` y
`numpy`, que sólo entraban por el layout.

Si alguna vez se necesita análisis de layout, hay que sacar las tres
exclusiones **y** agregar los recursos como datos (`--collect-data pymupdf`).

## Salida esperada

```
dist\Etiquetas 10x15\
├── Etiquetas 10x15.exe          <- el que se hace doble clic
├── errores.log                  <- aparece sólo si algo falló (junto al .exe)
└── _internal\                   <- intérprete, PyMuPDF, tkinter, datos
    ├── LEEME.md                 <- instrucciones dentro del paquete
    └── LICENSE, NOTICE          <- AGPL-3.0 y aviso de PyMuPDF/MuPDF
```

El log queda **al lado** del `.exe`, no dentro de `_internal\`. Si
`ETIQUETAS_10X15_LOG` tiene una ruta, el log va a esa ruta y no a `dist\`.

Medición de la última corrida (Windows 11, Python 3.12.10). Los tamaños y el hash del
binario cambian en cada compilación: sirven para verificar una descarga puntual, no
para comparar builds entre sí. Las versiones de las herramientas sí son fijas.

| Dato | Valor |
|---|---|
| Ejecutable | `dist\Etiquetas 10x15\Etiquetas 10x15.exe` |
| Tamaño del `.exe` | alrededor de 4,6 MB (varía unos cientos de bytes por corrida) |
| SHA-256 del `.exe` | cambia en cada compilación; el `construir.ps1` lo imprime al terminar |
| Tamaño de la carpeta | alrededor de 77,5 MiB en ~968 archivos |
| `pymupdf` | 2.0 |
| `pillow` | 12.2.0 |
| `pyinstaller` | 6.22.3 |
| `pyinstaller-hooks-contrib` | 2026.9 |

## Reproducibilidad: hasta dónde llega

Con las versiones fijadas, dos corridas dan el mismo tamaño de `.exe`, la misma
cantidad de archivos y el mismo comportamiento. **El SHA-256 no es idéntico
entre corridas**: PyInstaller mete marcas de tiempo en el `.exe`, así que el
hash cambia aunque el contenido sea el mismo. Por eso el hash sirve para
verificar una descarga puntual, no para comparar dos compilaciones.

## Cómo verificar el ejecutable

1. Doble clic en `dist\Etiquetas 10x15\Etiquetas 10x15.exe`. Tiene que abrirse
   la ventana **Etiquetas 10 x 15 cm** sin consola y sin avisos rojos.
2. Elegí un PDF de rótulo y confirmá que aparece `<nombre>_10x15.pdf` al lado
   del original. No hace falta imprimir nada para probarlo.
3. Si algo falla, mirá `dist\Etiquetas 10x15\errores.log` (al lado del `.exe`),
   salvo que hayas definido `ETIQUETAS_10X15_LOG`, que manda siempre.

## Antivirus y SmartScreen: el `.exe` no está firmado

El ejecutable **no está firmado digitalmente**: firmar requiere un certificado
de code signing que este proyecto no tiene. Consecuencias concretas, para que
nadie se asuste ni desconfíe de más:

- Windows puede mostrar **"Windows protegió tu PC"** (SmartScreen). Se sigue con
  *Más información → Ejecutar de todas formas*.
- Algunos antivirus marcan el arranque de PyInstaller como sospechoso
  (heurística de "autoextraíble" o "binario nuevo sin reputación"). Es un falso
  positivo conocido de PyInstaller, no un virus.
- La forma de verificarlo sin confiar en el binario: el código fuente está en el
  repositorio, cualquiera puede leerlo, y cualquiera puede compilar su propio
  `.exe` con este script.
- Si publicás una versión, publicá también el SHA-256 del `.exe` (el script lo
  imprime) para que quien descarga pueda comprobarlo con `certutil -hashfile
  "Etiquetas 10x15.exe" SHA256`.
