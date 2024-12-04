# mw-cart
MegaWiFi Cartridge

![mw-cart](/mw-cart.jpg)

This cartridge is for the MegaWiFi project. It consists of a cartridge for the SEGA Genesis/Megadrive console, along with a WiFi interface, allowing brave programmers to implement games with online gaming, leaderboards, evil DLCs, etc.

This project was initially created for 1985alternativo, but to this day, no brave soul has dared to make an online game using this cart. Will you give it a try?

Have a look to the [github project page](https://gitlab.com/doragasu/mw) for more information.

## License
mw-cart is licensed under the [CERN OHL 1.2](http://www.ohwr.org/licenses/cern-ohl/v1.2) license. You are free to study, distribute and make modifications to the Documentation, under the aforementioned license terms. You are also free to make cartridges derived from the Documentation for non-commercial purposes. If you want to make a commercial Product using this Documentation, please contact me to obtain a licence.

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
