#!/usr/bin/env python3
"""
Re-frame shipping-label PDFs to an exact 100 x 150 mm page (4 x 6 in thermal stock).

Design rules (do not break these):
  1. The label area is DETECTED by rendering the page and finding the ink, never
     hardcoded. A hardcoded rectangle breaks silently when the template changes.
  2. Scaling is ALWAYS uniform. Barcodes must never be stretched: a distorted
     barcode can fail to scan, and a rejected parcel costs more than any of this.
  3. The tool reports the aspect mismatch instead of hiding it. If the label is
     not shaped 100:150, the operator has to know.
"""

import os
import sys

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24 preferred module name
except ImportError:
    try:
        import fitz  # older releases
    except ImportError:
        fitz = None  # reported by whoever calls us, never exit silently

try:
    from PIL import Image
except ImportError:
    Image = None

PT_PER_MM = 72.0 / 25.4
LABEL_W_PT = 100.0 * PT_PER_MM
LABEL_H_PT = 150.0 * PT_PER_MM
LABEL_ASPECT = LABEL_W_PT / LABEL_H_PT

RENDER_DPI = 150
INK_THRESHOLD = 245
PAD_PT = 1.0
ASPECT_TOLERANCE = 0.03

# Label-frame detection thresholds (see detect_label_frame).
MIN_LABEL_MM = 20.0          # a label side shorter than this is not a label
MIN_FRAME_FRACTION = 0.02    # a frame smaller than 2% of the page is decoration
MAX_FRAME_FRACTION = 0.70    # a frame covering most of the page is a trim border
MIN_TEXT_INSIDE = 0.50       # the frame must hold most of the text
MIN_TRIM_MM = 5.0            # trim dead white space at the end when it is at least this tall
EDGE_MARGIN_MM = 2.0         # keep content off the label edge: thermal printers clip the very edge
BORDER_TOLERANCE_PT = 2.0    # a stroke this close to the frame rectangle IS the frame, not content

MM = PT_PER_MM


def ink_bbox(page):
    """Fallback: ink bounding box by rendering. Used only when no label frame is found."""
    if Image is None:
        return fitz.Rect(page.rect)

    zoom = RENDER_DPI / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    grey = img.convert("L")
    mask = grey.point(lambda v: 255 if v < INK_THRESHOLD else 0)
    box = mask.getbbox()
    if not box:
        return fitz.Rect(page.rect)

    scale = 72.0 / RENDER_DPI
    detected = fitz.Rect(
        box[0] * scale,
        box[1] * scale,
        box[2] * scale,
        box[3] * scale,
    )
    detected = detected + (-PAD_PT, -PAD_PT, PAD_PT, PAD_PT)
    detected.normalize()
    return detected.intersect(page.rect)


def detect_label_frame(page):
    """Find the label outline as a stroked rectangle.

    Shipping-label PDFs draw the label as an outlined rectangle. Detecting that
    outline is precise and immune to the loose text, guide marks and specks that
    merged documents carry outside the label -- garbage that inflates a naive
    ink bounding box.

    Rejected: strokes thicker than a frame, and rectangles covering most of the
    page (a page/trim border is not the label).
    """
    pr = page.rect
    page_area = pr.width * pr.height
    if page_area <= 0:
        return None

    candidates = {}
    for drawing in page.get_drawings():
        if drawing.get("type") != "s":
            continue
        stroke = drawing.get("width") or 0
        if stroke > 3.0:
            continue

        rect = fitz.Rect(drawing["rect"])
        if rect.width / MM < MIN_LABEL_MM or rect.height / MM < MIN_LABEL_MM:
            continue

        fraction = (rect.width * rect.height) / page_area
        if fraction < MIN_FRAME_FRACTION or fraction > MAX_FRAME_FRACTION:
            continue

        key = (round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1))
        candidates[key] = (rect.width * rect.height, rect)

    if not candidates:
        return None

    best = max(candidates.values(), key=lambda item: item[0])[1]
    return best.intersect(pr)


def frame_holds_content(page, frame):
    """Sanity check: most of the page text must live inside the detected frame."""
    blocks = page.get_text("blocks") or []
    if not blocks:
        return True
    inside = 0
    for block in blocks:
        rect = fitz.Rect(block[:4])
        centre = fitz.Point((rect.x0 + rect.x1) / 2.0, (rect.y0 + rect.y1) / 2.0)
        if frame.contains(centre):
            inside += 1
    return inside / float(len(blocks)) >= MIN_TEXT_INSIDE


def image_rects(page):
    """Bounding boxes of the raster images on a page.

    Text blocks and drawings say nothing about pixels, so an image used to be
    invisible to the trim: the dead-space estimate called a label with a logo or
    a stamp at the bottom empty and cut it away. Two independent sources are
    read (the text dict and the display list log) so a change in one API cannot
    hide an image again.
    """
    rects = []

    try:
        blocks = page.get_text("dict").get("blocks") or []
    except Exception:
        blocks = []
    for block in blocks:
        if block.get("type") != 1:  # 1 = raster image block
            continue
        rects.append(fitz.Rect(block["bbox"]))

    try:
        entries = page.get_bboxlog() or []
    except Exception:
        entries = []
    for entry in entries:
        if not entry or "image" not in str(entry[0]):
            continue
        rects.append(fitz.Rect(entry[1]))

    return [rect for rect in rects if rect.width > 0.5 and rect.height > 0.5]


def looks_like_frame_border(rect, frame):
    """True when a stroke is the frame outline itself and not content drawn inside it.

    The test is purely geometric: the frame stroke lies ON the frame rectangle
    and runs along it. A horizontal separator inside the label spans the frame
    width too, but sits away from the top and bottom edges, so it stays content.

    Counting the frame border as content was the bug that made every real label
    trim zero: the border bottom row became the content bottom row.
    """
    spans_width = rect.width >= frame.width * 0.9
    spans_height = rect.height >= frame.height * 0.9

    near_top = (
        abs(rect.y0 - frame.y0) <= BORDER_TOLERANCE_PT
        or abs(rect.y1 - frame.y0) <= BORDER_TOLERANCE_PT
    )
    near_bottom = (
        abs(rect.y1 - frame.y1) <= BORDER_TOLERANCE_PT
        or abs(rect.y0 - frame.y1) <= BORDER_TOLERANCE_PT
    )
    near_left = (
        abs(rect.x0 - frame.x0) <= BORDER_TOLERANCE_PT
        or abs(rect.x1 - frame.x0) <= BORDER_TOLERANCE_PT
    )
    near_right = (
        abs(rect.x1 - frame.x1) <= BORDER_TOLERANCE_PT
        or abs(rect.x0 - frame.x1) <= BORDER_TOLERANCE_PT
    )

    if spans_width and (near_top or near_bottom):
        return True
    if spans_height and (near_left or near_right):
        return True
    # the whole frame drawn as a single rectangle path
    return spans_width and spans_height


def content_inside(page, frame):
    """Where the real content of a label frame starts and ends.

    Shipping labels often carry dead white space at the end. Scaling the whole
    frame into the stock then shrinks everything for nothing: trimming that air
    first makes the printed label bigger without touching any content.

    The content is the union of the text blocks, the drawings that are not the
    frame border and the raster images inside the frame. Nothing else can be
    lost by cutting at the bottom of that union, so no conservative veto is
    needed -- a veto is what used to shrink real labels by 14%.

    Returns a fitz.Rect spanning the frame width between the first and the last
    content row, or None when nothing inside the frame is content.
    """
    inner = fitz.Rect(frame.x0 + 1, frame.y0 + 1, frame.x1 - 1, frame.y1 - 1)

    def inside(rect):
        centre = fitz.Point((rect.x0 + rect.x1) / 2.0, (rect.y0 + rect.y1) / 2.0)
        return inner.contains(centre)

    rects = [fitz.Rect(block[:4]) for block in page.get_text("blocks") or []]

    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing["rect"])
        if looks_like_frame_border(rect, frame):
            continue
        rects.append(rect)

    rects.extend(image_rects(page))

    rects = [rect for rect in rects if inside(rect)]
    if not rects:
        return None

    top = min(rect.y0 for rect in rects)
    bottom = max(rect.y1 for rect in rects)
    return fitz.Rect(frame.x0, top, frame.x1, bottom)


def describe(rect, label="area"):
    return "%.1f x %.1f mm" % (rect.width / MM, rect.height / MM)


def convert(src_path, out_path, trim_dead_space=True):
    if fitz is None:
        raise RuntimeError("falta PyMuPDF: python -m pip install --user pymupdf")
    src = fitz.open(src_path)
    out = fitz.open()
    warnings = []
    rows = []

    for pno in range(src.page_count):
        page = src[pno]

        box = detect_label_frame(page)
        if box is not None and not frame_holds_content(page, box):
            box = None
        frame_found = box is not None
        if box is None:
            box = ink_bbox(page)
            warnings.append(
                "pagina %d: no se encontro el marco del rotulo, se usa el area con tinta "
                "(puede incluir marcas sueltas de la hoja)" % (pno + 1)
            )

        if box.width <= 0.5 or box.height <= 0.5:
            warnings.append("pagina %d: no se detecto contenido, se copia la pagina completa" % (pno + 1))
            box = fitz.Rect(page.rect)

        trimmed_mm = 0.0
        if trim_dead_space:
            content = content_inside(page, box)
            if content is not None:
                dead = (box.y1 - content.y1) / MM
                if dead >= MIN_TRIM_MM:
                    # Nothing real can be lost: the cut line is the bottom of the
                    # content, images and inner separators included.
                    margin = EDGE_MARGIN_MM * MM   # mm -> points
                    top = max(box.y0, min(box.y0, content.y0) - margin)
                    bottom = min(box.y1, content.y1 + margin)
                    box = fitz.Rect(box.x0, top, box.x1, bottom)
                    trimmed_mm = dead

        src_aspect = box.width / box.height
        mismatch = abs(src_aspect - LABEL_ASPECT) / LABEL_ASPECT

        # Uniform scale only: contain, never stretch.
        scale = min(LABEL_W_PT / box.width, LABEL_H_PT / box.height)

        draw_w = box.width * scale
        draw_h = box.height * scale
        off_x = (LABEL_W_PT - draw_w) / 2.0
        off_y = (LABEL_H_PT - draw_h) / 2.0

        new_page = out.new_page(width=LABEL_W_PT, height=LABEL_H_PT)
        target = fitz.Rect(off_x, off_y, off_x + draw_w, off_y + draw_h)
        new_page.show_pdf_page(target, src, pno, clip=box)

        rows.append({
            "page": pno + 1,
            "frame_found": frame_found,
            "trimmed_mm": trimmed_mm,
            "source": describe(box),
            "printed": "%.1f x %.1f mm" % (draw_w / MM, draw_h / MM),
            "scale": scale * 100.0,
            "margin_x": off_x / MM,
            "margin_y": off_y / MM,
            "aspect": src_aspect,
            "mismatch": mismatch,
        })

        if mismatch > ASPECT_TOLERANCE:
            warnings.append(
                "pagina %d: el rotulo no es 10x15 (proporcion %.3f, esperada %.3f). "
                "Queda %.1f x %.1f mm con %.0f mm de blanco a cada lado. "
                "CONVIENE PEDIR EL ROTULO EN FORMATO 10x15 AL ORIGEN."
                % (pno + 1, src_aspect, LABEL_ASPECT, draw_w / MM, draw_h / MM, off_x / MM)
            )

    out.save(out_path, garbage=4, deflate=True)
    out.close()
    src.close()
    return rows, warnings


def main(argv):
    if fitz is None:
        print("ERROR: falta PyMuPDF.")
        print("Instalalo con:  python -m pip install --user pymupdf")
        return 1

    targets = [a for a in argv[1:] if a.lower().endswith(".pdf")]
    if not targets:
        print("USO: arrastra uno o mas archivos PDF sobre A_etiqueta_10x15.bat")
        print("     (o pasa las rutas como argumentos)")
        return 1

    print("=" * 78)
    print(" ROTULOS -> 100 x 150 mm  (escala uniforme, sin deformar codigos)")
    print("=" * 78)

    failures = 0
    for src_path in targets:
        if not os.path.isfile(src_path):
            print("\n[FALTA] %s" % src_path)
            failures += 1
            continue

        base, ext = os.path.splitext(src_path)
        out_path = base + "_10x15" + ext
        n = 2
        while os.path.exists(out_path):
            out_path = "%s_10x15 (%d)%s" % (base, n, ext)
            n += 1

        print("\n>> %s" % os.path.basename(src_path))
        try:
            rows, warnings = convert(src_path, out_path)
        except Exception as exc:
            print("   [ERROR] no se pudo convertir: %s" % exc)
            failures += 1
            continue

        for r in rows:
            print("   pagina %d: origen %-16s -> impreso %-16s escala %6.1f%%  blanco X %4.1f mm / Y %4.1f mm"
                  % (r["page"], r["source"], r["printed"], r["scale"], r["margin_x"], r["margin_y"]))

        for w in warnings:
            print("   ! AVISO: %s" % w)

        print("   [OK] %s" % os.path.basename(out_path))

    print("\n" + "=" * 78)
    print(" Imprimir con:  papel = Etiquetas 100x150   escala = TAMANO REAL   paginas = 1")
    print("=" * 78)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
