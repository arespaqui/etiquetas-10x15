"""Pruebas de la ventana pública (T7): texto humano en la superficie, detalle aparte.

Dos defensas concretas:

1. La superficie principal no muestra jerga («origen», «impreso», «proporción»,
   «deformación»): eso vive en el detalle técnico, que arranca oculto.
2. La ventana se puede construir sin abrirla de forma interactiva: se crea
   `tk.Tk()`, se instancia `App`, se llama `update_idletasks()` y se destruye.
   Si el entorno no tiene display, la prueba se saltea y lo dice.

Las pruebas de widgets no tocan `errores.log`: no convierten archivos.
"""

import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from unittest import mock

from tests import ROOT

APP_PATH = os.path.join(ROOT, "app_etiquetas.pyw")
NOMBRE_MODULO = "app_etiquetas_ventana_publica"

# Palabras que sólo pueden aparecer en el detalle técnico.
JERGA = ("origen", "impreso", "proporción", "deformación")


def cargar_app():
    """Importa el .pyw como módulo, sin ejecutar main() ni crear ventanas."""
    loader = importlib.machinery.SourceFileLoader(NOMBRE_MODULO, APP_PATH)
    spec = importlib.util.spec_from_loader(NOMBRE_MODULO, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


def fila(frame_found=True, mismatch=0.0, margin_x=0.0, trimmed_mm=0.0,
         printed="100.0 x 150.0 mm", scale=100.0, page=1):
    return {
        "page": page,
        "frame_found": frame_found,
        "trimmed_mm": trimmed_mm,
        "source": "86.0 x 163.0 mm",
        "printed": printed,
        "scale": scale,
        "margin_x": margin_x,
        "margin_y": 0.0,
        "aspect": 0.66,
        "mismatch": mismatch,
    }


def resultado(rows=None, warnings=None, error=None):
    return {
        "source": "/tmp/rotulo.pdf",
        "target": None if error else "/tmp/rotulo_10x15.pdf",
        "rows": rows or [],
        "warnings": warnings or [],
        "error": error,
    }


class TextoHumanoTest(unittest.TestCase):
    """La superficie habla en castellano común; el detalle guarda la jerga."""

    @classmethod
    def setUpClass(cls):
        cls.app = cargar_app()

    def test_la_linea_de_la_tarjeta_describe_medida_escala_y_blanco(self):
        texto = self.app.row_summary_line(
            fila(mismatch=0.05, margin_x=5.0, scale=105.0))

        self.assertIn("100 × 150 mm", texto)
        self.assertIn("escala 105 %", texto)
        self.assertIn("5 mm de blanco a cada lado", texto)

    def test_un_rotulo_exacto_no_habla_de_blanco(self):
        texto = self.app.row_summary_line(fila(margin_x=0.4, scale=100.0))

        self.assertNotIn("blanco", texto, texto)
        self.assertIn("escala 100 %", texto)

    def test_los_avisos_de_la_tarjeta_no_usan_jerga(self):
        casos = [
            resultado(rows=[fila(frame_found=False)]),
            resultado(rows=[fila(mismatch=0.2, margin_x=12.0)]),
            resultado(rows=[fila(trimmed_mm=9.0)]),
            resultado(error="algo salió mal"),
        ]
        for caso in casos:
            for linea in (self.app.result_warning_lines(caso)
                          + self.app.result_info_lines(caso)):
                for palabra in JERGA:
                    self.assertNotIn(
                        palabra, linea.lower(),
                        "la tarjeta usa jerga (%r): %r" % (palabra, linea))

    def test_los_textos_fijos_de_la_superficie_no_usan_jerga(self):
        for texto in (self.app.TEXTO_VACIO, self.app.PISTA_SOLTAR,
                      self.app.PISTA_SELECCION, self.app.TEXTO_ACCION,
                      self.app.TEXTO_ENLACE_DETALLE):
            for palabra in JERGA:
                self.assertNotIn(palabra, texto.lower(), texto)

    def test_el_aviso_de_rotulo_que_no_es_10x15_se_entiende(self):
        lineas = self.app.result_warning_lines(
            resultado(rows=[fila(mismatch=0.2, margin_x=12.0)]))

        self.assertEqual(1, len(lineas), lineas)
        self.assertIn("10 × 15", lineas[0])
        self.assertTrue(
            any("blanco" in linea for linea in lineas),
            "el aviso no explica que sobra blanco: %r" % (lineas,))

    def test_la_barra_de_estado_distingue_listo_aviso_y_error(self):
        self.assertEqual("ok", self.app.card_status(resultado(rows=[fila()])))
        self.assertEqual(
            "aviso", self.app.card_status(resultado(rows=[fila(frame_found=False)])))
        self.assertEqual(
            "error", self.app.card_status(resultado(error="no era un PDF")))

    def test_el_detalle_tecnico_si_conserva_la_jerga(self):
        detalle = self.app.technical_detail([
            resultado(rows=[fila(mismatch=0.2, margin_x=12.0)])])

        self.assertIn("origen", detalle.lower())
        self.assertIn("escala", detalle.lower())

    def test_el_logo_se_resuelve_desde_el_propio_script(self):
        ruta = self.app.default_logo_path()

        self.assertTrue(os.path.isabs(ruta), ruta)
        self.assertTrue(
            ruta.endswith(os.path.join("docs", "marca", "marca.png")), ruta)


class InstruccionesDeUsoTest(unittest.TestCase):
    """La ventana explica cómo se usa, sin depender de la documentación."""

    @classmethod
    def setUpClass(cls):
        cls.app = cargar_app()

    def test_hay_tres_pasos_numerados_con_lo_indispensable(self):
        pasos = self.app.PASOS_USO

        self.assertEqual(3, len(pasos), pasos)
        self.assertIn("PDF", pasos[0])
        self.assertIn("archivo nuevo", pasos[1])
        self.assertIn("original", pasos[1])
        self.assertIn("100 × 150 mm", pasos[2])
        self.assertIn("Tamaño real", pasos[2])

    def test_las_instrucciones_no_usan_jerga(self):
        textos = (self.app.TEXTO_INSTRUCCIONES,) + tuple(self.app.PASOS_USO)
        for texto in textos:
            for palabra in JERGA:
                self.assertNotIn(palabra, texto.lower(), texto)

    def test_el_marco_del_estado_vacio_es_un_gris_apagado(self):
        self.assertEqual("#3A4E5C", self.app.BORDE_PUNTEADO)
        self.assertNotEqual(self.app.DORADO, self.app.BORDE_PUNTEADO)


class EstadoSinSoloColorTest(unittest.TestCase):
    """El estado se lee con una palabra, no sólo con el color de la barra."""

    @classmethod
    def setUpClass(cls):
        cls.app = cargar_app()

    def test_cada_estado_tiene_su_palabra_y_su_color(self):
        self.assertEqual(
            {"ok": "Listo", "aviso": "Revisá", "error": "Error"},
            dict(self.app.ETIQUETA_ESTADO))
        for estado in ("ok", "aviso", "error"):
            self.assertIn(estado, self.app.COLOR_ESTADO)
            self.assertIn(estado, self.app.COLOR_BARRA)

    def test_una_tarjeta_limpia_muestra_una_sola_linea_corta(self):
        estado, lineas = self.app.card_lines(resultado(rows=[fila()]))

        self.assertEqual("ok", estado)
        self.assertEqual(1, len(lineas), lineas)
        self.assertTrue(lineas[0]["estado"],
                        "la línea no estrena la palabra del estado: %r" % (lineas,))
        leido = self.app.ETIQUETA_ESTADO[estado] + " · " + lineas[0]["texto"]
        self.assertEqual("Listo · 100 × 150 mm · escala 100 %", leido)

    def test_el_aviso_y_el_error_tambien_empiezan_con_su_palabra(self):
        estado, lineas = self.app.card_lines(
            resultado(rows=[fila(frame_found=False)]))
        self.assertEqual("aviso", estado)
        self.assertTrue(lineas[0]["estado"], lineas)
        self.assertTrue(any(linea["clase"] == "revisar" for linea in lineas), lineas)

        estado, lineas = self.app.card_lines(resultado(error="no era un PDF"))
        self.assertEqual("error", estado)
        self.assertEqual(1, len(lineas), lineas)
        self.assertTrue(lineas[0]["estado"], lineas)
        self.assertEqual("revisar", lineas[0]["clase"])

    def test_el_recorte_es_informacion_neutra_y_no_un_aviso(self):
        caso = resultado(rows=[fila(trimmed_mm=9.0)])

        self.assertEqual([], self.app.result_warning_lines(caso))
        self.assertEqual("ok", self.app.card_status(caso))
        infos = self.app.result_info_lines(caso)
        self.assertEqual(1, len(infos), infos)
        self.assertIn("recorté", infos[0].lower())
        _, lineas = self.app.card_lines(caso)
        self.assertEqual("info", lineas[-1]["clase"])

    def test_el_recorte_y_un_aviso_real_conviven_sin_taparse(self):
        caso = resultado(rows=[fila(trimmed_mm=9.0), fila(frame_found=False, page=2)])

        estado, lineas = self.app.card_lines(caso)
        self.assertEqual("aviso", estado)
        self.assertEqual(
            1, len([linea for linea in lineas if linea["estado"]]),
            "la palabra del estado aparece más de una vez: %r" % (lineas,))
        clases = [linea["clase"] for linea in lineas]
        self.assertIn("info", clases, lineas)
        self.assertIn("revisar", clases, lineas)
        info = [linea for linea in lineas if linea["clase"] == "info"][0]
        self.assertTrue(info["texto"].startswith("Página 1: "), info["texto"])

    def test_el_ambar_de_texto_es_mas_claro_que_el_de_la_barra(self):
        self.assertEqual("#E5AC63", self.app.AVISO)
        self.assertEqual("#D98E32", self.app.AVISO_BARRA)
        self.assertEqual("#9AAAB8", self.app.APAGADO)
        self.assertEqual(self.app.AVISO, self.app.COLOR_ESTADO["aviso"])
        self.assertEqual(self.app.AVISO_BARRA, self.app.COLOR_BARRA["aviso"])


class PistaCondicionalTest(unittest.TestCase):
    """La pista de arrastre no promete un .bat que puede no existir."""

    @classmethod
    def setUpClass(cls):
        cls.app = cargar_app()

    def test_desde_el_codigo_fuente_la_pista_de_arrastre_aparece(self):
        self.assertEqual(self.app.PISTA_SOLTAR, self.app.hint_text())

    def test_sin_el_bat_al_lado_la_pista_no_habla_de_arrastrar(self):
        if getattr(self.app.sys, "frozen", False):
            self.skipTest("corriendo empaquetada: no hay carpeta de código fuente")
        original = self.app._HERE
        with tempfile.TemporaryDirectory() as tmp:
            self.app._HERE = tmp
            try:
                pista = self.app.hint_text()
                self.assertEqual(self.app.PISTA_SELECCION, pista)
                self.assertNotIn("arrastrar", pista.lower(), pista)

                with open(os.path.join(tmp, "2 - Arrastrar PDF (alternativa).bat"),
                          "w", encoding="utf-8"):
                    pass
                self.assertEqual(self.app.PISTA_SOLTAR, self.app.hint_text())
            finally:
                self.app._HERE = original

    def test_empaquetada_mira_solo_la_carpeta_del_ejecutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "Etiquetas 10x15.exe")
            with mock.patch.object(self.app.sys, "frozen", True, create=True), \
                    mock.patch.object(self.app.sys, "executable", exe):
                self.assertEqual(self.app.PISTA_SELECCION, self.app.hint_text())

                with open(os.path.join(tmp, "2 - Arrastrar PDF (alternativa).bat"),
                          "w", encoding="utf-8"):
                    pass
                self.assertEqual(self.app.PISTA_SOLTAR, self.app.hint_text())


class VentanaSeConstruyeTest(unittest.TestCase):
    """La ventana se arma sin interacción: si esto explota, la app no abre."""

    @classmethod
    def setUpClass(cls):
        cls.app = cargar_app()

    def setUp(self):
        tk = self.app.tk
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest("el entorno no tiene display para Tk: %s" % exc)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_la_ventana_se_construye_y_cierra(self):
        ventana = self.app.App(self.root)
        self.root.update_idletasks()

        self.assertIn(self.app.APP_TITLE, self.root.title())
        self.assertIsInstance(ventana, self.app.App)
        self.assertTrue(ventana.cards.winfo_exists(), "no creó el área de tarjetas")
        self.assertEqual(
            "", ventana.detail_box.winfo_manager(),
            "el detalle técnico arrancó visible en la superficie principal")

    def _textos(self, widget, acumulado):
        if isinstance(widget, self.app.tk.Label):
            acumulado.append((widget.cget("text"), widget.cget("fg")))
        for hijo in widget.winfo_children():
            self._textos(hijo, acumulado)

    def test_la_tarjeta_muestra_la_palabra_del_estado(self):
        ventana = self.app.App(self.root)
        ventana.show_results([resultado(rows=[fila()])])
        self.root.update_idletasks()

        textos = []
        self._textos(ventana.cards, textos)
        leidos = [texto for texto, _ in textos]
        self.assertIn("Listo ·", leidos, leidos)
        self.assertTrue(any(texto.startswith("100 × 150 mm") for texto in leidos),
                        leidos)

    def test_el_recorte_no_pinta_barra_de_aviso(self):
        ventana = self.app.App(self.root)
        ventana.show_results([resultado(rows=[fila(trimmed_mm=9.0)])])
        self.root.update_idletasks()

        tarjeta = ventana.cards.winfo_children()[0]
        barra = tarjeta.winfo_children()[0]
        self.assertEqual(self.app.DORADO, barra.cget("bg"),
                         "la barra lateral sigue en ámbar para un recorte")

        textos = []
        self._textos(tarjeta, textos)
        recorte = "Recorté el aire que sobraba abajo para que el rótulo entre más grande."
        colores = dict(textos)
        self.assertIn(recorte, colores, textos)
        self.assertEqual(self.app.APAGADO, colores[recorte],
                         "el recorte no está en gris apagado")

    def test_los_tres_pasos_se_ven_sin_scrollear(self):
        ventana = self.app.App(self.root)
        self.root.update_idletasks()

        tarjeta = ventana.tarjeta_instrucciones
        self.assertTrue(tarjeta.winfo_manager(), "la tarjeta de uso no está visible")

        textos = []
        self._textos(tarjeta, textos)
        leidos = [texto for texto, _ in textos]
        colores = dict(textos)
        self.assertIn(self.app.TEXTO_INSTRUCCIONES, leidos, leidos)
        for numero, paso in zip(("1.", "2.", "3."), self.app.PASOS_USO):
            self.assertIn(numero, leidos, leidos)
            self.assertIn(paso, leidos, leidos)
            self.assertEqual(self.app.DORADO, colores[numero],
                             "el número del paso no está en dorado")
            self.assertEqual(self.app.CREMA, colores[paso],
                             "el texto del paso no está en crema")

    def _marco_punteado(self, canvas):
        for item in canvas.find_all():
            if canvas.type(item) != "rectangle":
                continue
            dash = canvas.itemcget(item, "dash")
            if dash.strip():
                return item, dash, canvas.itemcget(item, "outline")
        return None, None, None

    def test_el_estado_vacio_encierra_la_frase_con_borde_punteado(self):
        ventana = self.app.App(self.root)
        self.root.update_idletasks()

        canvas = ventana.canvas_vacio
        self.assertIsNotNone(canvas, "no hay canvas para el estado vacío")
        item, dash, outline = self._marco_punteado(canvas)
        self.assertIsNotNone(item, "el estado vacío no tiene borde punteado")
        self.assertEqual(self.app.BORDE_PUNTEADO.lower(), outline.lower())

        frases = [canvas.itemcget(i, "text") for i in canvas.find_all()
                  if canvas.type(i) == "text"]
        self.assertIn(self.app.TEXTO_VACIO, frases, frases)

    def test_el_marco_se_redibuja_al_cambiar_de_tamano(self):
        ventana = self.app.App(self.root)
        self.root.update_idletasks()

        canvas = ventana.canvas_vacio
        ventana._dibujar_marco_vacio(mock.Mock(width=500, height=300))

        marcos = [i for i in canvas.find_all() if canvas.type(i) == "rectangle"]
        self.assertEqual(1, len(marcos), "el marco se duplicó al redibujar")
        x1, y1, x2, y2 = canvas.coords(marcos[0])
        self.assertTrue(x2 > x1 and y2 > y1, (x1, y1, x2, y2))
        centro = [canvas.coords(i) for i in canvas.find_all()
                  if canvas.type(i) == "text"][0]
        self.assertAlmostEqual(250.0, centro[0], places=1)
        self.assertAlmostEqual(150.0, centro[1], places=1)

    def test_con_tarjetas_el_borde_punteado_desaparece(self):
        ventana = self.app.App(self.root)
        ventana.show_results([resultado(rows=[fila()])])
        self.root.update_idletasks()

        self.assertIsNone(ventana.canvas_vacio,
                          "el estado vacío siguió vivo con tarjetas")
        restos = [w for w in ventana.cards.winfo_children()
                  if isinstance(w, self.app.tk.Canvas)]
        self.assertEqual([], restos, "quedó un canvas vacío dibujado")

    def test_sin_logo_la_ventana_igual_se_construye(self):
        ventana = self.app.App(
            self.root, logo_path=os.path.join(ROOT, "no existe marca.png"))
        self.root.update_idletasks()

        self.assertIsNone(ventana.logo_image, "cargó una imagen de un archivo inexistente")
        self.assertIn(self.app.APP_TITLE, self.root.title())


if __name__ == "__main__":
    unittest.main()
