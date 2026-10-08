<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo-light.png">
  <img src="docs/images/logo-dark.png" alt="Schenktronics" width="320">
</picture>

# Levels

A 3HP Eurorack dual passive attenuator from **Schenktronics**. It has two channels, each with an input, an output and a level knob. The second input is normalled to the first, so one signal can be sent out at two different levels. It needs no power.

<img src="docs/images/front.jpg" alt="Levels front panel" width="120">

## Features

- 3HP Eurorack, 15 mm deep, and it needs no power
- Two channels, each turning a signal down from full level to off
- In 2 is normalled to In 1: one input, two outputs at independent levels
- Works on audio, CV, gates and bipolar signals
- The whole kit is through-hole, with 22 solder joints

## Documentation

| Document | For | PDF |
|----------|-----|-----|
| [User Manual](docs/manual.md) | Using the module | [PDF](docs/pdf/levels-manual.pdf) |
| [Assembly Guide](docs/assembly-guide.md) | Building the kit | [PDF](docs/pdf/levels-assembly-guide.pdf) |
| [Bill of Materials](docs/BOM.md) ([CSV](docs/BOM.csv)) | Parts and sourcing | |

## Repository layout

```
hardware/
  levels/                      Main PCB (KiCad 5.1 schematic, KiCad 10 PCB)
    Levels.sch                   Schematic
    Levels.kicad_pcb             PCB layout
    Levels.step                  3D model
    BOM.ods                      Original BOM spreadsheet
  panel/                       Faceplate (KiCad 10, made as an aluminium PCB)
    LevelsFaceplate.kicad_pcb    Faceplate layout
manufacturing/
  levels/                      Gerbers and drill files for the main PCB
  panel/                       Gerbers, drill files and the panel drawing (.dxf)
docs/                         Manual, assembly guide, BOM, images
  drawings/                     Scripts that generate the drawings
  pdf/                          PDF versions and their build settings
```

## Fabrication

| Board | Size | Layers | Thickness | Notes |
|-------|------|--------|-----------|-------|
| Main PCB | 15 × 100 mm | 2 | 1.6 mm | Standard green is fine |
| Faceplate | 15 × 128.5 mm | 1 | 1.6 mm | Aluminium PCB, white solder mask, black silkscreen. Only the front copper layer is used, so FR4 works too. |

Upload the matching `*Gerbers.zip` to any common PCB fab.

## License

This hardware design and its documentation are licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). See [LICENSE](LICENSE).

The Schenktronics name and logo are trademarks of Nathan Schenk and are not covered by the CC BY-NC-SA 4.0 license.

## Links

- Tindie: <https://www.tindie.com/products/schenktronics/passive-attenuator/>
- ModularGrid: <https://modulargrid.net/e/schenktronics-atten>
- Build video: <https://www.youtube.com/watch?v=RKkGsIigaSM>
- Website: <https://schenktronics.com>
