"""Pruebas de errores visibles (S7): con pythonw no hay consola, así que ningún error puede perderse.

El módulo `app_etiquetas.pyw` se carga con `SourceFileLoader`, sin ejecutar
`main()` y sin instanciar `App`: estas pruebas nunca abren una ventana de Tk.
El log se redirige a un archivo temporal para no tocar el `errores.log` real.
"""

import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock

from tests import ROOT

APP_PATH = os.path.join(ROOT, "app_etiquetas.pyw")
NOMBRE_MODULO = "app_etiquetas_bajo_prueba"


def ruta_log_por_defecto():
    """`errores.log` junto al .pyw, calculado sin escribir nada."""
    return os.path.join(ROOT, "errores.log")


def leer(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def cargar_app():
    """Importa el .pyw como módulo, sin ejecutar main() ni crear ventanas."""
    loader = importlib.machinery.SourceFileLoader(NOMBRE_MODULO, APP_PATH)
    spec = importlib.util.spec_from_loader(NOMBRE_MODULO, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


class ErroresVisiblesTest(unittest.TestCase):
    """S7: los errores quedan en el log y en pantalla, también sin consola."""

    @classmethod
    def setUpClass(cls):
        cls.app = cargar_app()

    def setUp(self):
        # Cargar el módulo no puede haber abierto una ventana de Tk.
        self.assertIsNone(
            self.app.tk._default_root, "cargar el módulo abrió una ventana de Tk"
        )

    def huella(self, path):
        """Tamaño y fecha de un archivo, o None si no existe."""
        if not os.path.exists(path):
            return None
        info = os.stat(path)
        return (info.st_size, info.st_mtime_ns)

    def test_convert_many_informa_y_registra_los_archivos_que_fallan(self):
        """Un PDF inexistente o corrupto no mata el proceso, y queda anotado en el log."""
        with tempfile.TemporaryDirectory() as carpeta:
            log = os.path.join(carpeta, "errores.log")
            inexistente = os.path.join(carpeta, "no existe.pdf")
            corrupto = os.path.join(carpeta, "roto.pdf")
            with open(corrupto, "wb") as handle:
                handle.write(b"esto no es un PDF\n")

            with mock.patch.dict(os.environ, {self.app.LOG_ENV_VAR: log}):
                resultados = self.app.convert_many([inexistente, corrupto])

            self.assertEqual(
                2, len(resultados), "no devolvió una fila por archivo: %r" % (resultados,)
            )
            for resultado, origen in zip(resultados, [inexistente, corrupto]):
                self.assertEqual(origen, resultado["source"])
                self.assertIsNone(
                    resultado["target"],
                    "dio un destino a un archivo que no se pudo convertir: %r" % (resultado,),
                )
                self.assertTrue(
                    resultado["error"], "no describió el problema de %s" % origen
                )

            self.assertTrue(
                os.path.isfile(log), "no dejó constancia de los errores en el log"
            )
            contenido = leer(log)
            self.assertIn("no existe.pdf", contenido, "el log no nombra el PDF inexistente")
            self.assertIn("roto.pdf", contenido, "el log no nombra el PDF corrupto")

    def test_fallo_inesperado_queda_en_el_log_aunque_no_haya_consola(self):
        """Con sys.stderr en None (pythonw) el fallo inesperado igual se escribe."""
        with tempfile.TemporaryDirectory() as carpeta:
            log = os.path.join(carpeta, "errores.log")

            with mock.patch.dict(os.environ, {self.app.LOG_ENV_VAR: log}):
                with mock.patch.object(self.app.messagebox, "showerror") as dialogo:
                    stderr_original = sys.stderr
                    try:
                        # Condición real de pythonw: no existe sys.stderr.
                        sys.stderr = None
                        try:
                            raise RuntimeError("fallo inesperado simulado")
                        except RuntimeError:
                            self.app._log_exception(*sys.exc_info())
                    finally:
                        sys.stderr = stderr_original

            self.assertTrue(
                os.path.isfile(log), "el fallo inesperado no llegó al log sin consola"
            )
            contenido = leer(log)
            self.assertIn("fallo inesperado simulado", contenido, "el log no guardó el mensaje")
            self.assertIn("Traceback", contenido, "el log no guardó la traza del fallo")
            self.assertIn(
                "RuntimeError", contenido, "el log no guardó el tipo de error"
            )
            self.assertTrue(dialogo.called, "no intentó avisar en pantalla")

    def test_con_override_el_log_va_al_archivo_temporal_y_no_al_lado_del_script(self):
        """La ruta del log es inyectable: con override no se toca el errores.log real."""
        junto_al_script = ruta_log_por_defecto()
        antes = self.huella(junto_al_script)

        with tempfile.TemporaryDirectory() as carpeta:
            log = os.path.join(carpeta, "errores.log")
            inexistente = os.path.join(carpeta, "no existe.pdf")

            with mock.patch.dict(os.environ, {self.app.LOG_ENV_VAR: log}):
                self.assertEqual(log, self.app.log_path(), "no respetó la ruta indicada")
                self.app.convert_many([inexistente])

            self.assertTrue(
                os.path.isfile(log), "no escribió el log en la ruta indicada por el override"
            )
            self.assertIn("no existe.pdf", leer(log))

        self.assertEqual(
            antes,
            self.huella(junto_al_script),
            "escribió el log al lado del script aunque había override",
        )

    def test_sin_override_la_ruta_por_defecto_sigue_siendo_errores_log_junto_al_script(self):
        """Sin override el comportamiento no cambia: errores.log junto al script."""
        antes = self.huella(ruta_log_por_defecto())

        with mock.patch.dict(os.environ):
            os.environ.pop(self.app.LOG_ENV_VAR, None)
            calculada = self.app.log_path()

        self.assertEqual(
            ruta_log_por_defecto(),
            calculada,
            "la ruta por defecto del log dejó de ser errores.log junto al script",
        )
        self.assertTrue(os.path.isabs(calculada), "la ruta por defecto no es absoluta")
        self.assertEqual(
            antes,
            self.huella(ruta_log_por_defecto()),
            "calcular la ruta por defecto escribió el archivo real",
        )

    def test_si_el_log_no_se_puede_escribir_avisa_en_pantalla_sin_romper(self):
        """Triangulación: un log imposible de escribir no puede tragarse el error."""
        with tempfile.TemporaryDirectory() as carpeta:
            # Un directorio en lugar de un archivo: abrirlo para agregar falla siempre.
            with mock.patch.dict(os.environ, {self.app.LOG_ENV_VAR: carpeta}):
                with mock.patch.object(self.app.messagebox, "showerror") as dialogo:
                    try:
                        raise RuntimeError("fallo sin log posible")
                    except RuntimeError:
                        self.app._log_exception(*sys.exc_info())

            self.assertTrue(dialogo.called, "no avisó en pantalla pese a no poder escribir el log")
            mensaje = dialogo.call_args[0][1] if dialogo.call_args[0] else ""
            self.assertIn(
                "No se pudo guardar", mensaje, "el aviso no aclara que el log no se pudo guardar"
            )
            self.assertIn("fallo sin log posible", mensaje, "el aviso no muestra el detalle")


class UbicacionDelLogTest(unittest.TestCase):
    """S7: el log tiene que quedar donde la persona lo encuentra, también empaquetado.

    Empaquetada con PyInstaller, `__file__` vive dentro de la carpeta `_internal`,
    así que el log quedaba en `_internal\\errores.log`: nadie lo encuentra ahí. Con la app
    congelada (`sys.frozen`) el log va junto al ejecutable; desde el código fuente
    sigue al lado del `.pyw`; y `ETIQUETAS_10X15_LOG` gana siempre.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = cargar_app()

    def sin_override(self):
        """Deja el entorno sin ETIQUETAS_10X15_LOG mientras dure el bloque."""
        entorno = mock.patch.dict(os.environ)
        entorno.start()
        self.addCleanup(entorno.stop)
        os.environ.pop(self.app.LOG_ENV_VAR, None)

    def congelada(self, ejecutable):
        """Simula el ejecutable empaquetado: sys.frozen y sys.executable apuntan ahí."""
        frozen = mock.patch.object(sys, "frozen", True, create=True)
        frozen.start()
        self.addCleanup(frozen.stop)
        exe = mock.patch.object(sys, "executable", ejecutable)
        exe.start()
        self.addCleanup(exe.stop)

    def test_empaquetada_el_log_queda_junto_al_ejecutable(self):
        """Congelada: errores.log al lado del .exe, no dentro de _internal."""
        with tempfile.TemporaryDirectory() as carpeta:
            ejecutable = os.path.join(carpeta, "Etiquetas 10x15.exe")

            self.sin_override()
            self.congelada(ejecutable)
            ruta = self.app.log_path()

            # La ubicación primero: si falla, la prueba no escribe nada real.
            self.assertEqual(
                os.path.join(carpeta, "errores.log"),
                ruta,
                "empaquetada, el log no quedó junto al ejecutable",
            )

            guardado = self.app.write_log("prueba de log empaquetado\n")

            self.assertTrue(guardado, "no pudo escribir el log junto al ejecutable")
            self.assertTrue(
                os.path.isfile(ruta), "el log junto al ejecutable no existe en disco"
            )
            self.assertIn(
                "prueba de log empaquetado",
                leer(ruta),
                "el texto no llegó al log junto al ejecutable",
            )

    def test_el_override_gana_tambien_empaquetada(self):
        """Triangulación: ETIQUETAS_10X15_LOG manda sobre la ubicación del ejecutable."""
        with tempfile.TemporaryDirectory() as carpeta:
            elegido = os.path.join(carpeta, "a elección", "diagnostico.log")
            ejecutable = os.path.join(carpeta, "Etiquetas 10x15.exe")

            with mock.patch.dict(os.environ, {self.app.LOG_ENV_VAR: elegido}):
                self.congelada(ejecutable)
                ruta = self.app.log_path()

            self.assertEqual(elegido, ruta, "el override no ganó sobre el ejecutable")
            self.assertFalse(
                os.path.exists(os.path.join(carpeta, "errores.log")),
                "con override igual apuntó al log junto al ejecutable",
            )

    def test_desde_el_codigo_fuente_el_log_sigue_junto_al_pyw(self):
        """Triangulación: sin congelar, el log sigue al lado del .pyw."""
        with tempfile.TemporaryDirectory() as carpeta:
            # sys.executable apunta a otra carpeta: no debe influir sin congelar.
            with mock.patch.object(sys, "executable", os.path.join(carpeta, "python.exe")):
                self.sin_override()
                ruta = self.app.log_path()

            self.assertEqual(
                os.path.join(ROOT, "errores.log"),
                ruta,
                "desde el código fuente el log dejó de quedar junto al .pyw",
            )
            self.assertFalse(
                os.path.exists(os.path.join(carpeta, "errores.log")),
                "usó sys.executable sin estar congelada",
            )


if __name__ == "__main__":
    unittest.main()
