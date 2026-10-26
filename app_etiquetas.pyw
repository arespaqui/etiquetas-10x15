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
"""

import os
import sys
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

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
        return "No elegiste ningún PDF.", "#b35c00"
    errors = [r for r in results if r["error"]]
    converted = [r for r in results if not r["error"]]
    warned = [r for r in converted if r["warnings"]]
    if errors and not converted:
        return "No se pudo convertir ningún archivo. Mirá el detalle abajo.", "#b00020"
    if errors:
        return ("Convertidos %d, con %d error(es). Mirá el detalle abajo."
                % (len(converted), len(errors)), "#b35c00")
    if warned:
        return "Convertido. Ojo: el rótulo no es 10×15 (mirá el aviso naranja).", "#b35c00"
    return "Listo: %d rótulo(s) convertido(s) al tamaño exacto." % len(converted), "#0a7d32"


# ---------------------------------------------------------------- interfaz

class App:
    def __init__(self, root):
        self.root = root
        self.last_dir = os.path.expanduser("~")
        self.results = []

        root.title(APP_TITLE)
        root.minsize(740, 580)
        root.configure(padx=18, pady=14)

        header = tk.Frame(root)
        header.pack(fill="x")
        tk.Label(header, text="Convertir rótulo en etiqueta 10 × 15",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(header,
                 text="Elegí el PDF que te da Correo Argentino. La app lo recorta y lo deja "
                      "del tamaño exacto de tu etiqueta.",
                 font=("Segoe UI", 10), fg="#444", justify="left",
                 wraplength=670).pack(anchor="w", pady=(4, 0))

        self.btn_pick = tk.Button(root, text="Elegir PDF y convertir",
                                  font=("Segoe UI", 13, "bold"), bg="#0a7d32", fg="white",
                                  activebackground="#096b2b", activeforeground="white",
                                  relief="flat", cursor="hand2", pady=12,
                                  command=self.pick_and_convert)
        self.btn_pick.pack(fill="x", pady=(16, 12))

        self.status = tk.Label(root, text="Esperando un archivo…",
                               font=("Segoe UI", 11, "bold"), anchor="w", fg="#555")
        self.status.pack(fill="x")

        text_frame = tk.Frame(root)
        text_frame.pack(fill="both", expand=True, pady=(8, 10))

        self.log = tk.Text(text_frame, height=10, wrap="word", font=("Consolas", 9),
                           relief="solid", borderwidth=1, padx=10, pady=8,
                           background="#fbfbfb", state="disabled", cursor="arrow")
        scroll = tk.Scrollbar(text_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.log.tag_configure("title", font=("Consolas", 9, "bold"), foreground="#111")
        self.log.tag_configure("ok", foreground="#0a7d32")
        self.log.tag_configure("warn", foreground="#b35c00")

        actions = tk.Frame(root)
        actions.pack(fill="x")

        self.btn_open_pdf = tk.Button(actions, text="Abrir el PDF convertido",
                                      font=("Segoe UI", 10), state="disabled",
                                      command=self.open_pdf)
        self.btn_open_pdf.pack(side="left")

        self.btn_open_dir = tk.Button(actions, text="Abrir la carpeta",
                                      font=("Segoe UI", 10), state="disabled",
                                      command=self.open_folder)
        self.btn_open_dir.pack(side="left", padx=8)

        tk.Button(actions, text="Limpiar", font=("Segoe UI", 10),
                  command=self.clear).pack(side="right")

        recipe = tk.Frame(root, bg="#eef4fb", highlightbackground="#b9d3ee",
                          highlightthickness=1)
        recipe.pack(fill="x", pady=(12, 0))
        tk.Label(recipe, text="Para imprimir", font=("Segoe UI", 10, "bold"),
                 bg="#eef4fb", anchor="w").pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(recipe,
                 text="1) Abrí el PDF convertido.     2) Elegí tu impresora térmica.\n"
                      "3) Papel: la etiqueta de 100 x 150 mm.     4) Escala: Tamaño real.     5) Páginas: 1.",
                 font=("Segoe UI", 10), bg="#eef4fb", justify="left",
                 anchor="w").pack(fill="x", padx=12, pady=(2, 8))

        self.write_line("Todo listo. Tocá el botón verde para empezar.", "title")

    # ---------- helpers de UI ----------

    def write_line(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_status(self, text, color="#555"):
        self.status.configure(text=text, fg=color)

    def clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.results = []
        self.btn_open_pdf.configure(state="disabled")
        self.btn_open_dir.configure(state="disabled")
        self.set_status("Esperando un archivo…")

    # ---------- acciones ----------

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
        self.btn_open_pdf.configure(state="disabled")
        self.btn_open_dir.configure(state="disabled")
        self.btn_pick.configure(state="disabled", text="Convirtiendo…")
        self.set_status("Convirtiendo…", "#0a5cb8")
        self.root.update_idletasks()

        try:
            results = convert_many(paths)
        except Exception:
            write_log("\n--- convert_many ---\n" + traceback.format_exc())
            messagebox.showerror("Error inesperado", traceback.format_exc(limit=3)[-900:])
            results = []
        finally:
            self.btn_pick.configure(state="normal", text="Elegir PDF y convertir")

        self.show_results(results)

    def show_results(self, results):
        self.results = [r for r in results if r["target"]]

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        for result in results:
            name = os.path.basename(result["source"])
            if result["error"]:
                self.write_line("X %s" % name, "warn")
                self.write_line("   no se pudo convertir: %s" % result["error"], "warn")
                continue
            self.write_line("OK  %s  ->  %s"
                            % (name, os.path.basename(result["target"])), "title")
            for row in result["rows"]:
                self.write_line("   página %d: origen %s  →  %s  (escala %.0f %%)"
                                % (row["page"], row["source"], row["printed"],
                                   row["scale"]), "ok")
            for row in result["rows"]:
                if row.get("trimmed_mm", 0) > 0:
                    self.write_line("   recorté %.0f mm de blanco del final: el rótulo entra más grande"
                                    % row["trimmed_mm"], "ok")
                note = human_note(row)
                if note:
                    self.write_line("   ! %s" % note, "warn")
            self.write_line("")

        text, colour = summarize(results)
        self.set_status(text, colour)

        if self.results:
            self.btn_open_pdf.configure(state="normal")
            self.btn_open_dir.configure(state="normal")

    def open_pdf(self):
        if self.results:
            os.startfile(self.results[0]["target"])

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
        app.set_status("Falta PyMuPDF: ejecutá  python -m pip install --user pymupdf", "#b00020")
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
