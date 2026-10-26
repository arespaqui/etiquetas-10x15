"""Verify a re-framed label PDF: page geometry and ink geometry, measured."""

import sys

try:
    import pymupdf as fitz
    _ = fitz.version
except ImportError:
    import fitz
from PIL import Image

PT_PER_MM = 72.0 / 25.4
MM = PT_PER_MM
RENDER_DPI = 150
INK_THRESHOLD = 245

LABEL_W_MM = 100.0
LABEL_H_MM = 150.0
LABEL_ASPECT = LABEL_W_MM / LABEL_H_MM


def ink_bbox_mm(page):
    zoom = RENDER_DPI / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    mask = img.convert("L").point(lambda v: 255 if v < INK_THRESHOLD else 0)
    box = mask.getbbox()
    if not box:
        return None
    s = 72.0 / RENDER_DPI
    return fitz.Rect(box[0] * s, box[1] * s, box[2] * s, box[3] * s)


def main(path):
    doc = fitz.open(path)
    print("archivo: %s" % path)
    print("paginas: %d\n" % doc.page_count)

    ok = True
    for i, page in enumerate(doc):
        w_mm = page.rect.width / MM
        h_mm = page.rect.height / MM
        page_ok = abs(w_mm - LABEL_W_MM) < 0.2 and abs(h_mm - LABEL_H_MM) < 0.2
        ok = ok and page_ok

        print("pagina %d" % (i + 1))
        print("  tamano de pagina : %.2f x %.2f mm   %s"
              % (w_mm, h_mm, "[OK 100x150]" if page_ok else "[MAL, se esperaba 100x150]"))

        box = ink_bbox_mm(page)
        if box is None:
            print("  tinta            : (pagina vacia)")
            ok = False
            continue

        iw = box.width / MM
        ih = box.height / MM
        aspect = iw / ih
        aspect_err = abs(aspect - LABEL_ASPECT) / LABEL_ASPECT
        fills_h = abs(ih - LABEL_H_MM) < 0.6
        centered = abs(box.x0 - (page.rect.width - box.width) / 2) < 1.0

        print("  tinta            : %.2f x %.2f mm  en x=%.2f y=%.2f mm" % (iw, ih, box.x0 / MM, box.y0 / MM))
        print("  proporcion       : %.4f  (objetivo %.4f, desvio %.2f%%)"
              % (aspect, LABEL_ASPECT, aspect_err * 100))
        print("  llena el alto    : %s" % ("si" if fills_h else "no"))
        print("  centrado en X    : %s" % ("si" if centered else "no"))

        if not fills_h or not centered:
            ok = False
            print("  -> FALLA: el contenido no esta donde corresponde")
        if box.x1 > page.rect.width + 0.5 or box.y1 > page.rect.height + 0.5:
            ok = False
            print("  -> FALLA: el contenido se sale de la pagina (recorte)")
        print()

    print("RESULTADO: %s" % ("TODO OK" if ok else "HAY PROBLEMAS"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
