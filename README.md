# mw-cart
MegaWiFi Cartridge

> **This is the MegaWiFi Rev.C fork** of [doragasu/mw-cart](https://gitlab.com/doragasu/mw-cart).
> Everything below the "Rev.C" section is doragasu's original README.

## Rev.C (this fork)

**What changed (2026-10-06, jfryman):** the NXP **SC16C550BIBS** UART (U7) is out of stock
everywhere, so Rev.C replaces it with the pin-compatible **TI TL16C550DRHB** (VQFN-32, RHB):

| | Rev.B (upstream) | Rev.C |
|---|---|---|
| U7 UART | NXP SC16C550BIBS | TI TL16C550DRHB (LCSC C2653239) |
| Y1 crystal | 24 MHz | **20 MHz** (C252261) + R18 1 MΩ bias resistor |
| Cart ↔ ESP32 link | 1.5 Mbaud | **1.25 Mbaud** |
| RI pin | NC | tied to VCC |

The TI part is rated to 20 MHz at 3.3 V, so the UART link runs at 1.25 Mbaud. **Rev.C is not
compatible with existing MegaWiFi ROMs or firmware**: ROMs need `UART_CLK` 20 MHz in their
`16c550.h`, and the ESP32 needs the Rev.C firmware from
[jfryman/mw-fw-rtos](https://github.com/jfryman/mw-fw-rtos/releases). Title blocks and silkscreen
are marked Rev.C.

**Status:** 10 boards assembled by JLCPCB (2026-10). The first board passes the full bring-up
suite at 1.25 Mbaud, including the flat 8 MiB ROM map with a Mega-CD and 32X attached.

**In this repo, beyond upstream:**
- `bringup-rom/`: a standalone 68000 test ROM for new boards (UART, crystal, ESP32 link,
  flash address lines, the 8 MiB map), plus a MAME simulation and FlashKit MD helper scripts.
- `tools/`: kicad-cli build wrapper and the KiCad s-expression helpers used for the U7 swap.
  `tools/fetch-ext.sh` fetches the Espressif 3D models.
- `lode/`: design notes, decisions and bench results.

**Downloads** ([releases](https://github.com/jfryman/mw-cart/releases)): JLCPCB Gerber zip,
BOM and CPL, schematic and fab PDFs, and the bring-up ROM. Upstream's own Rev.B outputs are on
[GitLab](https://gitlab.com/doragasu/mw-cart). Their BOM lists the unobtainable SC16C550BIBS.

---

![mw-cart](/mw-cart.jpg)

This is the cartridge for the MegaWiFi project. It consists of a cartridge for the SEGA Genesis/Megadrive console, along with a WiFi interface, allowing brave programmers to implement games with online gaming, leaderboards, evil DLCs, etc.

This project was initially created for 1985alternativo, and to this day, as far as I know, only 1985 WorldCup game has used it to implement online play. Will you give it a try?

Have a look to the [github project page](https://gitlab.com/doragasu/mw) for more information.

## Cartridge specs

The current cartridge is based on an ESP32-C3 WiFi microcontroller, that has a good specs/price tradeoff. But bear in mind that if needed, it would be easy swapping it for other more powerful ESP32 chip, like for example the ESP32-S3. The current specs are:

* Up to 64 megabits (8 MiB) of flat ROM (no mapper needed!).
* Fast ESP32 to m68k UART bridge (1.5 Mbps baud rate with hardware flow control; 1.25 Mbps on Rev.C).
* 32-bit RISC-V CPU running at 160 MHz. Can be upgraded to dual core up to 240 MHz if needed.
* Additional 16 megabits (2 MiB) available of readable/writable memory (managed by the ESP32 and accessed through the UART bridge, could be upgraded to up to 14 MiB if needed!).
* 400 KiB of SRAM managed by the ESP32.
* 802.11bgn Wi-Fi (2.4 GHz band) with WPA3 support.
* Bluetooth Low Energy (BLE) support.
* USB port for ESP32 programming and debugging. Can be upgraded to work as general purpose USB host/device port.
* Connection to the cart audio input, so the chip could be used to produce additional sound (though there is no software support for this yet).

**Note**: The cartridge slashes the the usual 32 megabits maximum of ROM space by implementing a hack: it unmaps the MegaCD and uses its address space. This has the drawback that you cannot access the MegaCD when the hack is enabled. If you need to access the MegaCD, the hack can be disabled, but then the cart is limited to the usual 32 megabits of ROM.

## License
mw-cart is licensed under the [CERN OHL 1.2](http://www.ohwr.org/licenses/cern-ohl/v1.2) license. You are free to study, distribute and make modifications to the Documentation, under the aforementioned license terms.

## About CAD files
Electronic CAD design files are for KiCAD Open Source electronics design suite. Please install latest version along with KiCAD libraries to open the project. When opening schematic, KiCAD will most likely complain about missing library "doragasu". Despite this warning, the schematic should load nicely (using the cached libraries). To avoid this message, install [the missing library](https://github.com/doragasu/doragasu-kicad-lib) and make sure to configure it in the schematic editor.

## Board fabrication

You can go to [the package registry](https://gitlab.com/doragasu/mw-cart/-/packages) to download artifact packages with the fabrication files, including Gerbers, bill of materials, drawings, CPL file, etc. To get the PCB made, you sould have some knowledge about PCB manufacturing, but I will try to give some indications about how to get the boards made and assembled by JLCPCB.

### Manufacturing process example: JLCPCB

[JLCPCB](https://jlcpcb.com/) is a widely known Chinese PCB manufacturer, that can do PCB fabrication and assembly, including component procurement. They are fairly cheap for PCB prototypes and quality is pretty good for boards not having difficult components (such as BGAs with very fine pitch). One of the things that make them have quite competitive pricing, is that **they will only assemble components they have stocked**. Luckily they source components from [LCSC](https://www.lcsc.com/) (one of the biggest Chinese suppliers) and have a very wide catalog of components. But even with this wide catalog it is not uncommon that one or more of the components for your board are not available. In this case, they allow you to purchase the components through their platform, and once they receive them, they can be selected for assembly on your boards.

So roughly speaking, the procedure to order assembled PCBs on JLCPCB is as follows:

1. Get a quotation for PCB manufacturing and assembly.
2. If all components required for assembly are available, awesome, make the order and you have finished. Otherwise, purchase the components using their *Parts Manager*. Once purchased, stocked components usually take 2 or 3 weeks to be received by JLCPCB, and they will notify you via email.
3. Repeat step one, components you purchased through *Parts Manager* will be available for assembly on your boards.

Getting into the details, the procedure is:

1. Download the [PCB artifact package](https://gitlab.com/doragasu/mw-cart/-/packages) from the package registry.
2. Extract the package and locate the `Fab/Manufacturers/mega-wifi-JLCPCB.zip` file, that contains the Gerber files, the `Fab/Manufacturers/JLCPCB/mega-wifi_bom_jlc.csv` that has the BoM (Bill of Materials) and the `Fab/Manufacturers/JLCPCB/mega-wifi_cpl_jlc.csv` that has the CPL (Component Placement/Centroid) file. We will have to upload these files later.
3. Go to [JLCPCB](https://jlcpcb.com/) and log into your account. Then click *Order now* on the top right of the page.
4. Click *Add gerber file* and upload the `mega-wifi-JLCPCB.zip` file we located in step 2. When the files are processed, many board parameters will be populated. Most of the default values will be OK, but some changes are recommended. I will mark with an asterisk (\*) the parameters that should be changed from defaults, and will omit some parameters that should be clear enough (like PCB quantity, color, or dimensions that will be automatically obtained from Gerber files):

* Base material: FR-4
* Layers: 2
* PCB Thickness: 1.6
* Surface Finish: ENIG (\*)
* Outer Copper Weight: 1 oz
* Via Covering: Tented
* Min via hole size/diameter: 0.3mm
* Board Outline Tolerance: +- 0.2mm(Regular)
* Gold Fingers: Yes (\*)
* 30°finger chamfered: Yes (\*)
* Castellated Holes: No
* Edge Plating: No

5. If you want assembly, enable the *PCB Assembly* slider. All the default assembly parameters should be OK:

* PCBA Type: Standard
* Assembly Side: Top Side
* Edge Rails/Fiducials: Added by JLCPCB
* Parts Selection: By Customer

Advanced options defaults should also be OK.

6. Click "Next", you will be asked for confirmation about the side that will be assembled and the assembly quantity. Again, click "Next". Then you will be prompted for the BOM and CPL files. Upload the `mega-wifi_bom_jlc.csv` and `mega-wifi_cpl_jlc.csv` files we located in step 2. Then click "Process BOM & CPL".
7. You will be presented the table of components that will be assembled. If you are lucky, everything will be stocked so you can click "Next" and jump to step 12. Otherwise take note of the non stocked components (and I would also recommend taking note of stocked components having low stock) and continue to step 8.
8. Open the "Parts Manager" and the "Order Parts" on the left column.
9. Search for the non stocked parts from step 7. I would recommend searching first on the "JLCPCB Parts" section (that is usually cheaper and faster), but most likely you will have to search in the "Global Sourcing Parts". I would recommend only purchasing components in stock, because orders with components having a Lead Time, in my experience sometimes get heavily delayed or even cancelled.
10. Complete the components order, and wait till they are received by JLCPCB (they will notify by email). For stocked components, this should take 2 or 3 weeks max.
11. Repeat steps 1 to 7. Now you should be able to select your purchased components for the assembly.
12. You will be presented a component placement preview. It is a common issue that all components have a wrong offset from the board origin, and some can be wrongly rotated. Do not worry, this is normal and will be later corrected by the DFM analysis. Just click "Next".
13. You can now review the order, place it to the cart and proceed to checkout. Done! Just have to wait for the boards to arrive to your door. Be warned though that depending on your country and the shipping method, you might have to fill additional paperwork and pay import customs.

Enjoy!
