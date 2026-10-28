| MegaWiFi Rev.C bring-up ROM: vectors, cartridge header and C runtime start.
| Only VINT (level 6) is used; every other exception jumps to _fault.

        .section .text.boot, "ax"
        .org    0
        dc.l    0x01000000              | initial SSP (wraps to top of work RAM)
        dc.l    _start                  | initial PC
        dc.l    _x2
        dc.l    _x3
        dc.l    _x4
        dc.l    _x5
        dc.l    _x6
        dc.l    _x7
        dc.l    _x8
        dc.l    _x9
        dc.l    _x10
        dc.l    _x11
        dc.l    _x12
        dc.l    _x13
        dc.l    _x14
        dc.l    _x15
        dc.l    _x16
        dc.l    _x17
        dc.l    _x18
        dc.l    _x19
        dc.l    _x20
        dc.l    _x21
        dc.l    _x22
        dc.l    _x23
        dc.l    _x24
        dc.l    _x25
        dc.l    _x26
        dc.l    _x27
        dc.l    _x28
        dc.l    _x29
        dc.l    _vint
        dc.l    _x31
        dc.l    _x32
        dc.l    _x33
        dc.l    _x34
        dc.l    _x35
        dc.l    _x36
        dc.l    _x37
        dc.l    _x38
        dc.l    _x39
        dc.l    _x40
        dc.l    _x41
        dc.l    _x42
        dc.l    _x43
        dc.l    _x44
        dc.l    _x45
        dc.l    _x46
        dc.l    _x47
        dc.l    _x48
        dc.l    _x49
        dc.l    _x50
        dc.l    _x51
        dc.l    _x52
        dc.l    _x53
        dc.l    _x54
        dc.l    _x55
        dc.l    _x56
        dc.l    _x57
        dc.l    _x58
        dc.l    _x59
        dc.l    _x60
        dc.l    _x61
        dc.l    _x62
        dc.l    _x63

        .org    0x100
        .ascii  "SEGA MEGA DRIVE "                                     | console
        .ascii  "(C)JFRY 2026.OCT"                                     | copyright
        .ascii  "MEGAWIFI REV.C BRING-UP TEST                    "     | domestic name
        .ascii  "MEGAWIFI REV.C BRING-UP TEST                    "     | overseas name
        .ascii  "GM 00000000-00"                                       | serial
        dc.w    0                                                      | checksum (unused)
        .ascii  "J               "                                     | I/O support
        dc.l    0x00000000, 0x0001FFFF                                 | ROM range (128 KiB)
        dc.l    0x00FF0000, 0x00FFFFFF                                 | RAM range
        .ascii  "            "                                         | no SRAM
        .ascii  "            "                                         | modem
        .ascii  "                                        "             | memo
        .ascii  "JUE             "                                     | regions

        .org    0x200
        .globl  _start
_start:
        move.w  #0x2700, %sr            | interrupts off
        move.b  0xA10001, %d0           | TMSS: write 'SEGA' on consoles that need it
        andi.b  #0x0F, %d0
        beq.s   1f
        move.l  #0x53454741, 0xA14000
1:
        lea     __bss_start, %a0        | clear .bss
        lea     __bss_end, %a1
2:      cmpa.l  %a1, %a0
        bcc.s   3f
        clr.b   (%a0)+
        bra.s   2b
3:
        lea     __data_load, %a0        | copy .data from ROM to RAM
        lea     __data_start, %a1
        lea     __data_end, %a2
4:      cmpa.l  %a2, %a1
        bcc.s   5f
        move.b  (%a0)+, (%a1)+
        bra.s   4b
5:
        jsr     main
6:      bra.s   6b

        .globl  _vint
_vint:
        addq.l  #1, g_frames
        rte

        .globl  _fault
_fault:
        move.l  %sp, 0xFFFF02
        move.w  #0x2700, %sr            | unexpected exception: paint backdrop red, halt
        move.l  #0xC0000000, 0xC00004   | CRAM write, colour 0
        move.w  #0x000E, 0xC00000
7:      bra.s   7b


| per-vector stubs: record vector number + SP at $FFFF00 for post-mortem, then halt
_x2: move.w #2, 0xFFFF00
        bra.w _fault
_x3: move.w #3, 0xFFFF00
        bra.w _fault
_x4: move.w #4, 0xFFFF00
        bra.w _fault
_x5: move.w #5, 0xFFFF00
        bra.w _fault
_x6: move.w #6, 0xFFFF00
        bra.w _fault
_x7: move.w #7, 0xFFFF00
        bra.w _fault
_x8: move.w #8, 0xFFFF00
        bra.w _fault
_x9: move.w #9, 0xFFFF00
        bra.w _fault
_x10: move.w #10, 0xFFFF00
        bra.w _fault
_x11: move.w #11, 0xFFFF00
        bra.w _fault
_x12: move.w #12, 0xFFFF00
        bra.w _fault
_x13: move.w #13, 0xFFFF00
        bra.w _fault
_x14: move.w #14, 0xFFFF00
        bra.w _fault
_x15: move.w #15, 0xFFFF00
        bra.w _fault
_x16: move.w #16, 0xFFFF00
        bra.w _fault
_x17: move.w #17, 0xFFFF00
        bra.w _fault
_x18: move.w #18, 0xFFFF00
        bra.w _fault
_x19: move.w #19, 0xFFFF00
        bra.w _fault
_x20: move.w #20, 0xFFFF00
        bra.w _fault
_x21: move.w #21, 0xFFFF00
        bra.w _fault
_x22: move.w #22, 0xFFFF00
        bra.w _fault
_x23: move.w #23, 0xFFFF00
        bra.w _fault
_x24: move.w #24, 0xFFFF00
        bra.w _fault
_x25: move.w #25, 0xFFFF00
        bra.w _fault
_x26: move.w #26, 0xFFFF00
        bra.w _fault
_x27: move.w #27, 0xFFFF00
        bra.w _fault
_x28: move.w #28, 0xFFFF00
        bra.w _fault
_x29: move.w #29, 0xFFFF00
        bra.w _fault
_x31: move.w #31, 0xFFFF00
        bra.w _fault
_x32: move.w #32, 0xFFFF00
        bra.w _fault
_x33: move.w #33, 0xFFFF00
        bra.w _fault
_x34: move.w #34, 0xFFFF00
        bra.w _fault
_x35: move.w #35, 0xFFFF00
        bra.w _fault
_x36: move.w #36, 0xFFFF00
        bra.w _fault
_x37: move.w #37, 0xFFFF00
        bra.w _fault
_x38: move.w #38, 0xFFFF00
        bra.w _fault
_x39: move.w #39, 0xFFFF00
        bra.w _fault
_x40: move.w #40, 0xFFFF00
        bra.w _fault
_x41: move.w #41, 0xFFFF00
        bra.w _fault
_x42: move.w #42, 0xFFFF00
        bra.w _fault
_x43: move.w #43, 0xFFFF00
        bra.w _fault
_x44: move.w #44, 0xFFFF00
        bra.w _fault
_x45: move.w #45, 0xFFFF00
        bra.w _fault
_x46: move.w #46, 0xFFFF00
        bra.w _fault
_x47: move.w #47, 0xFFFF00
        bra.w _fault
_x48: move.w #48, 0xFFFF00
        bra.w _fault
_x49: move.w #49, 0xFFFF00
        bra.w _fault
_x50: move.w #50, 0xFFFF00
        bra.w _fault
_x51: move.w #51, 0xFFFF00
        bra.w _fault
_x52: move.w #52, 0xFFFF00
        bra.w _fault
_x53: move.w #53, 0xFFFF00
        bra.w _fault
_x54: move.w #54, 0xFFFF00
        bra.w _fault
_x55: move.w #55, 0xFFFF00
        bra.w _fault
_x56: move.w #56, 0xFFFF00
        bra.w _fault
_x57: move.w #57, 0xFFFF00
        bra.w _fault
_x58: move.w #58, 0xFFFF00
        bra.w _fault
_x59: move.w #59, 0xFFFF00
        bra.w _fault
_x60: move.w #60, 0xFFFF00
        bra.w _fault
_x61: move.w #61, 0xFFFF00
        bra.w _fault
_x62: move.w #62, 0xFFFF00
        bra.w _fault
_x63: move.w #63, 0xFFFF00
        bra.w _fault

        .section .note.GNU-stack, "", %progbits
