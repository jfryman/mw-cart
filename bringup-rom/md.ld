/* Linker script: ROM at 0x000000, work RAM at 0xFF0000. */
OUTPUT_ARCH(m68k)
ENTRY(_start)

MEMORY
{
    rom (rx)  : ORIGIN = 0x00000000, LENGTH = 0x00020000
    ram (rwx) : ORIGIN = 0x00FF0000, LENGTH = 0x0000F000
}

SECTIONS
{
    .text : {
        KEEP(*(.text.boot))
        *(.text .text.*)
        . = ALIGN(2);
        *(.rodata .rodata.*)
        . = ALIGN(2);
    } > rom

    .data : {
        __data_start = .;
        *(.data .data.*)
        . = ALIGN(2);
        __data_end = .;
    } > ram AT > rom
    __data_load = LOADADDR(.data);

    .bss (NOLOAD) : {
        __bss_start = .;
        *(.bss .bss.* COMMON)
        . = ALIGN(2);
        __bss_end = .;
    } > ram

    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
