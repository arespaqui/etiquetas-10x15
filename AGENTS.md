# AGENTS.md — reglas del repo "Etiquetas 10x15"

Este archivo sirve para las personas y para los agentes que trabajan en el repo.
Dice qué es el proyecto, cómo se corre, qué no se puede romper y qué no se puede
tocar. Si algo de acá choca con el `README.md`, manda este archivo para el
desarrollo y el `README.md` para el usuario.

## Qué es este repo

Una herramienta de escritorio para Windows que convierte un PDF de rótulo (A4,
oficio, lo que venga) en un PDF de **100 × 150 mm exactos**, listo para imprimir
en una etiqueta térmica de 10 × 15 cm. Se distribuye como código fuente
(**AGPL-3.0**) y como ejecutable de Windows.

Es un proyecto **independiente**: no es software oficial de Correo Argentino, no
está afiliado a Correo Argentino y no reemplaza ningún sistema oficial.

**Todo lo que entra acá se publica.** No hay lugar para datos privados: ni PDFs
reales, ni nombres, ni direcciones, ni números de seguimiento, ni rutas de la
máquina de nadie.

## Mapa del repo

```
.
├── app_etiquetas.pyw          Ventana (tkinter). Sin hilos. Sin errores silenciosos.
├── etiqueta_10x15.py          Motor: detecta el marco, recorta el aire, escala. Sin GUI.
├── verificar.py               Control de calidad de un PDF ya convertido.
├── 1 - Abrir Etiquetas 10x15.bat      Abre la ventana (pythonw, sin consola).
├── 2 - Arrastrar PDF (alternativa).bat  Convierte sin ventana, arrastrando PDFs.
├── tests/
│   ├── soporte.py             Arma y mide PDFs sintéticos. Única fuente de fixtures.
│   ├── test_recorte_conservador.py     La guarda del recorte (S5).
│   └── test_errores_visibles.py        Log y avisos de error (S7).
├── empaquetar/
│   ├── construir.ps1          Build reproducible del .exe (PyInstaller).
│   └── README.md              Cómo se construye y por qué --onedir.
├── docs/imagenes/             Capturas y diagramas usados por el README.
├── docs/manual.md             Manual de uso: cuándo usarlo, cuándo no, problemas.
├── docs/marca/                Logo, tarjeta para redes y paleta de Ardamir.
├── .github/                   CI de pruebas y plantillas de issues.
├── README.md                  Documentación principal, para el usuario.
├── LEEME.md                   Guía corta del usuario final.
├── CONTRIBUTING.md            Reglas para mandar cambios.
├── CHANGELOG.md               Keep a Changelog.
├── LICENSE                    AGPL-3.0 completa. No se toca.
├── NOTICE                     Aviso de PyMuPDF/MuPDF (Artifex). No se toca.
└── requirements.txt           Dependencias fijas: pymupdf==2.0, pillow==12.2.0
```

## Comandos

Instalar dependencias (desde la raíz del repo):

```
python -m pip install -r requirements.txt
```

Correr la ventana:

```
python app_etiquetas.pyw
```

Convertir sin ventana:

```
python etiqueta_10x15.py rotulo.pdf
```

Control de calidad de un PDF convertido:

```
python verificar.py rotulo_10x15.pdf
```

Correr las pruebas (runner oficial; `unittest` de la biblioteca estándar):

```
python -m unittest discover -s tests -t .
```

Una sola prueba:

```
python -m unittest tests.test_recorte_conservador -v
```

Construir el ejecutable de Windows (Windows + Python 3.12 en el `PATH`; tarda unos
minutos y deja el resultado en `dist/`, que no se versiona):

```
powershell -NoProfile -ExecutionPolicy Bypass -File empaquetar\construir.ps1
```

## Reglas del proyecto

Estas cinco primeras son el motivo de ser de la herramienta. Romper una es un
error, aunque las pruebas pasen.

1. **La escala es siempre uniforme.** Nunca estirar para llenar la etiqueta. Un
   código de barras deformado puede no escanear, y una etiqueta rechazada cuesta
   más que todo este proceso.
2. **El PDF original no se toca nunca.** La salida es siempre un archivo nuevo
   `<nombre>_10x15.pdf`; si ya existe, se agrega `(2)`, `(3)`, etc.
3. **El recorte es conservador.** El aire del final se recorta sólo si hay 5 mm o
   más de blanco, siempre con 2 mm de margen, y **nunca** si hay contenido visible
   que el cálculo no pueda ver (imágenes, dibujos anchos): en ese caso no recorta
   y avisa. Si el recorte tiene que decidir entre "más grande" y "no perder
   contenido", gana "no perder contenido".
4. **Ningún error en silencio.** Todo fallo se muestra en la ventana y queda en
   `errores.log` (junto al `.exe` si está empaquetada, junto al `.pyw` si no, o
   donde diga `ETIQUETAS_10X15_LOG`). La ventana corre con `pythonw`: no hay
   consola que mirar.
5. **La detección se gana el derecho a recortar.** El marco se detecta por
   geometría vectorial y se valida contra el texto; si no aparece, se cae al área
   con tinta y se avisa. Nada de rectángulos escritos a mano.

Y estas otras, sobre cómo se trabaja acá:

6. **Todo lo visible va en español**: ventana, mensajes, documentación. Los
   comentarios de código pueden quedar en inglés, como ya están.
7. **Las pruebas usan sólo PDFs sintéticos** generados por el propio test
   (`tests/soporte.py`). Nunca fixtures copiados de casos reales.
8. **Un cambio, un tema**: el arreglo, su prueba y la documentación que lo explica
   van juntos. Si cambia el uso, se actualiza `README.md` y `LEEME.md`; si se nota
   desde afuera, se anota en `CHANGELOG.md`.
9. **Primero la prueba que falla.** Para un error de comportamiento: se escribe la
   prueba que lo reproduce, se ve fallar, se arregla y se ve pasar.
10. **Sin dependencias nuevas** sin hablarlo antes. `requirements.txt` lleva sólo
    lo que hace falta para correr desde el código fuente; las herramientas de build
    (PyInstaller) viven en `empaquetar/construir.ps1`, no ahí.

## Límites: qué no se toca

- **`LICENSE` y `NOTICE` no se modifican ni se borran.** El proyecto es AGPL-3.0 y
  toda distribución modificada tiene que mantener el código fuente disponible,
  también si se ofrece como servicio en red.
- **No se versiona nada privado ni generado**: PDFs, ZIPs, `_diag/`, respaldos
  `.reg`, `errores.log`, `__pycache__/`, `dist/`, `build/`, `*.spec`, `.venv/`,
  `.atl/`. Está en `.gitignore`; no se agrega `--force`.
- **No se agregan datos de personas** a ningún archivo, ni siquiera en un ejemplo
  o en un mensaje de error: nombres, direcciones, teléfonos, CUIT, números de
  seguimiento. Los ejemplos usan datos de mentira y lo dicen.
- **No se toca la escala ni el orden de las operaciones** del motor (detectar →
  recortar → escalar uniforme → centrar) sin una razón medida y una prueba que la
  respalde.
- **No se agregan remotos, credenciales, tokens ni automatizaciones de publicación**
  sin autorización explícita de quien mantiene el repo.
- **No se reemplazan las imágenes de `docs/imagenes/`** por capturas nuevas sin
  revisar que no muestren datos reales ni rutas personales.

## Si algo no cierra

- Dudas de uso o de comportamiento: [`docs/manual.md`](docs/manual.md) (el
  manual completo, con cuándo usarla y cuándo no), `README.md` (secciones *Cómo
  funciona* y *Solución de problemas*) y `LEEME.md`.
- Dudas de proceso, pruebas o licencia: `CONTRIBUTING.md`.
- Qué cambió y cuándo: `CHANGELOG.md`.
- Cómo se arma el ejecutable y por qué con esas banderas: `empaquetar/README.md`.
