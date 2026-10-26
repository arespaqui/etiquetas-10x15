"""Utilidades para armar y medir PDFs sintéticos en las pruebas (S4).

Nada de esto lee un PDF real: cada documento se arma en memoria y se guarda,
cuando hace falta, dentro del directorio temporal de la prueba.
"""

import pymupdf as fitz

PT_PER_MM = 72.0 / 25.4

# Un borde claro: el marco existe para el detector, pero no ensucia la medición
# de tinta, que es lo que se quiere medir por separado.
BORDER_SHADE = 0.93

# Umbral de gris para considerar que un píxel tiene tinta.
INK_THRESHOLD = 200


def mm(value):
    """Milímetros a puntos."""
    return value * PT_PER_MM


def pts_to_mm(value):
    """Puntos a milímetros."""
    return value / PT_PER_MM


def blank_page(width_mm=210.0, height_mm=297.0):
    """Documento nuevo con una página del tamaño pedido."""
    doc = fitz.open()
    return doc, doc.new_page(width=mm(width_mm), height=mm(height_mm))


def add_frame(page, x_mm=20.0, y_mm=20.0, w_mm=86.0, h_mm=163.0):
    """Dibuja el marco del rótulo como rectángulo contorneado."""
    rect = fitz.Rect(mm(x_mm), mm(y_mm), mm(x_mm + w_mm), mm(y_mm + h_mm))
    page.draw_rect(rect, color=(BORDER_SHADE, BORDER_SHADE, BORDER_SHADE), width=1.0)
    return rect


def add_text_lines(page, x_mm=24.0, first_baseline_mm=32.0, count=1, step_mm=9.0):
    """Escribe `count` líneas de texto y devuelve la lista de líneas base usadas."""
    baselines = []
    for index in range(count):
        baseline_mm = first_baseline_mm + index * step_mm
        page.insert_text((mm(x_mm), mm(baseline_mm)), "LINEA %02d DE PRUEBA" % (index + 1))
        baselines.append(baseline_mm)
    return baselines


def add_wide_rule(page, x_mm, y_mm, w_mm, shade=0.15):
    """Dibuja una línea horizontal ancha: un dibujo que el recorte viejo tampoco veía."""
    page.draw_line(
        (mm(x_mm), mm(y_mm)), (mm(x_mm + w_mm), mm(y_mm)), color=(shade, shade, shade), width=1.0
    )


def add_dark_image(page, x_mm, y_mm, w_mm, h_mm, side=24):
    """Pega una imagen raster oscura: el contenido que el recorte no veía."""
    rect = fitz.Rect(mm(x_mm), mm(y_mm), mm(x_mm + w_mm), mm(y_mm + h_mm))
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, side, side), False)
    view = pix.samples_mv
    view[:] = bytes([255]) * len(view)
    for y in range(side // 4, 3 * side // 4):
        for x in range(side // 4, 3 * side // 4):
            pix.set_pixel(x, y, (0, 0, 0))
    page.insert_image(rect, pixmap=pix)
    return rect


def save(doc, path):
    """Guarda el documento en `path` (siempre dentro del temporal de la prueba)."""
    doc.save(path, garbage=4, deflate=True)
    doc.close()
    return path


def _ink_rows(pix):
    """Filas (en píxeles) que tienen al menos un píxel de tinta."""
    samples, width, height, stride = pix.samples, pix.width, pix.height, pix.stride
    rows = []
    for y in range(height):
        row = samples[y * stride: y * stride + width]
        if min(row) < INK_THRESHOLD:
            rows.append(y)
    return rows


def _ink_columns(pix, rows):
    """Columnas extremas con tinta, mirando solo las filas que ya se sabe que la tienen."""
    samples, width, height, stride = pix.samples, pix.width, pix.height, pix.stride
    x0 = x1 = None
    for y in rows:
        row = samples[y * stride: y * stride + width]
        for x in range(width):
            if row[x] < INK_THRESHOLD:
                if x0 is None or x < x0:
                    x0 = x
                if x1 is None or x > x1:
                    x1 = x
    return x0, x1


def _render(page, dpi):
    return page.get_pixmap(
        matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), colorspace=fitz.csGRAY, alpha=False
    )


def ink_box_mm(page, dpi=100):
    """Caja de la tinta visible, medida renderizando la página. None si está vacía."""
    pix = _render(page, dpi)
    rows = _ink_rows(pix)
    if not rows:
        return None
    x0, x1 = _ink_columns(pix, rows)
    if x0 is None:
        return None
    scale = 25.4 / dpi
    return fitz.Rect(
        x0 * scale, rows[0] * scale, (x1 + 1) * scale, (rows[-1] + 1) * scale
    )


def ink_bands_mm(page, dpi=100):
    """Franjas horizontales de tinta separadas por blanco: una por línea de texto."""
    pix = _render(page, dpi)
    rows = _ink_rows(pix)
    if not rows:
        return []
    scale = 25.4 / dpi
    bands = []
    start = previous = rows[0]
    for y in rows[1:]:
        if y > previous + 1:
            bands.append((start * scale, (previous + 1) * scale))
            start = y
        previous = y
    bands.append((start * scale, (previous + 1) * scale))
    return bands


def page_size_mm(page):
    return pts_to_mm(page.rect.width), pts_to_mm(page.rect.height)
