#!/usr/bin/env python3
"""Ventana para convertir rotulos a etiquetas de 100 x 150 mm.

Pensada para usarse sin saber nada de comandos: elegir el PDF, convertir,
abrir el resultado. El motor vive en etiqueta_10x15.py.

Dos reglas que sostienen esto:
  1. Nada de hilos. Tkinter no es thread-safe y root.after() desde un hilo
     secundario puede matar la ventana sin dejar rastro. La conversion es
     rapida: se hace en el hilo principal mostrando el avance.
  2. Ningun error puede ser silencioso. Con pythonw no hay consola, asi que
     todo se escribe en errores.log junto a la app (o junto al .exe si esta
     empaquetada).

Donde queda errores.log, en orden de prioridad:
  1. Si existe la variable de entorno ETIQUETAS_10X15_LOG, se escribe ahi
     (sirve para diagnosticar o para las pruebas).
  2. Si la app corre empaquetada (PyInstaller, getattr(sys, "frozen", False)),
     junto al ejecutable: Path(sys.executable).parent. Empaquetada, __file__
     vive dentro de _internal, y un log ahi no lo encuentra nadie.
  3. Si corre desde el codigo fuente, al lado de este archivo .pyw.

La superficie principal habla en castellano comun: medida, escala y, si hace
falta, un aviso entendible. La jerga de la conversion (area de origen, area
impresa, proporcion, deformacion) vive detras de «Ver detalle tecnico», que
arranca oculto.
"""

import glob
import os
import re
import sys
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Etiquetas 10 x 15 cm"

# El log se puede redirigir con esta variable de entorno; manda sobre todo lo demas.
LOG_ENV_VAR = "ETIQUETAS_10X15_LOG"
LOG_FILENAME = "errores.log"

# Make the engine importable no matter which directory we were launched from.
_HERE = os.path.dirname(os.path.abspath(__file__))


def log_path():
    """Devuelve la ruta del log de errores.

    Tres casos, en este orden:
      1. ETIQUETAS_10X15_LOG con una ruta: escribe ahi, gana siempre.
      2. App empaquetada (sys.frozen): errores.log junto al ejecutable.
      3. Codigo fuente: errores.log junto a este archivo .pyw.
    """
    override = os.environ.get(LOG_ENV_VAR, "").strip()
    if override:
        return os.path.abspath(os.path.expanduser(override))
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).parent / LOG_FILENAME)
    return os.path.join(_HERE, LOG_FILENAME)


def write_log(text):
    """Agrega texto al log. Nunca levanta: con pythonw nadie veria el error.

    Devuelve True si pudo escribir, False si no (por ejemplo, sin permisos).
    """
    try:
        with open(log_path(), "a", encoding="utf-8") as handle:
            handle.write(text)
        return True
    except Exception:
        return False

# Make the engine importable no matter which directory we were launched from.
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    import etiqueta_10x15 as engine
except Exception:
    tk.Tk().withdraw()
    messagebox.showerror("Falta un archivo",
                         "No se pudo cargar el motor etiqueta_10x15.py:\n\n%s"
                         % traceback.format_exc(limit=2))
    sys.exit(1)


# ---------------------------------------------------------------- identidad

# Tokens de marca medidos (docs/marca/paleta.md). No inventar variantes.
FONDO = "#0F1D2A"
PANEL = "#162833"
PANEL_ALTO = "#1E3441"
DORADO = "#C9A24C"
DORADO_HOVER = "#D6A547"
VINO = "#5A0001"           # acento de peso: reservado, no hace falta en pantalla
CREMA = "#F5EFDF"
APAGADO = "#9AAAB8"
AVISO = "#E5AC63"           # ámbar de texto: más claro para leerse sobre el panel
AVISO_BARRA = "#D98E32"     # ámbar de la barra lateral: sólo ahí
ERROR = "#A8353A"

FAMILIA_TITULO = "Georgia"     # la serif de la marca
FAMILIA_TEXTO = "Segoe UI"     # todo lo demas
FAMILIA_TECNICA = "Consolas"   # solo detalle tecnico

ANCHO_VENTANA = 900
ALTO_VENTANA = 700
ANCHO_MINIMO = 760
ALTO_MINIMO = 600
ALTO_LOGO = 44
ANCHO_ACCION = 420
ALTO_ACCION = 56

# Textos de la superficie principal. Sin jerga: eso vive en el detalle tecnico.
TEXTO_ACCION = "Elegir PDF y convertir"
TEXTO_OCUPADO = "Convirtiendo…"
TEXTO_VACIO = "Acá van a aparecer tus etiquetas convertidas"
PISTA_SOLTAR = "También podés soltar los PDF sobre «2 - Arrastrar PDF»"
PISTA_SELECCION = "También podés elegir varios PDF a la vez"
PATRON_ARRASTRAR = "2 - Arrastrar PDF*.bat"
TEXTO_ENLACE_DETALLE = "Ver detalle técnico"
TEXTO_ENLACE_OCULTAR = "Ocultar detalle técnico"

# Instrucciones dentro de la ventana: tres pasos, siempre visibles, sin jerga.
TEXTO_INSTRUCCIONES = "Cómo se usa"
PASOS_USO = (
    "Elegí el PDF del rótulo.",
    "Convertí: sale un archivo nuevo al lado; el original no se toca.",
    "Imprimí con papel de 100 × 150 mm y escala «Tamaño real».",
)

# Borde del estado vacío: gris apagado, punteado, para no competir con el botón.
BORDE_PUNTEADO = "#3A4E5C"
GUION_PUNTEADO = (6, 6)

# Estado de la tarjeta: color para el texto, color para la barra lateral y una
# palabra corta que lo diga sin depender del color.
ETIQUETA_ESTADO = {"ok": "Listo", "aviso": "Revisá", "error": "Error"}
COLOR_ESTADO = {"ok": DORADO, "aviso": AVISO, "error": ERROR}
COLOR_BARRA = {"ok": DORADO, "aviso": AVISO_BARRA, "error": ERROR}
ESTILO_SCROLL = "Ardamir.Vertical.TScrollbar"


def preparar_estilos(root):
    """Deja las barras de scroll oscuras y finas, sin paquetes de temas.

    ttk con el tema `clam` es lo unico que respeta los colores en Windows: el
    tema nativo `vista` pinta la barra de gris claro y rompe la identidad.
    """
    try:
        estilo = ttk.Style(root)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure(ESTILO_SCROLL, background=PANEL, troughcolor=FONDO,
                         bordercolor=FONDO, darkcolor=PANEL, lightcolor=PANEL,
                         arrowcolor=APAGADO, width=10, arrowsize=10)
        estilo.map(ESTILO_SCROLL, background=[("active", DORADO)])
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- logica pura

def convert_many(paths):
    """Convert every PDF in paths. Returns a list of result dicts.

    No Tkinter, no printing: los errores de cada archivo se devuelven en la fila
    del resultado y ademas quedan anotados en el log (S7). This is the exact code
    path the button uses, so it can be tested from a console.
    """
    results = []
    for source in paths:
        if not source.lower().endswith(".pdf"):
            continue
        base, ext = os.path.splitext(source)
        target = base + "_10x15" + ext
        counter = 2
        while os.path.exists(target):
            target = "%s_10x15 (%d)%s" % (base, counter, ext)
            counter += 1
        try:
            rows, warnings = engine.convert(source, target)
            results.append({"source": source, "target": target,
                            "rows": rows, "warnings": warnings, "error": None})
        except Exception as exc:
            write_log("\n=== no se pudo convertir %s ===\n%s"
                      % (source, traceback.format_exc()))
            results.append({"source": source, "target": None,
                            "rows": [], "warnings": [], "error": str(exc)})
    return results



def human_note(row):
    """Turn a conversion row into one plain sentence for the user, or None."""
    if not row.get("frame_found", True):
        return ("No encontré el marco del rótulo en esta página: usé el área con tinta, "
                "que puede incluir marcas sueltas de la hoja. Revisá el resultado antes de imprimir.")
    if row["mismatch"] <= engine.ASPECT_TOLERANCE:
        return None
    return ("El rótulo de origen no tiene forma 10×15: quedó con %.0f mm de blanco a cada lado, "
            "a escala %.0f %% y sin deformar los códigos. Conviene pedir el rótulo en formato "
            "10×15 al origen." % (row["margin_x"], row["scale"]))


def summarize(results):
    """Return (status_text, colour) so the window and tests agree."""
    if not results:
        return "No elegiste ningún PDF.", AVISO
    errors = [r for r in results if r["error"]]
    converted = [r for r in results if not r["error"]]
    warned = [r for r in converted if r["warnings"]]
    if errors and not converted:
        return "No se pudo convertir ningún archivo. Abrí «Ver detalle técnico».", ERROR
    if errors:
        return ("Convertidos %d de %d. Abrí «Ver detalle técnico» para ver qué pasó con el resto."
                % (len(converted), len(results)), AVISO)
    if warned:
        return "Convertido, con un aviso para revisar antes de imprimir.", AVISO
    if len(converted) == 1:
        return "Listo: 1 rótulo convertido al tamaño exacto.", DORADO
    return ("Listo: %d rótulos convertidos al tamaño exacto." % len(converted), DORADO)


def _numero_corto(texto):
    """'100.0' -> '100'; '99.5' -> '99,5'."""
    try:
        valor = float(texto)
    except (TypeError, ValueError):
        return None
    if abs(valor - round(valor)) < 0.05:
        return "%d" % int(round(valor))
    return ("%.1f" % valor).replace(".", ",")


def row_summary_line(row):
    """Segunda línea de la tarjeta: medida, escala y blanco, en lenguaje comun."""
    numeros = re.findall(r"\d+(?:[.,]\d+)?", str(row.get("printed", "")))
    ancho = _numero_corto(numeros[0]) if len(numeros) > 0 else None
    alto = _numero_corto(numeros[1]) if len(numeros) > 1 else None
    medida = "%s × %s mm" % (ancho or "100", alto or "150")

    escala = _numero_corto(row.get("scale", 100.0)) or "100"
    partes = [medida, "escala %s %%" % escala]

    margen = row.get("margin_x", 0.0) or 0.0
    if margen >= 1.0:
        partes.append("%.0f mm de blanco a cada lado" % margen)
    return " · ".join(partes)


def hint_text():
    """Pista bajo el botón. Sólo promete arrastrar si el .bat está al lado.

    Empaquetada mira únicamente la carpeta del ejecutable, que es donde el
    usuario vería el .bat: el ejecutable no lo lleva, así que ahí la pista de
    arrastre sería mentira.
    """
    if getattr(sys, "frozen", False):
        bases = [str(Path(sys.executable).parent)]
    else:
        bases = [_HERE]
    for base in bases:
        try:
            if glob.glob(os.path.join(base, PATRON_ARRASTRAR)):
                return PISTA_SOLTAR
        except Exception:
            continue
    return PISTA_SELECCION


def _avisos_crudos_de_fila(row):
    """Avisos de una página, en minúscula y sin prefijo: la tarjeta los agrupa."""
    if not row.get("frame_found", True):
        return ["no encontré el marco del rótulo: usé el área con tinta, "
                "que puede traer marcas sueltas de la hoja. Revisá el resultado."]
    if (row.get("mismatch", 0.0) or 0.0) > engine.ASPECT_TOLERANCE:
        return ["el rótulo original no es bien 10 × 15: quedó centrado y con "
                "blanco a los lados. Pedilo en 10 × 15."]
    return []


def _infos_crudas_de_fila(row, varias_paginas):
    """Información neutra de una página, en minúscula y sin prefijo.

    Con varias páginas el recorte dice cuántos milímetros de aire sacó: si no,
    cada página repetiría la misma frase y el número quedaría invisible.
    """
    milimetros = row.get("trimmed_mm", 0.0) or 0.0
    if milimetros <= 0:
        return []
    if varias_paginas:
        return ["recorté %s mm de aire al final para que el rótulo entre más grande."
                % _numero_corto(milimetros)]
    return ["recorté el aire que sobraba abajo para que el rótulo entre más grande."]


def _con_prefijo(lineas, prefijo):
    """Con varias páginas antepone «Página N: »; con una sola, mayúscula inicial."""
    if not lineas:
        return []
    if prefijo:
        return [prefijo + linea for linea in lineas]
    return [linea[0].upper() + linea[1:] for linea in lineas]


def _tramos_de_paginas(paginas):
    """[1, 2, 3, 5] -> [[1, 3], [5, 5]]: los números contiguos se juntan."""
    tramos = []
    for pagina in sorted(set(paginas)):
        if tramos and pagina == tramos[-1][1] + 1:
            tramos[-1][1] = pagina
        else:
            tramos.append([pagina, pagina])
    return tramos


def _prefijo_de_paginas(paginas):
    """«Página 4: » o «Páginas 2-3: », con los tramos que hagan falta."""
    tramos = [("%d-%d" % (desde, hasta)) if desde != hasta else "%d" % desde
              for desde, hasta in _tramos_de_paginas(paginas)]
    rango = tramos[0] if len(tramos) == 1 else ", ".join(tramos[:-1]) + " y " + tramos[-1]
    if len(set(paginas)) == 1:
        return "Página %s: " % rango
    return "Páginas %s: " % rango


def _agrupar_por_paginas(rows, textos_de_fila):
    """[(texto, [páginas])] en orden de aparición; textos idénticos se juntan."""
    grupos = []
    indice = {}
    for row in rows:
        pagina = row.get("page", 1)
        for texto in textos_de_fila(row):
            paginas = indice.get(texto)
            if paginas is None:
                paginas = []
                indice[texto] = paginas
                grupos.append((texto, paginas))
            if pagina not in paginas:
                paginas.append(pagina)
    return grupos


def _lineas_por_concepto(rows, textos_de_fila):
    """Una línea por concepto: sin prefijo si vale para todas las páginas.

    Repetir el mismo aviso siete veces porque cambia el número de página es una
    pared de texto: el número sólo aparece cuando el aviso no es de todas.
    """
    varias = len(rows) > 1
    todas = set(row.get("page", 1) for row in rows)
    lineas = []
    for texto, paginas in _agrupar_por_paginas(rows, textos_de_fila):
        if varias and set(paginas) != todas:
            lineas.append(_prefijo_de_paginas(paginas) + texto)
        else:
            lineas.append(texto[0].upper() + texto[1:])
    return lineas


def _resumen_lineas(rows):
    """Resumen de la tarjeta: una línea si todas las páginas dicen lo mismo.

    Con más de una página la línea arranca con el total, que es el dato que el
    usuario necesita para saber que convirtió todo.
    """
    if len(rows) > 1 and len(set(row_summary_line(row) for row in rows)) == 1:
        return ["%d páginas · %s" % (len(rows), row_summary_line(rows[0]))]
    return _lineas_por_concepto(rows, lambda row: [row_summary_line(row)])


def result_warning_lines(result):
    """Avisos de la tarjeta: lo que el usuario tiene que revisar. En ámbar o rojo."""
    if result.get("error"):
        return ["No se pudo convertir. Abrí «Ver detalle técnico» para saber por qué."]
    return _lineas_por_concepto(result.get("rows") or [], _avisos_crudos_de_fila)


def result_info_lines(result):
    """Información neutra de la tarjeta: gris apagado, sin barra de aviso.

    El recorte de aire es lo que hizo la conversión, no algo que haya que
    revisar: si compite con los avisos reales, los avisos se pierden.
    """
    if result.get("error"):
        return []
    rows = result.get("rows") or []
    varias = len(rows) > 1
    return _lineas_por_concepto(rows, lambda row: _infos_crudas_de_fila(row, varias))


def card_status(result):
    """'ok' (dorado), 'aviso' (ámbar) o 'error' (rojo) para la tarjeta."""
    if result.get("error"):
        return "error"
    if result.get("warnings") or result_warning_lines(result):
        return "aviso"
    return "ok"


def card_lines(result):
    """Las líneas de la tarjeta, en orden, sin tocar Tk.

    Devuelve (estado, líneas). Cada línea es un dict con 'texto', 'clase' y
    'estado'. 'clase' decide el color: 'resumen' e 'info' van en gris apagado
    ('info' es información neutra, sin barra de aviso); 'revisar' va en ámbar o
    en rojo. 'estado' marca la única línea que estrena la palabra del estado
    («Listo», «Revisá», «Error»), que es la segunda línea de la tarjeta.

    Cada concepto ocupa como mucho una línea: las páginas que dicen lo mismo
    se agrupan en vez de repetir el mismo texto página por página.
    """
    estado = card_status(result)
    lineas = []
    estrena = True
    if not result.get("error"):
        for resumen in _resumen_lineas(result.get("rows") or []):
            lineas.append({"texto": resumen, "clase": "resumen",
                           "estado": estrena})
            estrena = False
    for aviso in result_warning_lines(result):
        lineas.append({"texto": aviso, "clase": "revisar", "estado": estrena})
        estrena = False
    for info in result_info_lines(result):
        lineas.append({"texto": info, "clase": "info", "estado": False})
    return estado, lineas


def technical_detail(results):
    """Texto monospace viejo, con toda la jerga. Vive oculto por defecto."""
    lineas = []
    for result in results:
        nombre = os.path.basename(result.get("source") or "?")
        if result.get("error"):
            lineas.append("X %s" % nombre)
            lineas.append("   no se pudo convertir: %s" % result["error"])
            continue
        lineas.append("OK  %s  ->  %s"
                      % (nombre, os.path.basename(result.get("target") or "")))
        for row in result.get("rows") or []:
            lineas.append("   página %d: origen %s  →  %s  (escala %.0f %%)"
                          % (row["page"], row["source"], row["printed"], row["scale"]))
            if row.get("trimmed_mm", 0) > 0:
                lineas.append("   recorté %.0f mm de blanco del final: el rótulo entra más grande"
                              % row["trimmed_mm"])
            note = human_note(row)
            if note:
                lineas.append("   ! %s" % note)
        for aviso in result.get("warnings") or []:
            lineas.append("   · %s" % aviso)
        lineas.append("")
    return "\n".join(lineas)


def default_logo_path():
    """Ruta del isotipo de la marca, resuelta desde el propio script.

    Empaquetada con PyInstaller primero busca `sys._MEIPASS` (donde viajan los
    datos), después la carpeta del ejecutable y por último el código fuente.
    Devuelve una ruta aunque el archivo no exista: `App` decide qué hacer.
    """
    nombres = [os.path.join("docs", "marca", "marca.png"), "marca.png"]
    bases = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            bases.append(meipass)
        bases.append(str(Path(sys.executable).parent))
    bases.append(_HERE)

    for base in bases:
        for nombre in nombres:
            candidato = os.path.join(base, nombre)
            if os.path.isfile(candidato):
                return candidato
    return os.path.join(_HERE, nombres[0])


def load_logo_image(path, alto=ALTO_LOGO):
    """Carga el isotipo con PIL a `alto` px. Devuelve None si no se puede."""
    try:
        from PIL import Image, ImageTk
    except Exception:
        return None
    try:
        imagen = Image.open(path).convert("RGBA")
        escala = float(alto) / float(imagen.height or 1)
        ancho = max(1, int(round(imagen.width * escala)))
        imagen = imagen.resize((ancho, alto), Image.LANCZOS)
        return ImageTk.PhotoImage(imagen)
    except Exception:
        return None


def _elegir_familia(raiz, preferida, por_defecto="TkDefaultFont"):
    """Devuelve `preferida` si está instalada; si no, la default sin romper."""
    try:
        from tkinter import font as tkfont
        instaladas = set(tkfont.families(raiz))
    except Exception:
        return por_defecto
    return preferida if preferida in instaladas else por_defecto


def _rectangulo_redondeado(canvas, x1, y1, x2, y2, radio, **opciones):
    """Rectángulo de esquinas redondeadas dibujado a mano (sin paquetes de temas)."""
    puntos = [
        x1 + radio, y1, x2 - radio, y1, x2, y1,
        x2, y1 + radio, x2, y2 - radio, x2, y2,
        x2 - radio, y2, x1 + radio, y2, x1, y2,
        x1, y2 - radio, x1, y1 + radio, x1, y1,
    ]
    return canvas.create_polygon(puntos, smooth=True, **opciones)


# ---------------------------------------------------------------- interfaz

class App:
    def __init__(self, root, logo_path=None):
        self.root = root
        self.last_dir = os.path.expanduser("~")
        self.results = []
        self.logo_image = None
        self._accion_activa = True
        self._vacio = True
        self.canvas_vacio = None

        self.f_titulo = _elegir_familia(root, FAMILIA_TITULO, "Georgia")
        self.f_texto = _elegir_familia(root, FAMILIA_TEXTO, "TkDefaultFont")
        self.f_tecnica = _elegir_familia(root, FAMILIA_TECNICA, "TkFixedFont")

        root.title(APP_TITLE)
        root.configure(bg=FONDO)
        root.minsize(ANCHO_MINIMO, ALTO_MINIMO)
        preparar_estilos(root)
        self._centrar(ANCHO_VENTANA, ALTO_VENTANA)

        self._construir_encabezado(logo_path)
        self._construir_accion()
        self._construir_instrucciones()
        self._construir_resultados()
        self._construir_pie()

        self.set_status("Elegí un PDF y listo: el resto es automático.", APAGADO)
        self._render_empty_state()

    # ---------- disposición ----------

    def _centrar(self, ancho, alto):
        """Ventana centrada a lo ancho y un poco arriba del centro vertical."""
        try:
            pantalla_w = self.root.winfo_screenwidth()
            pantalla_h = self.root.winfo_screenheight()
        except Exception:
            pantalla_w, pantalla_h = ancho, alto
        x = max(0, (pantalla_w - ancho) // 2)
        y = max(0, (pantalla_h - alto) // 3)
        self.root.geometry("%dx%d+%d+%d" % (ancho, alto, x, y))

    def _construir_encabezado(self, logo_path):
        cabecera = tk.Frame(self.root, bg=FONDO)
        cabecera.pack(fill="x", padx=28, pady=(22, 6))

        ruta_logo = logo_path if logo_path else default_logo_path()
        self.logo_image = load_logo_image(ruta_logo) if os.path.isfile(ruta_logo) else None
        if self.logo_image is not None:
            tk.Label(cabecera, image=self.logo_image, bg=FONDO).pack(
                side="left", padx=(0, 16))

        bloque = tk.Frame(cabecera, bg=FONDO)
        bloque.pack(side="left", fill="x", expand=True)
        tk.Label(bloque, text="Etiquetas 10 × 15", font=(self.f_titulo, 26, "bold"),
                 fg=CREMA, bg=FONDO, anchor="w").pack(fill="x")
        tk.Label(bloque, text="Rótulos a 100 × 150 mm exactos",
                 font=(self.f_texto, 11), fg=APAGADO, bg=FONDO,
                 anchor="w").pack(fill="x", pady=(2, 0))

        tk.Label(cabecera, text="por Ardamir", font=(self.f_texto, 9),
                 fg=APAGADO, bg=FONDO, anchor="ne").pack(side="right", anchor="n", pady=(8, 0))

    def _construir_accion(self):
        contenedor = tk.Frame(self.root, bg=FONDO)
        contenedor.pack(fill="x", pady=(14, 4))

        self.btn_pick = tk.Canvas(contenedor, width=ANCHO_ACCION, height=ALTO_ACCION,
                                  bg=FONDO, highlightthickness=0, bd=0,
                                  cursor="hand2")
        self.btn_pick.pack()
        self._dibujar_accion(False)

        self.btn_pick.bind("<Enter>", lambda e: self._dibujar_accion(True))
        self.btn_pick.bind("<Leave>", lambda e: self._dibujar_accion(False))
        self.btn_pick.bind("<Button-1>", lambda e: self._accion_click())

        self.hint = tk.Label(self.root, text=hint_text(), font=(self.f_texto, 9),
                             fg=APAGADO, bg=FONDO)
        self.hint.pack(pady=(0, 2))

        self.status = tk.Label(self.root, text="", font=(self.f_texto, 10),
                               fg=APAGADO, bg=FONDO, anchor="center")
        self.status.pack(fill="x", padx=28)

    def _construir_instrucciones(self):
        """Tarjeta «Cómo se usa», debajo del botón y siempre visible.

        Vive fuera del área de resultados a propósito: esa área scrollea, y las
        instrucciones tienen que verse sin scrollear. La jerarquía es menor que
        la del botón (panel oscuro, texto chico): explica, no compite.
        """
        self.tarjeta_instrucciones = tk.Frame(self.root, bg=PANEL)
        self.tarjeta_instrucciones.pack(fill="x", padx=28, pady=(8, 0))

        interior = tk.Frame(self.tarjeta_instrucciones, bg=PANEL)
        interior.pack(fill="x", padx=14, pady=(9, 10))

        tk.Label(interior, text=TEXTO_INSTRUCCIONES,
                 font=(self.f_texto, 9, "bold"), fg=APAGADO, bg=PANEL,
                 anchor="w").pack(fill="x", pady=(0, 3))

        self.pasos_uso = []
        for numero, paso in enumerate(PASOS_USO, start=1):
            fila = tk.Frame(interior, bg=PANEL)
            fila.pack(fill="x", pady=(1, 0))
            etiqueta_numero = tk.Label(fila, text="%d." % numero,
                                       font=(self.f_texto, 10, "bold"),
                                       fg=DORADO, bg=PANEL, anchor="w", width=2)
            etiqueta_numero.pack(side="left", anchor="n")
            etiqueta_texto = tk.Label(fila, text=paso, font=(self.f_texto, 10),
                                      fg=CREMA, bg=PANEL, anchor="w",
                                      justify="left")
            etiqueta_texto.pack(side="left", fill="x", expand=True)
            self.pasos_uso.append((etiqueta_numero, etiqueta_texto))

    def _dibujar_accion(self, hover):
        """Repinta el botón principal: relleno dorado, texto navy, hover más claro."""
        self.btn_pick.delete("all")
        activo = self._accion_activa
        relleno = DORADO_HOVER if (hover and activo) else DORADO
        if not activo:
            relleno = PANEL_ALTO
        _rectangulo_redondeado(self.btn_pick, 1, 1, ANCHO_ACCION - 1, ALTO_ACCION - 1, 14,
                               fill=relleno, outline="")
        self.btn_pick.create_text(
            ANCHO_ACCION / 2.0, ALTO_ACCION / 2.0,
            text=TEXTO_ACCION if activo else TEXTO_OCUPADO,
            font=(self.f_texto, 13, "bold"),
            fill=FONDO if activo else APAGADO)
        self.btn_pick.configure(cursor="hand2" if activo else "arrow")

    def _accion_click(self):
        if self._accion_activa:
            self.pick_and_convert()

    def _construir_resultados(self):
        self.cuerpo = tk.Frame(self.root, bg=FONDO)
        self.cuerpo.pack(fill="both", expand=True, padx=28, pady=(10, 6))

        self.canvas_resultados = tk.Canvas(self.cuerpo, bg=FONDO, highlightthickness=0, bd=0)
        self.canvas_resultados.pack(side="left", fill="both", expand=True)

        self.scroll = ttk.Scrollbar(self.cuerpo, orient="vertical",
                                    style=ESTILO_SCROLL, command=self.canvas_resultados.yview)
        self.canvas_resultados.configure(yscrollcommand=self._on_scroll)

        self.cards = tk.Frame(self.canvas_resultados, bg=FONDO)
        self._ventana_cards = self.canvas_resultados.create_window(
            (0, 0), window=self.cards, anchor="nw")

        self.cards.bind("<Configure>", self._on_cards_configure)
        self.canvas_resultados.bind("<Configure>", self._on_canvas_configure)
        # Un solo binding de rueda, filtrado por posición: en Tk los hijos "tapan"
        # el Enter/Leave del contenedor y la rueda se cortaría sobre las tarjetas.
        self.root.bind_all("<MouseWheel>", self._on_wheel)

    def _construir_pie(self):
        pie = tk.Frame(self.root, bg=FONDO)
        pie.pack(side="bottom", fill="x", padx=28, pady=(0, 18))

        self.detail_box = tk.Frame(pie, bg=PANEL, highlightbackground=PANEL_ALTO,
                                   highlightthickness=1)
        self.detail = tk.Text(self.detail_box, height=8, wrap="word",
                              font=(self.f_tecnica, 9), bg=PANEL, fg=APAGADO,
                              insertbackground=CREMA, relief="flat", borderwidth=0,
                              padx=12, pady=10, state="disabled", cursor="arrow")
        detail_scroll = ttk.Scrollbar(self.detail_box, orient="vertical",
                                      style=ESTILO_SCROLL, command=self.detail.yview)
        self.detail.configure(yscrollcommand=detail_scroll.set)
        self.detail.pack(side="left", fill="both", expand=True)
        detail_scroll.pack(side="right", fill="y")

        self.fila_pie = tk.Frame(pie, bg=FONDO)
        self.fila_pie.pack(fill="x")

        self.btn_open_dir = self._boton_pie(self.fila_pie, "Abrir la carpeta", self.open_folder)
        self.btn_open_dir.configure(state="disabled")
        self.btn_open_dir.pack(side="left")
        self._boton_pie(self.fila_pie, "Limpiar", self.clear).pack(side="left", padx=10)

        self.enlace = tk.Label(self.fila_pie, text=TEXTO_ENLACE_DETALLE,
                               font=(self.f_texto, 9), fg=DORADO, bg=FONDO,
                               cursor="hand2")
        self.enlace.pack(side="right")
        self.enlace.bind("<Button-1>", lambda e: self.toggle_detail())
        self.enlace.bind("<Enter>", lambda e: self.enlace.configure(fg=DORADO_HOVER,
                                                                   font=(self.f_texto, 9, "underline")))
        self.enlace.bind("<Leave>", lambda e: self.enlace.configure(fg=DORADO,
                                                                   font=(self.f_texto, 9)))

    def _boton_pie(self, padre, texto, accion):
        return tk.Button(padre, text=texto, command=accion, font=(self.f_texto, 10),
                         bg=PANEL, fg=CREMA, activebackground=PANEL_ALTO,
                         activeforeground=DORADO, disabledforeground=APAGADO,
                         relief="flat", bd=0, highlightthickness=0,
                         cursor="hand2", padx=14, pady=6)

    # ---------- helpers de UI ----------

    def _on_scroll(self, primero, ultimo):
        self.scroll.set(primero, ultimo)

    def _on_cards_configure(self, event=None):
        self.canvas_resultados.configure(scrollregion=self.canvas_resultados.bbox("all"))
        self._ajustar_barra()

    def _on_canvas_configure(self, event=None):
        self.canvas_resultados.itemconfigure(self._ventana_cards, width=event.width)
        if self._vacio:
            # Sin tarjetas el texto vacio se centra en toda el area disponible.
            self.canvas_resultados.itemconfigure(self._ventana_cards, height=event.height)
        self._ajustar_barra()

    def _ajustar_barra(self):
        """La barra de scroll solo aparece cuando hace falta."""
        try:
            alto_canvas = self.canvas_resultados.winfo_height()
            alto_cards = self.cards.winfo_reqheight()
        except Exception:
            return
        if alto_cards > alto_canvas:
            self.scroll.pack(side="right", fill="y")
        else:
            self.scroll.pack_forget()

    def _on_wheel(self, event):
        """Rueda del mouse: solo mueve los resultados si el puntero está ahí."""
        try:
            x, y = self.root.winfo_pointerxy()
            x0 = self.canvas_resultados.winfo_rootx()
            y0 = self.canvas_resultados.winfo_rooty()
            ancho = self.canvas_resultados.winfo_width()
            alto = self.canvas_resultados.winfo_height()
            if not (x0 <= x <= x0 + ancho and y0 <= y <= y0 + alto):
                return
            if self.cards.winfo_reqheight() <= alto:
                return
            self.canvas_resultados.yview_scroll(-1 * (event.delta // 120), "units")
        except Exception:
            pass

    def write_line(self, text, tag=None):
        """Agrega texto al detalle técnico (nunca a la superficie principal)."""
        self.detail.configure(state="normal")
        self.detail.insert("end", text + "\n", tag or ())
        self.detail.see("end")
        self.detail.configure(state="disabled")

    def set_status(self, text, color=None):
        self.status.configure(text=text, fg=color or APAGADO)

    def toggle_detail(self):
        """Muestra u oculta el detalle técnico. Oculto por defecto."""
        if self.detail_box.winfo_manager():
            self.detail_box.pack_forget()
            self.enlace.configure(text=TEXTO_ENLACE_DETALLE)
        else:
            self.detail_box.pack(fill="x", pady=(0, 10), before=self.fila_pie)
            self.enlace.configure(text=TEXTO_ENLACE_OCULTAR)

    def _poner_detalle(self, results):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.configure(state="disabled")
        texto = technical_detail(results)
        if texto.strip():
            for linea in texto.splitlines():
                self.write_line(linea)
            self.detail.see("1.0")

    def _borrar_tarjetas(self):
        for widget in self.cards.winfo_children():
            widget.destroy()
        self.canvas_vacio = None

    def _mostrar_instrucciones(self, visible):
        """Muestra u oculta la tarjeta «Cómo se usa».

        Con resultados en pantalla las instrucciones ya cumplieron su función y le
        roban alto a las tarjetas: se ocultan. Vuelven cuando la lista queda vacía.
        """
        if not hasattr(self, "tarjeta_instrucciones"):
            return
        if visible:
            if not self.tarjeta_instrucciones.winfo_manager():
                self.tarjeta_instrucciones.pack(fill="x", padx=28, pady=(8, 0),
                                                before=self.cuerpo)
        elif self.tarjeta_instrucciones.winfo_manager():
            self.tarjeta_instrucciones.pack_forget()

    def _render_empty_state(self):
        self._mostrar_instrucciones(True)
        self._borrar_tarjetas()
        self._vacio = True
        # La frase sola flotaba en el vacío: el marco punteado le da un lugar al
        # resultado que todavía no existe y marca el área donde van a aparecer.
        self.canvas_vacio = tk.Canvas(self.cards, bg=FONDO, highlightthickness=0, bd=0)
        self.canvas_vacio.pack(fill="both", expand=True)
        self.canvas_vacio.bind("<Configure>", self._dibujar_marco_vacio)
        self._dibujar_marco_vacio()
        try:
            alto = self.canvas_resultados.winfo_height()
            ancho = self.canvas_resultados.winfo_width()
            if alto > 1:
                self.canvas_resultados.itemconfigure(self._ventana_cards,
                                                     width=ancho, height=alto)
        except Exception:
            pass
        self.canvas_resultados.yview_moveto(0)

    def _dibujar_marco_vacio(self, event=None):
        """Rectángulo de borde punteado con la frase vacía centrada.

        Se redibuja en cada cambio de tamaño. Cuando hay tarjetas, el canvas se
        destruye con ellas: el borde no puede quedar detrás de los resultados.
        """
        lienzo = self.canvas_vacio
        if lienzo is None:
            return
        try:
            if not lienzo.winfo_exists():
                return
            ancho = event.width if event is not None else lienzo.winfo_width()
            alto = event.height if event is not None else lienzo.winfo_height()
            if ancho <= 12 or alto <= 12:
                return
            lienzo.delete("marco_vacio")
            margen = 6
            lienzo.create_rectangle(
                margen, margen, ancho - margen, alto - margen,
                outline=BORDE_PUNTEADO, width=1, dash=GUION_PUNTEADO,
                tags="marco_vacio")
            lienzo.create_text(
                ancho / 2.0, alto / 2.0, text=TEXTO_VACIO,
                font=(self.f_texto, 12), fill=APAGADO,
                width=max(120, ancho - 80), justify="center",
                tags="marco_vacio")
        except Exception:
            pass

    def _crear_tarjeta(self, result):
        """Una tarjeta por archivo: barra de estado, nombre, una línea humana y avisos.

        El estado se dice con una palabra al inicio de la segunda línea, además
        del color: la barra sola no sirve para quien no distingue colores.
        """
        estado, lineas = card_lines(result)
        color_texto = COLOR_ESTADO.get(estado, APAGADO)
        color_barra = COLOR_BARRA.get(estado, APAGADO)
        color_revisar = ERROR if result.get("error") else AVISO
        destino = result.get("target")
        cursor = "hand2" if destino else "arrow"

        tarjeta = tk.Frame(self.cards, bg=PANEL_ALTO, cursor=cursor,
                           highlightthickness=1, highlightbackground=PANEL_ALTO)
        if self._vacio:
            self._vacio = False
            self.canvas_resultados.itemconfigure(self._ventana_cards, height=0)
        tarjeta.pack(fill="x", padx=(2, 8), pady=(0, 10))

        barra = tk.Frame(tarjeta, bg=color_barra, width=5, cursor=cursor)
        barra.pack(side="left", fill="y")
        barra.pack_propagate(False)

        cuerpo = tk.Frame(tarjeta, bg=PANEL_ALTO, cursor=cursor)
        cuerpo.pack(side="left", fill="x", expand=True, padx=14, pady=10)

        widgets = [tarjeta, barra, cuerpo]
        nombre = tk.Label(cuerpo, text=os.path.basename(result.get("source") or "archivo.pdf"),
                          font=(self.f_texto, 11, "bold"), fg=CREMA, bg=PANEL_ALTO,
                          anchor="w", justify="left", cursor=cursor)
        nombre.pack(fill="x")
        widgets.append(nombre)

        for linea in lineas:
            if linea["estado"]:
                widgets.extend(self._linea_con_estado(
                    cuerpo, linea["texto"], cursor, estado, color_texto,
                    color_revisar if linea["clase"] == "revisar" else APAGADO))
            else:
                widgets.append(self._linea_simple(
                    cuerpo, linea["texto"], cursor,
                    color_revisar if linea["clase"] == "revisar" else APAGADO))

        if destino:
            for widget in widgets:
                widget.bind("<Button-1>", lambda e, ruta=destino: self.open_pdf_target(ruta))
                widget.bind("<Enter>", lambda e, t=tarjeta: t.configure(highlightbackground=DORADO))
                widget.bind("<Leave>", lambda e, t=tarjeta: t.configure(highlightbackground=PANEL_ALTO))

        return tarjeta

    def _linea_con_estado(self, padre, texto, cursor, estado, color_estado, color_texto):
        """Línea con la palabra del estado adelante, en su color, y el texto después."""
        linea = tk.Frame(padre, bg=PANEL_ALTO, cursor=cursor)
        linea.pack(fill="x", pady=(2, 0))
        widgets = [linea]
        palabra = ETIQUETA_ESTADO.get(estado)
        if palabra:
            etiqueta = tk.Label(linea, text=palabra + " ·",
                                font=(self.f_texto, 10, "bold"), fg=color_estado,
                                bg=PANEL_ALTO, anchor="w", cursor=cursor)
            etiqueta.pack(side="left")
            widgets.append(etiqueta)
        detalle = tk.Label(linea, text=texto, font=(self.f_texto, 10), fg=color_texto,
                           bg=PANEL_ALTO, anchor="w", justify="left",
                           cursor=cursor, wraplength=620)
        detalle.pack(side="left", fill="x", expand=True)
        widgets.append(detalle)
        return widgets

    def _linea_simple(self, padre, texto, cursor, color_texto):
        """Línea sin palabra de estado: resumen de otra página o aviso que sigue."""
        etiqueta = tk.Label(padre, text=texto, font=(self.f_texto, 10), fg=color_texto,
                            bg=PANEL_ALTO, anchor="w", justify="left",
                            cursor=cursor, wraplength=680)
        etiqueta.pack(fill="x", pady=(4, 0))
        return etiqueta

    # ---------- acciones ----------

    def clear(self):
        self._render_empty_state()
        self.results = []
        self._poner_detalle([])
        self.btn_open_dir.configure(state="disabled")
        self.set_status("Listo. Elegí otro PDF cuando quieras.", APAGADO)

    def pick_and_convert(self):
        if engine.fitz is None:
            messagebox.showerror(
                "Falta una librería",
                "No está instalada PyMuPDF.\n\nAbrí una consola y ejecutá:\n\n"
                "python -m pip install --user pymupdf")
            return

        paths = filedialog.askopenfilenames(
            title="Elegí el o los PDF de rótulos",
            initialdir=self.last_dir,
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos", "*.*")])
        if not paths:
            return

        self.last_dir = os.path.dirname(paths[0])
        self.results = []
        self._render_empty_state()
        self._accion_activa = False
        self._dibujar_accion(False)
        self.set_status("Convirtiendo…", DORADO)
        self.root.update_idletasks()

        try:
            results = convert_many(paths)
        except Exception:
            write_log("\n--- convert_many ---\n" + traceback.format_exc())
            messagebox.showerror("Error inesperado", traceback.format_exc(limit=3)[-900:])
            results = []
        finally:
            self._accion_activa = True
            self._dibujar_accion(False)

        self.show_results(results)

    def show_results(self, results):
        self.results = [r for r in results if r["target"]]

        self._borrar_tarjetas()
        for result in results:
            self._crear_tarjeta(result)
        if not results:
            self._render_empty_state()
            self.btn_open_dir.configure(state="disabled")
            self.set_status("No elegiste ningún PDF.", AVISO)
            return

        self._poner_detalle(results)
        self._mostrar_instrucciones(False)

        texto, color = summarize(results)
        self.set_status(texto, color)

        self.btn_open_dir.configure(state="normal" if self.results else "disabled")
        self.root.update_idletasks()
        self._on_cards_configure()
        self.canvas_resultados.yview_moveto(0)

    def open_pdf_target(self, path):
        try:
            os.startfile(path)
        except Exception:
            write_log("\n--- no se pudo abrir %s ---\n%s" % (path, traceback.format_exc()))
            messagebox.showerror(
                "No se pudo abrir el PDF",
                "Windows no pudo abrir el archivo. Está en la misma carpeta que el original:\n\n%s"
                % os.path.basename(path))

    def open_pdf(self):
        if self.results:
            self.open_pdf_target(self.results[0]["target"])

    def open_folder(self):
        if self.results:
            os.startfile(os.path.dirname(os.path.abspath(self.results[0]["target"])))


def _log_exception(exc_type, exc_value, exc_tb):
    """Deja el fallo en el log y avisa en pantalla, aunque no haya consola."""
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    guardado = write_log("\n=== error ===\n" + text)
    if guardado:
        donde = "Detalle guardado en %s" % log_path()
    else:
        donde = "No se pudo guardar el detalle en %s" % log_path()
    try:
        messagebox.showerror("Error inesperado",
                             "La app encontró un problema. %s:\n\n" % donde
                             + text[-800:])
    except Exception:
        pass


def main():
    sys.excepthook = _log_exception
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass
    app = App(root)
    if engine.fitz is None:
        app.set_status("Falta PyMuPDF: ejecutá  python -m pip install --user pymupdf", ERROR)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
