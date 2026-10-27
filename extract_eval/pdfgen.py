"""Minimal text-only PDF writer, so the dataset can be generated with no extra dependencies."""
import textwrap

PAGE_W, PAGE_H = 612, 792
LINES_PER_PAGE = 54


def _escape(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(lines, width=92):
    out = []
    for line in lines:
        out.extend(textwrap.wrap(line, width) or [""])
    return out


def write_pdf(path, lines, font_size=10):
    lines = _wrap(lines)
    pages = [lines[i:i + LINES_PER_PAGE] for i in range(0, len(lines), LINES_PER_PAGE)] or [[]]

    objects = []  # object bodies; object number = index + 1
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(None)  # pages tree, filled in once page object numbers are known
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    page_refs = []
    for page_lines in pages:
        ops = [f"BT /F1 {font_size} Tf {font_size + 4} TL 50 {PAGE_H - 60} Td"]
        ops += [f"({_escape(l)}) Tj T*" for l in page_lines]
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1", "replace")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream.decode('latin-1')}\nendstream")
        content_num = len(objects)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>"
        )
        page_refs.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>"

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for num, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{num} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as f:
        f.write(out)
