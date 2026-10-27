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


class ImagenEnLaZonaBajaTest(unittest.TestCase):
    """S5: la imagen del pie del rótulo cuenta como contenido y sobrevive al recorte.

    El requisito es que la imagen se imprima, no que se deje de recortar: la
    salida con imagen queda más chica que la salida sin imagen, y eso es correcto.
    """

    def test_la_imagen_de_la_zona_baja_sobrevive_al_recorte(self):
        """La imagen del pie se imprime completa y el corte nunca queda por encima de ella."""
        with tempfile.TemporaryDirectory() as carpeta:
            # 1) rótulo con una imagen raster en la zona baja del marco
            con_imagen = os.path.join(carpeta, "rotulo con imagen.pdf")
            doc, page = soporte.blank_page()
            soporte.add_frame(page, x_mm=20, y_mm=20, w_mm=FRAME_W_MM, h_mm=FRAME_H_MM)
            soporte.add_text_lines(page, x_mm=24, first_baseline_mm=32, count=2, step_mm=9)
            # la imagen vive entre y = 163 y 176 mm; el marco termina en y = 183 mm
            rect_imagen = soporte.add_dark_image(page, x_mm=30, y_mm=163, w_mm=20, h_mm=13)
            soporte.save(doc, con_imagen)

            # 2) rótulo gemelo sin la imagen: sirve para comparar tamaños
            sin_imagen = os.path.join(carpeta, "rotulo sin imagen.pdf")
            doc, page = soporte.blank_page()
            soporte.add_frame(page, x_mm=20, y_mm=20, w_mm=FRAME_W_MM, h_mm=FRAME_H_MM)
            soporte.add_text_lines(page, x_mm=24, first_baseline_mm=32, count=2, step_mm=9)
            soporte.save(doc, sin_imagen)

            destino_imagen = os.path.join(carpeta, "rotulo con imagen_10x15.pdf")
            destino_texto = os.path.join(carpeta, "rotulo sin imagen_10x15.pdf")
            filas_imagen, avisos_imagen = etiqueta.convert(con_imagen, destino_imagen)
            filas_texto, _ = etiqueta.convert(sin_imagen, destino_texto)

            fila = filas_imagen[0]
            self.assertTrue(fila["frame_found"], "no se detectó el marco del rótulo")

            # el corte se mide contra el fondo de la imagen, no contra el del texto
            fondo_imagen_mm = soporte.pts_to_mm(rect_imagen.y1)
            aire_bajo_la_imagen_mm = (20.0 + FRAME_H_MM) - fondo_imagen_mm
            self.assertGreater(
                fila["trimmed_mm"],
                0.0,
                "no recortó nada: la etiqueta sale más chica de lo necesario (aire %.1f mm)"
                % aire_bajo_la_imagen_mm,
            )
            self.assertLessEqual(
                fila["trimmed_mm"],
                aire_bajo_la_imagen_mm + 0.5,
                "el corte (%.1f mm) quedó por encima del fondo de la imagen (%.1f mm)"
                % (fila["trimmed_mm"], fondo_imagen_mm),
            )
            self.assertFalse(
                any("espacio muerto" in aviso for aviso in avisos_imagen),
                "volvió la guarda que se niega a recortar: %r" % (avisos_imagen,),
            )

            salida = fitz.open(destino_imagen)
            try:
                self.assertEqual(1, salida.page_count)
                ancho_mm, alto_mm = soporte.page_size_mm(salida[0])
                self.assertAlmostEqual(100.0, ancho_mm, delta=0.2)
                self.assertAlmostEqual(150.0, alto_mm, delta=0.2)

                # Dónde tiene que quedar la tinta de la imagen: se mide en el origen
                # (por debajo de y = 150 mm sólo hay imagen) y se proyecta con la
                # escala y el margen que informó la conversión.
                origen_doc = fitz.open(con_imagen)
                try:
                    tinta_origen = soporte.ink_box_in_band_mm(origen_doc[0], 150.0, 195.0)
                finally:
                    origen_doc.close()
                self.assertIsNotNone(tinta_origen, "la imagen no se dibujó en el PDF de origen")
                escala = fila["scale"] / 100.0
                base_x_mm, base_y_mm = 20.0, 20.0   # esquina del marco en este fixture
                esperado = fitz.Rect(
                    fila["margin_x"] + (tinta_origen.x0 - base_x_mm) * escala,
                    fila["margin_y"] + (tinta_origen.y0 - base_y_mm) * escala,
                    fila["margin_x"] + (tinta_origen.x1 - base_x_mm) * escala,
                    fila["margin_y"] + (tinta_origen.y1 - base_y_mm) * escala,
                )

                tinta = soporte.ink_box_mm(salida[0])
                self.assertIsNotNone(tinta, "la etiqueta salió en blanco")
                self.assertAlmostEqual(
                    esperado.y1,
                    tinta.y1,
                    delta=1.5,
                    msg="la imagen del pie no se imprimió completa: la tinta llega a %.1f mm "
                    "y la imagen debería llegar a %.1f mm" % (tinta.y1, esperado.y1),
                )
                self.assertLessEqual(
                    tinta.y1, 149.8, "la tinta se sale de la etiqueta: %.1f mm" % tinta.y1
                )

                # al pie de la etiqueta tiene que estar la imagen, y sólo la imagen
                pie = soporte.ink_box_in_band_mm(salida[0], 100.0, 150.0)
                self.assertIsNotNone(pie, "no quedó nada de la imagen en el pie de la etiqueta")
                self.assertAlmostEqual(
                    esperado.y1, pie.y1, delta=1.5, msg="la imagen no llegó al pie de la etiqueta"
                )
                self.assertAlmostEqual(
                    esperado.x0, pie.x0, delta=1.5, msg="la imagen se movió a la izquierda"
                )
                self.assertAlmostEqual(
                    esperado.x1,
                    pie.x1,
                    delta=1.5,
                    msg="la imagen se movió a la derecha o se cortó: %.1f mm" % pie.x1,
                )
                self.assertLess(
                    pie.width, 50.0, "debe haber imagen al pie, no contenido de lado a lado"
                )
            finally:
                salida.close()

            # con imagen la etiqueta queda más chica: es lo esperado y no es un error
            self.assertGreater(
                filas_texto[0]["scale"],
                fila["scale"],
                "la salida con imagen no es más chica que la salida sin imagen",
            )

            salida_texto = fitz.open(destino_texto)
            try:
                self.assertIsNone(
                    soporte.ink_box_in_band_mm(salida_texto[0], 100.0, 150.0),
                    "la prueba sin imagen tiene contenido al pie: la comparación no sirve",
                )
            finally:
                salida_texto.close()


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
                any("espacio muerto" in aviso for aviso in warnings),
                "volvió la guarda que se niega a recortar: %r" % (warnings,),
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


class SeparadorAnchoDebajoDelTextoTest(unittest.TestCase):
    """S5 (triangulación): un separador interno de ancho completo es contenido, no borde.

    El separador no está pegado a los bordes del marco, así que no es el marco:
    cuenta como contenido y el recorte lo respeta, sin bloquear nada.
    """

    def test_separador_ancho_debajo_del_texto_cuenta_como_contenido(self):
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

            # el marco termina en y = 183 mm y el separador en 168 mm
            self.assertGreaterEqual(
                rows[0]["trimmed_mm"],
                12.0,
                "el separador ancho bloqueó el recorte en vez de contar como contenido",
            )
            self.assertLessEqual(
                rows[0]["trimmed_mm"],
                15.5,
                "el corte pasó por encima del separador (%.1f mm)" % rows[0]["trimmed_mm"],
            )
            self.assertFalse(
                any("espacio muerto" in aviso for aviso in warnings),
                "volvió la guarda que se niega a recortar: %r" % (warnings,),
            )

            salida = fitz.open(destino)
            try:
                tinta = soporte.ink_box_mm(salida[0])
                self.assertIsNotNone(tinta, "la etiqueta salió en blanco")
                self.assertGreaterEqual(
                    tinta.y1, 145.0, "el separador del pie no llegó a la etiqueta"
                )
                self.assertGreater(
                    tinta.width, 80.0, "el separador se imprimió más angosto de lo que es"
                )
            finally:
                salida.close()


class RotuloTipoCorreoTest(unittest.TestCase):
    """Regresión de producción: un rótulo como el real tiene que recortar su aire.

    Geometría medida en el PDF real: página A4 horizontal, marco de 86 x 163 mm,
    el contenido termina ~20 mm por encima del borde inferior del marco y hay un
    separador horizontal de ancho completo dentro del contenido. Antes del
    arreglo la guarda conservadora se negaba a recortar y la etiqueta salía
    79.1 x 150.0 mm (14 % más chica) en vez de ~90 x 150 mm.
    """

    def test_rotulo_tipo_correo_recorta_el_aire_del_pie(self):
        with tempfile.TemporaryDirectory() as carpeta:
            origen = os.path.join(carpeta, "rotulo correo.pdf")
            doc, page = soporte.blank_page(width_mm=297.0, height_mm=210.0)
            soporte.add_frame(page, x_mm=20, y_mm=21, w_mm=FRAME_W_MM, h_mm=FRAME_H_MM)
            page.insert_text((soporte.mm(24), soporte.mm(30)), "Correo Argentino")
            soporte.add_text_lines(page, x_mm=24, first_baseline_mm=46, count=12, step_mm=9)
            # separador de ancho completo al pie del contenido: y = 163.8 mm,
            # a 20.2 mm del borde inferior del marco (y = 184 mm)
            soporte.add_wide_rule(page, x_mm=20, y_mm=163.8, w_mm=FRAME_W_MM)
            soporte.save(doc, origen)
            destino = os.path.join(carpeta, "rotulo correo_10x15.pdf")

            rows, warnings = etiqueta.convert(origen, destino)

            fila = rows[0]
            self.assertTrue(fila["frame_found"], "no se detectó el marco del rótulo")
            self.assertGreaterEqual(
                fila["trimmed_mm"],
                15.0,
                "no recortó el aire del pie: la etiqueta sale chica de más ("
                "recorte %.1f mm)" % fila["trimmed_mm"],
            )
            self.assertFalse(
                any("espacio muerto" in aviso for aviso in warnings),
                "volvió la guarda que se niega a recortar: %r" % (warnings,),
            )

            salida = fitz.open(destino)
            try:
                self.assertEqual(1, salida.page_count)
                ancho_mm, alto_mm = soporte.page_size_mm(salida[0])
                self.assertAlmostEqual(100.0, ancho_mm, delta=0.01)
                self.assertAlmostEqual(150.0, alto_mm, delta=0.01)

                tinta = soporte.ink_box_mm(salida[0])
                self.assertIsNotNone(tinta, "la etiqueta salió en blanco")
                self.assertGreater(
                    tinta.width,
                    88.0,
                    "el contenido impreso mide %.1f mm de ancho: la etiqueta salió "
                    "más angosta que el marco" % tinta.width,
                )
                self.assertLessEqual(tinta.width, 99.8, "el contenido se sale de la etiqueta")
                self.assertGreaterEqual(
                    tinta.y1, 146.0, "el separador del pie no llegó al pie de la etiqueta"
                )
                self.assertLessEqual(tinta.y1, 149.8, "el contenido se sale de la etiqueta")
            finally:
                salida.close()


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
                any("espacio muerto" in aviso for aviso in warnings),
                "volvió la guarda que se niega a recortar: %r" % (warnings,),
            )


if __name__ == "__main__":
    unittest.main()
