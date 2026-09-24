#!/usr/bin/env python3
"""Generate faceplate line drawings from the KiCad faceplate file.

Writes docs/images/panel.svg (annotated front view) and docs/images/panel-plain.svg
(the panel alone, for packaging labels where small captions would be lost).
Run from anywhere: python3 docs/drawings/make_panel_svg.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "PassiveAttenuatorFaceplate" / "PassiveAttenuatorFaceplate.kicad_pcb"
OUT = ROOT / "docs" / "images"

INK = "#1a1a1a"
DIM = "#555"
RED = "#d9302c"
FONT = "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'"

# Drill sizes (mm) that identify each kind of hole.
JACK, POT = 6.0, 7.0


def parse(path):
    s = path.read_text()
    edges = [tuple(map(float, m)) for m in re.findall(
        r"\(gr_line \(start ([\d.]+) ([\d.]+)\) \(end ([\d.]+) ([\d.]+)\) \(layer Edge\.Cuts\)", s)]
    xs = [v for e in edges for v in (e[0], e[2])]
    ys = [v for e in edges for v in (e[1], e[3])]
    outline = (min(xs), min(ys), max(xs), max(ys))

    holes = []
    for m in re.finditer(r"\(module Mounting_Holes:\S+.*?\(at ([\d.]+) ([\d.]+)(?: [-\d.]+)?\).*?\(drill ([\d.]+)\)",
                         s, re.S):
        holes.append((float(m[1]), float(m[2]), float(m[3])))

    silk_lines = [(tuple(map(float, m[:4])), float(m[4])) for m in re.findall(
        r"\(gr_line \(start ([\d.]+) ([\d.]+)\) \(end ([\d.]+) ([\d.]+)\) \(layer F\.SilkS\) \(width ([\d.]+)\)", s)]
    # Filled silkscreen areas (the solid boxes behind the output jacks).
    silk_fills = []
    for z in re.finditer(r"\(zone [^\n]*\(layer F\.SilkS\).*?\(polygon\s*\(pts(.*?)\(filled_polygon", s, re.S):
        silk_fills.append([tuple(map(float, p)) for p in re.findall(r"\(xy ([\d.]+) ([\d.]+)\)", z[1])])
    texts = []
    for m in re.finditer(r"\(gr_text (\S+) \(at ([\d.]+) ([\d.]+)(?: ([\d.]+))?\) \(layer F\.SilkS\)"
                         r"(.*?)\n  \)", s, re.S):
        size = re.search(r"\(size ([\d.]+)", m[5])
        justify = re.search(r"\(justify (\w+)", m[5])
        texts.append(dict(text=m[1], x=float(m[2]), y=float(m[3]), rot=float(m[4] or 0),
                          size=float(size[1]), justify=justify and justify[1], italic="italic" in m[5]))
    return outline, holes, silk_lines, silk_fills, texts


def knob(x, y):
    """A skirted knob seen from the front, pointer at 12 o'clock."""
    return [f"<circle cx='{x}' cy='{y}' r='6.3' fill='#fff' stroke='{INK}' stroke-width='0.35'/>",
            f"<circle cx='{x}' cy='{y}' r='4.6' fill='#fff' stroke='{INK}' stroke-width='0.25'/>",
            f"<line x1='{x}' y1='{y - 6.3}' x2='{x}' y2='{y - 3}' stroke='{INK}' stroke-width='0.6' "
            f"stroke-linecap='round'/>"]


def panel_body(outline, holes, silk_lines, silk_fills, texts):
    """SVG elements for the faceplate itself, in board coordinates (mm)."""
    x0, y0, x1, y1 = outline
    el = [f"<rect x='{x0}' y='{y0}' width='{x1 - x0}' height='{y1 - y0}' rx='0.4' "
          f"fill='#fff' stroke='{INK}' stroke-width='0.3'/>"]
    for pts in silk_fills:
        el.append(f"<polygon points='{' '.join(f'{x},{y}' for x, y in pts)}' fill='{INK}'/>")
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
    body += label(i1, "In 1", "outlined box = input", x1 - 3)
    body += label(o1, "Out 1", "solid box = output", x1 - 3)
    body += label(k2, "Level 2", "turn right for more", x1 - 2)
    body += label(i2, "In 2", "unplugged: copies In 1", x1 - 3)
    body += label(o2, "Out 2", "solid box = output", x1 - 3)
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
