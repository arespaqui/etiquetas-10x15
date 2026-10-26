"""Pruebas del paquete público Etiquetas 10x15 (S1, S4).

Todos los PDFs de prueba se generan dentro de un directorio temporal durante la
prueba: el repo nunca guarda un PDF real ni datos de personas.
"""

import os
import sys

# El motor vive en la raíz del paquete; las pruebas se importan desde tests/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
