"""Pruebas del recorte conservador de espacio muerto (S5) con fixtures sintéticos (S4).

Cada PDF se genera durante la prueba, en un directorio temporal. No hay fixtures
versionados, ni datos de personas, ni red.
"""

import contextlib
import hashlib
import io
import os
import tempfile
import unittest

import pymupdf as fitz

import etiqueta_10x15 as etiqueta
from tests import soporte

# El marco de prueba mide el alto exacto de la etiqueta: 86 x 163 mm.
FRAME_W_MM = 86.0
FRAME_H_MM = 163.0


def hash_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ContenidoFueraDelAreaCalculadaTest(unittest.TestCase):
    """S5: si hay contenido (imágenes incluidas) fuera del área calculada, no recorta y avisa."""

    def test_imagen_en_el_espacio_muerto_no_se_recorta(self):
        """Una imagen al pie del marco no puede desaparecer con el recorte."""
        with tempfile.TemporaryDirectory() as carpeta:
            origen = os.path.join(carpeta, "rotulo con imagen.pdf")
            doc, page = soporte.blank_page()
            # marco de 86 x 163 mm: el alto exacto de la etiqueta, con el aire al final
            soporte.add_frame(page, x_mm=20, y_mm=20, w_mm=FRAME_W_MM, h_mm=FRAME_H_MM)
            soporte.add_text_lines(page, x_mm=24, first_baseline_mm=32, count=2, step_mm=9)
            # imagen raster chica en la zona muerta: el marco termina en y = 183 mm
            soporte.add_dark_image(page, x_mm=30, y_mm=163, w_mm=20, h_mm=15)
            soporte.save(doc, origen)
            destino = os.path.join(carpeta, "rotulo con imagen_10x15.pdf")

            rows, warnings = etiqueta.convert(origen, destino)

            self.assertTrue(rows[0]["frame_found"], "no se detectó el marco del rótulo")
            self.assertEqual(
                0.0,
                rows[0]["trimmed_mm"],
                "recortó espacio muerto con una imagen adentro: la imagen se pierde",
            )
            self.assertTrue(
                any("no se recorta" in aviso for aviso in warnings),
                "no avisó que no recorta: %r" % (warnings,),
            )

            salida = fitz.open(destino)
            try:
                self.assertEqual(1, salida.page_count)
                ancho_mm, alto_mm = soporte.page_size_mm(salida[0])
                self.assertAlmostEqual(100.0, ancho_mm, delta=0.2)
                self.assertAlmostEqual(150.0, alto_mm, delta=0.2)

                tinta = soporte.ink_box_mm(salida[0])
                self.assertIsNotNone(tinta, "la etiqueta salió en blanco")
                self.assertGreaterEqual(
                    tinta.y1,
                    128.0,
                    "la imagen del pie del marco no llegó a la etiqueta (tinta hasta %.1f mm)"
                    % tinta.y1,
                )
                self.assertLessEqual(
                    tinta.y1, 149.8, "la tinta se sale de la etiqueta: %.1f mm" % tinta.y1
                )
            finally:
                salida.close()


class RecorteSinImagenesTest(unittest.TestCase):
    """S5: cuando no hay contenido escondido, el aire del final se recorta de verdad."""

    def test_recorta_el_espacio_muerto_de_una_etiqueta_solo_de_texto(self):
        """Con ~20 mm de aire al final: recorta, deja 100 x 150 mm y no corta ninguna línea."""
        with tempfile.TemporaryDirectory() as carpeta:
            origen = os.path.join(carpeta, "rotulo solo texto.pdf")
            doc, page = soporte.blank_page()
            soporte.add_frame(page, x_mm=20, y_mm=20, w_mm=FRAME_W_MM, h_mm=FRAME_H_MM)
            # 15 líneas: la última termina cerca de 159 mm, o sea ~24 mm antes del marco
            baselines = soporte.add_text_lines(page, x_mm=24, first_baseline_mm=32, count=15, step_mm=9)
            soporte.save(doc, origen)
            destino = os.path.join(carpeta, "rotulo solo texto_10x15.pdf")

            rows, warnings = etiqueta.convert(origen, destino)

            self.assertTrue(rows[0]["frame_found"], "no se detectó el marco del rótulo")
            self.assertGreaterEqual(
                rows[0]["trimmed_mm"],
                15.0,
                "no recortó el espacio muerto de una etiqueta sin imágenes",
            )
            self.assertLessEqual(rows[0]["trimmed_mm"], 27.0, "recortó de más")
            self.assertFalse(
                any("no se recorta" in aviso for aviso in warnings),
                "avisó que no recorta cuando no había nada escondido: %r" % (warnings,),
            )

            salida = fitz.open(destino)
            try:
                ancho_mm, alto_mm = soporte.page_size_mm(salida[0])
                self.assertAlmostEqual(100.0, ancho_mm, delta=0.2)
                self.assertAlmostEqual(150.0, alto_mm, delta=0.2)

                tinta = soporte.ink_box_mm(salida[0])
                self.assertIsNotNone(tinta, "la etiqueta salió en blanco")
                # la tinta llena el alto, sin tocar los bordes: el contenido quedó completo
                self.assertGreaterEqual(
                    tinta.y1, 140.0, "el contenido no llenó el alto de la etiqueta"
                )
                self.assertLessEqual(tinta.y1, 149.8, "el contenido se sale de la etiqueta")
                self.assertGreater(tinta.x0, 0.5, "el contenido se cortó a la izquierda")
                self.assertLess(tinta.x1, 99.5, "el contenido se cortó a la derecha")

                franjas = soporte.ink_bands_mm(salida[0])
                self.assertEqual(
                    len(baselines),
                    len(franjas),
                    "se perdió alguna línea: %d de %d franjas de tinta"
                    % (len(franjas), len(baselines)),
                )
            finally:
                salida.close()


class EtiquetaYaEnDiezPorQuinceTest(unittest.TestCase):
    """S5: una etiqueta que ya mide 100 x 150 mm pasa sin recorte y sin romperse."""

    def test_pdf_que_ya_es_100x150_no_se_recorta_ni_falla(self):
        with tempfile.TemporaryDirectory() as carpeta:
            origen = os.path.join(carpeta, "rotulo ya 10x15.pdf")
            doc, page = soporte.blank_page(width_mm=100.0, height_mm=150.0)
            baselines = soporte.add_text_lines(page, x_mm=15, first_baseline_mm=20, count=10, step_mm=12)
            soporte.save(doc, origen)
            destino = os.path.join(carpeta, "rotulo ya 10x15_10x15.pdf")

            rows, warnings = etiqueta.convert(origen, destino)

            self.assertEqual(1, len(rows))
            self.assertEqual(0.0, rows[0]["trimmed_mm"], "recortó una etiqueta que ya era 10x15")

            salida = fitz.open(destino)
            try:
                self.assertEqual(1, salida.page_count)
                ancho_mm, alto_mm = soporte.page_size_mm(salida[0])
                self.assertAlmostEqual(100.0, ancho_mm, delta=0.2)
                self.assertAlmostEqual(150.0, alto_mm, delta=0.2)

                tinta = soporte.ink_box_mm(salida[0])
                self.assertIsNotNone(tinta, "la etiqueta salió en blanco")
                self.assertGreater(tinta.x0, 0.5, "el contenido se cortó a la izquierda")
                self.assertLess(tinta.x1, 99.5, "el contenido se cortó a la derecha")
                self.assertLessEqual(tinta.y1, 149.8, "el contenido se sale de la etiqueta")

                franjas = soporte.ink_bands_mm(salida[0])
                self.assertEqual(
                    len(baselines),
                    len(franjas),
                    "se perdió alguna línea: %d de %d franjas de tinta"
                    % (len(franjas), len(baselines)),
                )
            finally:
                salida.close()


class ArchivoOriginalIntactoTest(unittest.TestCase):
    """S5: el original no se toca y el resultado queda al lado con el sufijo _10x15."""

    def test_no_modifica_el_original_y_escribe_al_lado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            origen = os.path.join(carpeta, "rotulo de prueba.pdf")
            doc, page = soporte.blank_page()
            soporte.add_frame(page, x_mm=20, y_mm=20, w_mm=FRAME_W_MM, h_mm=FRAME_H_MM)
            soporte.add_text_lines(page, x_mm=24, first_baseline_mm=32, count=4, step_mm=9)
            soporte.save(doc, origen)

            antes = os.stat(origen)
            hash_antes = hash_of(origen)

            salida_texto = io.StringIO()
            with contextlib.redirect_stdout(salida_texto):
                codigo = etiqueta.main(["etiqueta_10x15.py", origen])

            self.assertEqual(0, codigo, "la conversión falló:\n%s" % salida_texto.getvalue())

            esperado = os.path.join(carpeta, "rotulo de prueba_10x15.pdf")
            self.assertTrue(os.path.isfile(esperado), "no creó <nombre>_10x15.pdf al lado")
            self.assertEqual(
                {"rotulo de prueba.pdf", "rotulo de prueba_10x15.pdf"},
                {nombre for nombre in os.listdir(carpeta) if nombre.lower().endswith(".pdf")},
                "el resultado no quedó junto al original o se escribió de más",
            )

            despues = os.stat(origen)
            self.assertEqual(hash_antes, hash_of(origen), "el PDF original cambió de contenido")
            self.assertEqual(antes.st_size, despues.st_size, "el PDF original cambió de tamaño")
            self.assertEqual(
                antes.st_mtime_ns, despues.st_mtime_ns, "el PDF original cambió de fecha"
            )

            convertido = fitz.open(esperado)
            try:
                ancho_mm, alto_mm = soporte.page_size_mm(convertido[0])
                self.assertAlmostEqual(100.0, ancho_mm, delta=0.2)
                self.assertAlmostEqual(150.0, alto_mm, delta=0.2)
            finally:
                convertido.close()


class SinMarcoDetectableTest(unittest.TestCase):
    """S5: sin marco detectable la función lo informa en vez de entregar un rótulo mal recortado."""

    def test_sin_marco_avisa_en_vez_de_recortar_en_silencio(self):
        with tempfile.TemporaryDirectory() as carpeta:
            origen = os.path.join(carpeta, "rotulo sin marco.pdf")
            doc, page = soporte.blank_page()
            # sin rectángulo contorneado: no hay marco que detectar
            soporte.add_text_lines(page, x_mm=40, first_baseline_mm=60, count=6, step_mm=10)
            soporte.save(doc, origen)
            destino = os.path.join(carpeta, "rotulo sin marco_10x15.pdf")

            rows, warnings = etiqueta.convert(origen, destino)

            self.assertFalse(
                rows[0]["frame_found"], "dijo que encontró un marco que no existe"
            )
            self.assertTrue(warnings, "no avisó nada sobre el marco faltante")
            self.assertTrue(
                any("marco" in aviso for aviso in warnings),
                "el aviso no explica que falta el marco: %r" % (warnings,),
            )

            salida = fitz.open(destino)
            try:
                ancho_mm, alto_mm = soporte.page_size_mm(salida[0])
                self.assertAlmostEqual(100.0, ancho_mm, delta=0.2)
                self.assertAlmostEqual(150.0, alto_mm, delta=0.2)
                self.assertIsNotNone(soporte.ink_box_mm(salida[0]), "la etiqueta salió en blanco")
            finally:
                salida.close()


class DibujoAnchoFueraDelAreaTest(unittest.TestCase):
    """S5 (triangulación): un dibujo ancho debajo del texto tampoco se recorta."""

    def test_dibujo_ancho_debajo_del_texto_frena_el_recorte(self):
        with tempfile.TemporaryDirectory() as carpeta:
            origen = os.path.join(carpeta, "rotulo con linea ancha.pdf")
            doc, page = soporte.blank_page()
            soporte.add_frame(page, x_mm=20, y_mm=20, w_mm=FRAME_W_MM, h_mm=FRAME_H_MM)
            soporte.add_text_lines(page, x_mm=24, first_baseline_mm=32, count=2, step_mm=9)
            # línea de 80 mm de ancho (más del 90% del marco) lejos de los bordes
            soporte.add_wide_rule(page, x_mm=23, y_mm=168, w_mm=80.0)
            soporte.save(doc, origen)
            destino = os.path.join(carpeta, "rotulo con linea ancha_10x15.pdf")

            rows, warnings = etiqueta.convert(origen, destino)

            self.assertEqual(
                0.0,
                rows[0]["trimmed_mm"],
                "recortó una línea ancha que estaba debajo del texto",
            )
            self.assertTrue(
                any("no se recorta" in aviso for aviso in warnings),
                "no avisó que no recorta por el dibujo ancho: %r" % (warnings,),
            )


class ImagenDentroDelAreaTest(unittest.TestCase):
    """S5 (triangulación): una imagen dentro del área calculada no frena el recorte útil."""

    def test_imagen_dentro_del_area_no_impide_el_recorte(self):
        with tempfile.TemporaryDirectory() as carpeta:
            origen = os.path.join(carpeta, "rotulo con imagen arriba.pdf")
            doc, page = soporte.blank_page()
            soporte.add_frame(page, x_mm=20, y_mm=20, w_mm=FRAME_W_MM, h_mm=FRAME_H_MM)
            soporte.add_text_lines(page, x_mm=24, first_baseline_mm=32, count=15, step_mm=9)
            # imagen entre las líneas: no hay nada escondido debajo del texto
            soporte.add_dark_image(page, x_mm=74, y_mm=100, w_mm=12, h_mm=12)
            soporte.save(doc, origen)
            destino = os.path.join(carpeta, "rotulo con imagen arriba_10x15.pdf")

            rows, warnings = etiqueta.convert(origen, destino)

            self.assertGreaterEqual(
                rows[0]["trimmed_mm"],
                15.0,
                "una imagen dentro del área calculada frenó un recorte que era seguro",
            )
            self.assertFalse(
                any("no se recorta" in aviso for aviso in warnings),
                "avisó de un contenido escondido que no existe: %r" % (warnings,),
            )


if __name__ == "__main__":
    unittest.main()
