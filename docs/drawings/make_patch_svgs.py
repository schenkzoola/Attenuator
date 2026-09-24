#!/usr/bin/env python3
"""Generate the patch-example drawings for the user manual.

Each example draws the panel (from the KiCad faceplate file) with source
modules on the left, destination modules on the right, and patch cables.

Writes docs/images/patch-*.svg.
Run from anywhere: python3 docs/drawings/make_patch_svgs.py
"""
from pathlib import Path

from make_panel_svg import FONT, INK, PCB, RED, controls, panel_body, parse, svg

OUT = Path(__file__).resolve().parents[2] / "docs" / "images"

GREY = "#777"
BLUE = "#2a6fb0"  # second signal, for patches with two
BOX_W, BOX_H = 38, 11
GAP = 22  # space between the panel and the module boxes


def text(x, y, s, size=2.6, weight="normal", color=INK, anchor="middle"):
    return (f"<text x='{x:.2f}' y='{y:.2f}' {FONT} font-size='{size}' font-weight='{weight}' fill='{color}' "
            f"text-anchor='{anchor}' dominant-baseline='central'>{s}</text>")


def marker(color, name):
    return (f"<marker id='{name}' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='4' markerHeight='4' "
            f"orient='auto'><path d='M0 1 L10 5 L0 9 z' fill='{color}'/></marker>")


class Patch:
    def __init__(self, data):
        self.data = data
        outline, holes = data[0], data[1]
        self.x0, self.y0, self.x1, self.y1 = outline
        (k1, i1, o1), (k2, i2, o2) = controls(holes)
        cx = (self.x0 + self.x1) / 2
        self.jacks = {"In 1": (cx, i1), "Out 1": (cx, o1), "In 2": (cx, i2), "Out 2": (cx, o2)}
        self.knobs = {"Level 1": k1, "Level 2": k2}
        self.cables, self.boxes, self.plugs, self.notes = [], [], [], []

    def jack(self, name):
        return self.jacks[name]

    def box(self, side, y, title, sub):
        x = self.x0 - GAP - BOX_W if side == "left" else self.x1 + GAP
        self.boxes += [f"<rect x='{x}' y='{y - BOX_H / 2}' width='{BOX_W}' height='{BOX_H}' rx='1.2' "
                       f"fill='#fff' stroke='{INK}' stroke-width='0.35'/>",
                       text(x + BOX_W / 2, y - 2, title, 3.4, "bold"),
                       text(x + BOX_W / 2, y + 2.7, sub, 2.7, color=GREY)]
        return (x + BOX_W, y) if side == "left" else (x, y)

    def source(self, jack, title, sub, color=RED):
        jx, jy = self.jack(jack)
        bx, by = self.box("left", jy, title, sub)
        self.cable((bx, by), (jx, jy), color, into_jack=True)

    def dest(self, jack, title, sub, color=RED):
        jx, jy = self.jack(jack)
        bx, by = self.box("right", jy, title, sub)
        self.cable((jx, jy), (bx, by), color, into_jack=False)

    def cable(self, a, b, color, into_jack):
        (ax, ay), (bx, by) = a, b
        k = abs(bx - ax) * 0.5
        mid = "r" if color == RED else "b"
        end = "" if into_jack else f" marker-end='url(#{mid})'"
        self.cables.append(f"<path d='M{ax:.2f} {ay:.2f} C{ax + k:.2f} {ay:.2f} {bx - k:.2f} {by:.2f} {bx:.2f} {by:.2f}' "
                           f"fill='none' stroke='{color}' stroke-width='0.9' stroke-linecap='round'{end}/>")
        jx, jy = b if into_jack else a
        self.plugs.append(f"<circle cx='{jx}' cy='{jy}' r='2.3' fill='{color}' stroke='{INK}' stroke-width='0.3'/>")

    def note(self, target, label, sub, side="left", color=RED):
        """A note beside a knob ("Level 1") or an unplugged jack ("In 2")."""
        y = self.knobs[target] if target in self.knobs else self.jacks[target][1]
        x, anchor = (self.x0 - 3, "end") if side == "left" else (self.x1 + 3, "start")
        self.notes += [text(x, y - 1.8, label, 3.2, "bold", color=color, anchor=anchor),
                       text(x, y + 2.4, sub, 2.7, color=GREY, anchor=anchor)]

    def render(self, title):
        body = [f"<defs>{marker(RED, 'r')}{marker(BLUE, 'b')}</defs>"]
        body += panel_body(*self.data)
        body += self.cables + self.plugs + self.boxes + self.notes
        left = self.x0 - GAP - BOX_W - 3
        width = (self.x1 + GAP + BOX_W + 3) - left
        return svg((left, self.y0 - 3, width, (self.y1 - self.y0) + 6), body, title)


def tame(data):
    p = Patch(data)
    p.source("In 1", "LFO", "out")
    p.dest("Out 1", "Filter", "cutoff CV in")
    p.note("Level 1", "Level 1", "sets the depth")
    return p.render("Patch example: set the depth of an LFO")


def two_depths(data):
    p = Patch(data)
    p.source("In 1", "LFO", "out")
    p.dest("Out 1", "Filter", "cutoff CV in")
    p.dest("Out 2", "VCO", "pulse width CV in")
    p.note("In 2", "In 2 empty", "copies In 1")
    return p.render("Patch example: one LFO at two depths")


def separate(data):
    p = Patch(data)
    p.source("In 1", "Envelope", "out", color=RED)
    p.dest("Out 1", "VCA", "CV in", color=RED)
    p.source("In 2", "VCO", "audio out", color=BLUE)
    p.dest("Out 2", "Mixer", "channel in", color=BLUE)
    return p.render("Patch example: two separate attenuators")


def main():
    data = parse(PCB)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fig in (("patch-1-depth.svg", tame), ("patch-2-two-depths.svg", two_depths),
                      ("patch-3-separate.svg", separate)):
        (OUT / name).write_text(fig(data))
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
