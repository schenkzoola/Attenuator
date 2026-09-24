# Bill of Materials — Passive Attenuator v1.0

A machine-readable copy is in [BOM.csv](BOM.csv). The original spreadsheet is [PassiveAttenuator/BOM.ods](../PassiveAttenuator/BOM.ods).

| Qty | Reference | Part | Manufacturer / Part No. | Notes |
|----:|-----------|------|--------------------------|-------|
| 4 | J1–J4 | 3.5 mm mono switched jack, vertical PCB mount, with nut | QingPu WQP-PJ398SM or WQP518MA, or equivalent. Either one works. | [Datasheet / product page](http://www.qingpu-electronics.com/en/products/WQP-PJ398SM-362.html). The switched (normalling) contact is used on J3 (In 2) only, so J3 must be a switched jack. |
| 2 | RV1, RV2 | Potentiometer, 100 kΩ linear, 9 mm, vertical PCB mount with board-lock lugs, 15 mm D shaft, with nut | TT Electronics/BI P0915N-FC15BR100K, or equivalent | [Digi-Key 987-1709-ND](https://www.digikey.com/product-detail/en/tt-electronics-bi/P0915N-FC15BR100K/987-1709-ND/5957453), [datasheet (P09 series)](https://www.ttelectronics.com/TTElectronics/media/ProductFiles/Datasheet/P09x.pdf). No center detent. An equivalent must fit the 9 mm footprint (3 pins in a row, 2 mounting lugs), have a threaded bushing that fits the 7 mm panel hole, and a 6 mm shaft that fits the knob. |
| 2 | — | Knob, skirted, 15 mm | Davies Molding 1227-J, or equivalent | [Digi-Key 1722-1247-ND](https://www.digikey.com/product-detail/en/davies-molding-llc/1227-J/1722-1247-ND/6566470). The skirt hides the pot nut. An equivalent must fit the pot shaft and cover the nut. |
| 1 | — | Main PCB, 15 × 100 mm, 2-layer, 1.6 mm FR4 | Schenktronics | Gerbers: [PassiveAttenuatorGerbers.zip](../PassiveAttenuator/PassiveAttenuatorGerbers.zip) |
| 1 | — | Faceplate, 3HP (15 × 128.5 mm), 1.6 mm FR4 PCB | Schenktronics | Gerbers: [PassiveAttenuatorFaceplateGerbers.zip](../PassiveAttenuatorFaceplate/PassiveAttenuatorFaceplateGerbers.zip) |

## Not included

| Qty | Part | Notes |
|----:|------|-------|
| 2 | M3 rack screws | Supplied with most Eurorack cases. |

No power cable is needed. The module is passive.
