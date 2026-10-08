#!/usr/bin/env python3
"""Generate faceplate line drawings from the KiCad faceplate file.

Writes docs/images/panel.svg (annotated front view) and docs/images/panel-plain.svg
(the panel alone, for packaging labels where small captions would be lost).
Run from anywhere: python3 docs/drawings/make_panel_svg.py

The faceplate file is KiCad's S-expression format (KiCad 10: footprints, nested
stroke/effects blocks, quoted layer names). Parsed with a small generic
S-expression reader rather than ad hoc regexes, since graphics like the logo
live inside a footprint and need its position and rotation applied.
"""
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "hardware" / "panel" / "PassiveAttenuatorFaceplate.kicad_pcb"
OUT = ROOT / "docs" / "images"

INK = "#1a1a1a"
DIM = "#555"
RED = "#d9302c"
FONT = "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'"

# Drill sizes (mm) that identify each kind of hole.
JACK, POT = 6.0, 7.0

# Footprints that carry the Schenktronics wordmark as silkscreen polygons.
LOGO_FOOTPRINT = "SchentronicsLogo"


def read_sexp(text):
    """Parse a KiCad S-expression file into nested lists of strings."""
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)

    def parse(pos):
        items = []
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == "(":
                node, pos = parse(pos + 1)
                items.append(node)
            elif tok == ")":
                return items, pos + 1
            else:
                items.append(tok[1:-1] if tok.startswith('"') else tok)
                pos += 1
        return items, pos

    node, _ = parse(1)  # skip the opening paren of (kicad_pcb ...)
    return node


def tagged(node, name):
    """Direct children of node that are lists starting with `name`."""
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def first(node, name):
    found = tagged(node, name)
    return found[0] if found else None


def at_xyr(node):
    a = first(node, "at")
    vals = [float(v) for v in a[1:]] if a else []
    while len(vals) < 3:
        vals.append(0.0)
    return tuple(vals[:3])


def stroke_width(node):
    s = first(node, "stroke")
    w = first(s, "width") if s else None
    return float(w[1]) if w else 0.2


def parse(path):
    root = read_sexp(path.read_text())

    edges = []
    for e in tagged(root, "gr_line"):
        if first(e, "layer") and first(e, "layer")[1] == "Edge.Cuts":
            sx, sy = (float(v) for v in first(e, "start")[1:])
            ex, ey = (float(v) for v in first(e, "end")[1:])
            edges.append((sx, sy, ex, ey))
    xs = [v for e in edges for v in (e[0], e[2])]
    ys = [v for e in edges for v in (e[1], e[3])]
    outline = (min(xs), min(ys), max(xs), max(ys))

    holes = []
    for fp in tagged(root, "footprint"):
        if "Mounting_Holes" in fp[1]:
            x, y, _ = at_xyr(fp)
            pad = first(fp, "pad")
            holes.append((x, y, float(first(pad, "drill")[1])))

    silk_lines = []
    for e in tagged(root, "gr_line"):
        layer = first(e, "layer")
        if layer and layer[1] == "F.SilkS":
            sx, sy = (float(v) for v in first(e, "start")[1:])
            ex, ey = (float(v) for v in first(e, "end")[1:])
            silk_lines.append(((sx, sy, ex, ey), stroke_width(e)))

    # Rings around the jacks: a bold ring marks an output; inputs are unmarked.
    silk_rings = []
    for c in tagged(root, "gr_circle"):
        layer = first(c, "layer")
        if layer and layer[1] == "F.SilkS":
            cx, cy = (float(v) for v in first(c, "center")[1:])
            ex, ey = (float(v) for v in first(c, "end")[1:])
            r = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
            silk_rings.append((cx, cy, r, stroke_width(c)))

    texts = []
    for t in tagged(root, "gr_text"):
        layer = first(t, "layer")
        if not (layer and layer[1] == "F.SilkS"):
            continue
        x, y, rot = at_xyr(t)
        effects = first(t, "effects")
        font = first(effects, "font")
        size = float(first(font, "size")[1])
        justify = first(effects, "justify")
        italic = first(font, "italic") is not None
        texts.append(dict(text=t[1], x=x, y=y, rot=rot, size=size,
                          justify=justify[1] if justify else None, italic=italic))

    logo_polys = []
    for fp in tagged(root, "footprint"):
        if LOGO_FOOTPRINT not in fp[1]:
            continue
        ox, oy, orot = at_xyr(fp)
        theta = math.radians(orot)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for poly in tagged(fp, "fp_poly"):
            layer = first(poly, "layer")
            if not (layer and layer[1] == "F.SilkS"):
                continue
            pts = []
            for xy in tagged(first(poly, "pts"), "xy"):
                lx, ly = float(xy[1]), float(xy[2])
                # KiCad rotates footprints clockwise for positive angles.
                bx = ox + lx * cos_t + ly * sin_t
                by = oy - lx * sin_t + ly * cos_t
                pts.append((bx, by))
            logo_polys.append(pts)

    return outline, holes, silk_lines, silk_rings, texts, logo_polys


def knob(x, y):
    """A skirted knob seen from the front, pointer at 12 o'clock."""
    return [f"<circle cx='{x}' cy='{y}' r='6.3' fill='#fff' stroke='{INK}' stroke-width='0.35'/>",
            f"<circle cx='{x}' cy='{y}' r='4.6' fill='#fff' stroke='{INK}' stroke-width='0.25'/>",
            f"<line x1='{x}' y1='{y - 6.3}' x2='{x}' y2='{y - 3}' stroke='{INK}' stroke-width='0.6' "
            f"stroke-linecap='round'/>"]


def panel_body(outline, holes, silk_lines, silk_rings, texts, logo_polys):
    """SVG elements for the faceplate itself, in board coordinates (mm)."""
    x0, y0, x1, y1 = outline
    el = [f"<rect x='{x0}' y='{y0}' width='{x1 - x0}' height='{y1 - y0}' rx='0.4' "
          f"fill='#fff' stroke='{INK}' stroke-width='0.3'/>"]
    for pts in logo_polys:
        el.append(f"<polygon points='{' '.join(f'{x},{y}' for x, y in pts)}' fill='{INK}'/>")
    for cx, cy, r, w in silk_rings:
        el.append(f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{INK}' stroke-width='{w}'/>")
    for (xa, ya, xb, yb), w in silk_lines:
        el.append(f"<line x1='{xa}' y1='{ya}' x2='{xb}' y2='{yb}' stroke='{INK}' "
                  f"stroke-width='{w}' stroke-linecap='square'/>")
    for t in texts:
        anchor = "start" if t["justify"] == "left" else "middle"
        rot = f" transform='rotate({-t['rot']} {t['x']} {t['y']})'" if t["rot"] else ""
        style = " font-style='italic'" if t["italic"] else ""
        el.append(f"<text x='{t['x']}' y='{t['y']}' {FONT} font-size='{t['size'] * 1.15}'{style} "
                  f"fill='{INK}' text-anchor='{anchor}' dominant-baseline='central'{rot}>"
                  f"{t['text']}</text>")
    for x, y, d in holes:
        if d == JACK:
            # Knurled jack nut with the socket opening.
            el.append(f"<circle cx='{x}' cy='{y}' r='3.9' fill='#fff' stroke='{INK}' stroke-width='0.35'/>")
            el.append(f"<circle cx='{x}' cy='{y}' r='3.1' fill='none' stroke='{INK}' stroke-width='0.2'/>")
            el.append(f"<circle cx='{x}' cy='{y}' r='1.8' fill='{INK}'/>")
        elif d == POT:
            el += knob(x, y)
        else:
            el.append(f"<circle cx='{x}' cy='{y}' r='{d / 2}' fill='#fff' stroke='{INK}' stroke-width='0.3'/>")
    return el


def svg(view, body, title):
    vx, vy, vw, vh = view
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='{vx} {vy} {vw} {vh}' "
            f"width='{vw * 4:.0f}' height='{vh * 4:.0f}'>\n<title>{title}</title>\n"
            f"<rect x='{vx}' y='{vy}' width='{vw}' height='{vh}' fill='#fff'/>\n"
            + "\n".join(body) + "\n</svg>\n")


def controls(holes):
    """(knob, input, output) y positions for each channel, top to bottom."""
    jacks = sorted(y for _, y, d in holes if d == JACK)
    pots = sorted(y for _, y, d in holes if d == POT)
    return [(pots[0], jacks[0], jacks[1]), (pots[1], jacks[2], jacks[3])]


def annotated(outline, holes, *silk):
    x0, y0, x1, y1 = outline
    body = panel_body(outline, holes, *silk)
    lx = x1 + 5  # leader lines end here
    tx = lx + 2  # labels start here

    def label(y, title, sub, from_x):
        return [f"<line x1='{from_x}' y1='{y}' x2='{lx}' y2='{y}' stroke='{DIM}' stroke-width='0.3'/>",
                f"<circle cx='{from_x}' cy='{y}' r='0.5' fill='{DIM}'/>",
                f"<text x='{tx}' y='{y - 1.6}' {FONT} font-size='3.2' font-weight='bold' fill='{INK}' "
                f"dominant-baseline='central'>{title}</text>",
                f"<text x='{tx}' y='{y + 2.4}' {FONT} font-size='2.4' fill='{DIM}' "
                f"dominant-baseline='central'>{sub}</text>"]

    (k1, i1, o1), (k2, i2, o2) = controls(holes)
    body += label(k1, "Level 1", "turn right for more", x1 - 2)
    body += label(i1, "In 1", "no ring: input", x1 - 3)
    body += label(o1, "Out 1", "bold ring = output", x1 - 3)
    body += label(k2, "Level 2", "turn right for more", x1 - 2)
    body += label(i2, "In 2", "unplugged: copies In 1", x1 - 3)
    body += label(o2, "Out 2", "bold ring = output", x1 - 3)
    pad = 4
    return svg((x0 - pad, y0 - pad, (x1 - x0) + 44 + pad, (y1 - y0) + 2 * pad), body,
               "Passive Attenuator front panel")


def plain(outline, holes, *silk):
    x0, y0, x1, y1 = outline
    pad = 1
    return svg((x0 - pad, y0 - pad, (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad), panel_body(outline, holes, *silk),
               "Passive Attenuator front panel")


def main():
    data = parse(PCB)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "panel.svg").write_text(annotated(*data))
    (OUT / "panel-plain.svg").write_text(plain(*data))
    print("wrote", OUT / "panel.svg", "and", OUT / "panel-plain.svg")


if __name__ == "__main__":
    main()
