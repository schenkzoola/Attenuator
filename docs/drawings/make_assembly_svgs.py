#!/usr/bin/env python3
"""Generate the assembly-guide drawings.

The front and back board views come from the KiCad PCB file. The side views
are diagrams, not to scale, positioned using the same part locations.

Writes docs/images/assembly-*.svg.
Run from anywhere: python3 docs/drawings/make_assembly_svgs.py
"""
import math
import re
from pathlib import Path

from make_panel_svg import FONT, INK, RED, svg

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "PassiveAttenuator" / "PassiveAttenuator.kicad_pcb"
OUT = ROOT / "docs" / "images"

GREY = "#888"
LIGHT = "#f1f1f1"
PAD = "#d6d6d6"
TINT = "#fbe3e2"


# ---------------------------------------------------------------- parsing

def parse(path):
    s = path.read_text()
    edges = [tuple(map(float, m)) for m in re.findall(
        r"\(gr_line \(start ([\d.]+) ([\d.]+)\) \(end ([\d.]+) ([\d.]+)\) \(layer Edge\.Cuts\)", s)]
    xs = [v for e in edges for v in (e[0], e[2])]
    ys = [v for e in edges for v in (e[1], e[3])]
    outline = (min(xs), min(ys), max(xs), max(ys))

    parts = []
    for block in re.findall(r"\n  \(module .*?\n  \)", s, re.S):
        at = re.search(r"\n    \(at ([\d.]+) ([\d.]+)(?: ([\d.-]+))?\)", block)
        mx, my = float(at[1]), float(at[2])
        a = math.radians(float(at[3] or 0))

        def place(x, y):
            # KiCad rotates footprints counter-clockwise on a y-down board.
            return (mx + x * math.cos(a) + y * math.sin(a), my - x * math.sin(a) + y * math.cos(a))

        ref = re.search(r"fp_text reference (\S+) \(at ([\d.-]+) ([\d.-]+)", block)
        part = dict(ref=ref[1], at=(mx, my), label_at=place(float(ref[2]), float(ref[3])), lines=[], circles=[], pads=[])
        for m in re.findall(r"\(fp_line \(start ([\d.-]+) ([\d.-]+)\) \(end ([\d.-]+) ([\d.-]+)\) \(layer F\.SilkS\)", block):
            x1, y1, x2, y2 = map(float, m)
            part["lines"].append((*place(x1, y1), *place(x2, y2)))
        for m in re.findall(r"\(fp_circle \(center ([\d.-]+) ([\d.-]+)\) \(end ([\d.-]+) ([\d.-]+)\) \(layer F\.SilkS\)", block):
            cx, cy, ex, ey = map(float, m)
            part["circles"].append((*place(cx, cy), math.hypot(ex - cx, ey - cy)))
        for m in re.finditer(r"\(pad (\S+) (\S+) (\S+) \(at ([\d.-]+) ([\d.-]+)(?: ([\d.-]+))?\) \(size ([\d.]+) ([\d.]+)\)"
                             r"(?: \(drill (?:oval )?([\d.]+)(?: ([\d.]+))?\))?", block):
            name, kind, shape = m[1].strip('"'), m[2], m[3]
            px, py = place(float(m[4]), float(m[5]))
            w, h = float(m[7]), float(m[8])
            dw = float(m[9] or 0)
            dh = float(m[10] or m[9] or 0)
            if m[6] and float(m[6]) % 180 == 90:
                # Pad angles in KiCad 5 are absolute.
                w, h, dw, dh = h, w, dh, dw
            part["pads"].append(dict(name=name, npth=kind == "np_thru_hole", shape=shape,
                                     x=px, y=py, w=w, h=h, dw=dw, dh=dh))
        parts.append(part)
    return outline, parts


# ------------------------------------------------------------- board views

class BoardView:
    """Draws the board lying horizontally, RV1 on the left.

    front=True looks at the component side; front=False looks at the solder
    side (the board flipped over its long edge).
    """

    def __init__(self, outline, ox, oy, front):
        self.x0, self.y0, self.x1, self.y1 = outline
        self.ox, self.oy, self.front = ox, oy, front

    def pt(self, x, y):
        u = y - self.y0
        v = (self.x1 - x) if self.front else (x - self.x0)
        return self.ox + u, self.oy + v

    def size(self, w, h):
        return h, w  # Board x runs vertically in the drawing.

    def board(self):
        w, h = self.y1 - self.y0, self.x1 - self.x0
        return [f"<rect x='{self.ox}' y='{self.oy}' width='{w}' height='{h}' rx='0.6' "
                f"fill='{LIGHT}' stroke='{INK}' stroke-width='0.35'/>"]

    def pad(self, p, fill=PAD, stroke=GREY):
        cx, cy = self.pt(p["x"], p["y"])
        w, h = self.size(p["w"], p["h"])
        out = []
        if not p["npth"]:
            if p["shape"] == "circle":
                out.append(f"<circle cx='{cx:.3f}' cy='{cy:.3f}' r='{w / 2}' fill='{fill}' stroke='{stroke}' stroke-width='0.15'/>")
            else:
                r = min(w, h) / 2 if p["shape"] == "oval" else 0.15
                out.append(f"<rect x='{cx - w / 2:.3f}' y='{cy - h / 2:.3f}' width='{w}' height='{h}' rx='{r}' "
                           f"fill='{fill}' stroke='{stroke}' stroke-width='0.15'/>")
        dw, dh = self.size(p["dw"], p["dh"])
        if dw:
            out.append(f"<rect x='{cx - dw / 2:.3f}' y='{cy - dh / 2:.3f}' width='{dw}' height='{dh}' "
                       f"rx='{min(dw, dh) / 2}' fill='#fff' stroke='{GREY if p['npth'] else 'none'}' stroke-width='0.15'/>")
        return out

    def silk(self, part, color=GREY, width=0.2):
        out = []
        for x1, y1, x2, y2 in part["lines"]:
            a, b = self.pt(x1, y1), self.pt(x2, y2)
            out.append(f"<line x1='{a[0]:.3f}' y1='{a[1]:.3f}' x2='{b[0]:.3f}' y2='{b[1]:.3f}' "
                       f"stroke='{color}' stroke-width='{width}'/>")
        for cx, cy, r in part["circles"]:
            c = self.pt(cx, cy)
            out.append(f"<circle cx='{c[0]:.3f}' cy='{c[1]:.3f}' r='{r}' fill='none' stroke='{color}' stroke-width='{width}'/>")
        return out

    def ref(self, part, color=GREY):
        x, y = self.pt(*part["label_at"])
        return [f"<text x='{x:.3f}' y='{y:.3f}' {FONT} font-size='1.6' fill='{color}' "
                f"text-anchor='middle' dominant-baseline='central'>{part['ref']}</text>"]


def text(x, y, s, size=2.6, weight="normal", color=INK, anchor="start"):
    return (f"<text x='{x:.2f}' y='{y:.2f}' {FONT} font-size='{size}' font-weight='{weight}' fill='{color}' "
            f"text-anchor='{anchor}' dominant-baseline='central'>{s}</text>")


def arrow_defs():
    return (f"<defs><marker id='arr' viewBox='0 0 10 10' refX='8' refY='5' markerWidth='5' markerHeight='5' "
            f"orient='auto-start-reverse'><path d='M0 1 L10 5 L0 9 z' fill='{INK}'/></marker></defs>")


def arrow(x1, y1, x2, y2, color=INK, width=0.35):
    return (f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='{color}' "
            f"stroke-width='{width}' marker-end='url(#arr)'/>")


def view_title(x, y, title, sub):
    return [text(x, y, title, 3, "bold"), text(x, y + 3.6, sub, 2.2, color=GREY)]


def end_labels(view, y):
    w = view.y1 - view.y0
    return [text(view.ox, y, "RV1 end (top of panel)", 2, color=GREY),
            text(view.ox + w, y, "J4 end", 2, color=GREY, anchor="end")]


# ----------------------------------------------------------------- figures

OFFSET = -12.5  # faceplate y = PCB y - 12.5 (from the two KiCad files)
PANEL_TOP, PANEL_BOT = 23.25, 151.75  # faceplate outline, in faceplate coordinates
PANEL_SCREWS = (26.25, 148.75)


def pots(parts):
    return [p for p in parts if p["ref"].startswith("RV")]


def jacks(parts):
    return [p for p in parts if p["ref"].startswith("J")]


def shaft(pot):
    """A pot's shaft sits midway between its two mounting lugs."""
    lugs = [p for p in pot["pads"] if not p["name"]]
    return ((lugs[0]["x"] + lugs[1]["x"]) / 2, (lugs[0]["y"] + lugs[1]["y"]) / 2)


def jack_hole(jack):
    return next(((p["x"], p["y"]) for p in jack["pads"] if p["npth"]))


def fig_parts(outline, parts):
    """Step 1: pots and jacks go in from the front, not soldered yet."""
    h = outline[2] - outline[0]
    v = BoardView(outline, 0, 8, front=True)
    body = view_title(0, 2.5, "Front (part side)", "Fit RV1, RV2 and J1–J4. Don't solder yet.")
    body += v.board()
    for p in parts:
        for pad in p["pads"]:
            body += v.pad(pad)
        body += v.silk(p, color=RED, width=0.3) + v.ref(p, color=RED)
    for p in pots(parts):
        x, y = v.pt(*shaft(p))
        body.append(f"<circle cx='{x:.2f}' cy='{y:.2f}' r='3.5' fill='{TINT}' stroke='{RED}' stroke-width='0.35'/>")
    body += end_labels(v, 8 + h + 2.2)
    return svg((-3, -3, 106, h + 16), body, "Step 1: fit the pots and jacks")


def fig_faceplate(outline, parts):
    """Step 2: exploded side view of pots, jacks, faceplate and nuts."""
    x0, y0, x1, y1 = outline
    jack_ys = sorted(jack_hole(j)[1] for j in jacks(parts))
    pot_ys = sorted(shaft(p)[1] for p in pots(parts))
    panel_top, panel_bot = PANEL_TOP - OFFSET, PANEL_BOT - OFFSET
    u = lambda y: y - panel_top + 2  # drawing x for a board y

    pcb_y, body_h, bush_h = 60, 9, 4.5
    body_top = pcb_y - body_h
    panel_y = body_top - 16  # exploded gap
    nut_y = panel_y - 9

    body = [arrow_defs()]
    body.append(f"<rect x='{u(y0)}' y='{pcb_y}' width='{y1 - y0}' height='1.6' fill='{LIGHT}' stroke='{INK}' stroke-width='0.3'/>")
    legs = lambda x, dxs: [f"<line x1='{x + dx}' y1='{pcb_y + 1.6}' x2='{x + dx}' y2='{pcb_y + 3.6}' "
                           f"stroke='{INK}' stroke-width='0.35'/>" for dx in dxs]
    thread = lambda x, w, top: [f"<line x1='{x - w}' y1='{top + dy}' x2='{x + w}' y2='{top + dy}' "
                                f"stroke='{GREY}' stroke-width='0.15'/>" for dy in (1.2, 2.4, 3.6)]
    for y in jack_ys:
        x = u(y)
        body.append(f"<rect x='{x - 4.5}' y='{body_top}' width='9' height='{body_h}' rx='0.4' fill='#fff' stroke='{INK}' stroke-width='0.35'/>")
        body.append(f"<rect x='{x - 3}' y='{body_top - bush_h}' width='6' height='{bush_h}' fill='#fff' stroke='{INK}' stroke-width='0.35'/>")
        body += thread(x, 3, body_top - bush_h) + legs(x, (-3, 3))
    for y in pot_ys:
        x = u(y)
        body.append(f"<rect x='{x - 5}' y='{body_top}' width='10' height='{body_h}' rx='0.4' fill='#fff' stroke='{INK}' stroke-width='0.35'/>")
        body.append(f"<rect x='{x - 3.5}' y='{body_top - bush_h}' width='7' height='{bush_h}' fill='#fff' stroke='{INK}' stroke-width='0.35'/>")
        body.append(f"<rect x='{x - 3}' y='{body_top - bush_h - 12}' width='6' height='12' fill='#fff' stroke='{RED}' stroke-width='0.35'/>")
        body += thread(x, 3.5, body_top - bush_h) + legs(x, (-4.75, -2.5, 0, 4.75))

    # Faceplate, cut away at each hole.
    holes = sorted([(y, 6.0) for y in jack_ys] + [(y, 7.0) for y in pot_ys] +
                   [(s - OFFSET, 3.2) for s in PANEL_SCREWS])
    edges = [u(panel_top)]
    for y, d in holes:
        edges += [u(y) - d / 2, u(y) + d / 2]
    edges.append(u(panel_bot))
    for a, b in zip(edges[::2], edges[1::2]):
        body.append(f"<rect x='{a:.2f}' y='{panel_y}' width='{b - a:.2f}' height='1.6' fill='{INK}'/>")

    # Nuts.
    for y in jack_ys + pot_ys:
        x = u(y)
        w = 9 if y in pot_ys else 8
        body.append(f"<rect x='{x - w / 2}' y='{nut_y}' width='{w}' height='2.2' rx='0.3' fill='#fff' stroke='{INK}' stroke-width='0.35'/>")
        for dx in (-2.5, -0.8, 0.8, 2.5):
            body.append(f"<line x1='{x + dx}' y1='{nut_y}' x2='{x + dx}' y2='{nut_y + 2.2}' stroke='{GREY}' stroke-width='0.15'/>")

    # Arrows and labels.
    for y in (jack_ys[0], jack_ys[-1]):
        body.append(arrow(u(y), nut_y + 3, u(y), panel_y - 0.8, width=0.3))
        body.append(arrow(u(y), panel_y + 2.8, u(y), body_top - bush_h - 0.8, width=0.3))
    lx = u(panel_bot) + 3
    body.append(text(lx, nut_y + 1.1, "Nuts", 2.6, "bold"))
    body.append(text(lx, nut_y + 4.3, "finger-tight first", 2.2, color=GREY))
    body.append(text(lx, panel_y + 0.8, "Faceplate", 2.6, "bold"))
    body.append(text(lx, panel_y + 4, "“Atten.” end over RV1", 2.2, color=GREY))
    body.append(text(lx, body_top + 3, "Pots and jacks", 2.6, "bold"))
    body.append(text(lx, body_top + 6.2, "not soldered yet", 2.2, color=GREY))
    body.append(text(lx, pcb_y + 0.8, "PCB", 2.6, "bold"))
    body.append(text(u(pot_ys[1]), pcb_y + 7.5, "Straighten the pot shafts in their holes,", 2.6, "bold",
                     color=RED, anchor="middle"))
    body.append(text(u(pot_ys[1]), pcb_y + 10.7, "then tighten the nuts", 2.2, color=GREY, anchor="middle"))
    body.append(text(u(y0), pcb_y + 7.5, "RV1 end", 2, color=GREY))
    body.append(text(u(y1), pcb_y + 7.5, "J4 end", 2, color=GREY, anchor="end"))
    body.append(text(u(panel_top), pcb_y + 15, "Side view, not to scale vertically", 2, color=GREY))
    return svg((u(panel_top) - 2, nut_y - 4, (panel_bot - panel_top) + 38, pcb_y - nut_y + 22), body,
               "Step 2: fit the faceplate")


def fig_solder(outline, parts):
    """Step 3: back view. Tack one leg of each part, then the rest."""
    h = outline[2] - outline[0]
    v = BoardView(outline, 0, 8, front=False)
    body = [text(0, 2.5, "Back (solder side)", 3, "bold")]
    body += v.board()
    for p in parts:
        tack = "S" if p["ref"].startswith("J") else "2"
        for pad in p["pads"]:
            if pad["npth"]:
                body += v.pad(pad)
            elif pad["name"] == tack:
                body += v.pad(pad, fill=RED, stroke=RED)
            else:
                body += v.pad(pad, fill="#fff", stroke=RED)
    body += end_labels(v, 8 + h + 2.2)
    ky = 8 + h + 8
    body += [f"<rect x='0' y='{ky - 1.2}' width='2.4' height='2.4' rx='0.2' fill='{RED}'/>",
             text(3.6, ky, "1. Tack these first: one leg per part (6 joints)", 2.4),
             f"<rect x='0' y='{ky + 3.3}' width='2.4' height='2.4' rx='1.2' fill='#fff' stroke='{RED}' stroke-width='0.3'/>",
             text(3.6, ky + 4.5, "2. Then the rest, including the 4 large pot lugs (16 joints)", 2.4)]
    return svg((-3, -1, 106, ky + 9), body, "Step 3: solder the pots and jacks")


def main():
    outline, parts = parse(PCB)
    OUT.mkdir(parents=True, exist_ok=True)
    figs = {
        "assembly-1-parts.svg": fig_parts(outline, parts),
        "assembly-2-faceplate.svg": fig_faceplate(outline, parts),
        "assembly-3-solder.svg": fig_solder(outline, parts),
    }
    for name, content in figs.items():
        (OUT / name).write_text(content)
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
