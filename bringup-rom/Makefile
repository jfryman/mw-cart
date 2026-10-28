# MegaWiFi Rev.C bring-up ROM
# Needs an m68k cross gcc (Fedora: dnf install gcc-m68k-linux-gnu binutils-m68k-linux-gnu).
PREFIX ?= m68k-linux-gnu-
CC      = $(PREFIX)gcc
OBJCOPY = $(PREFIX)objcopy
OBJDUMP = $(PREFIX)objdump

TARGET  = mw-revc-bringup
CFLAGS  = -m68000 -mstrict-align -Os -Wall -Wextra -ffreestanding -fno-builtin -fomit-frame-pointer \
          -ffunction-sections -fdata-sections -fno-asynchronous-unwind-tables
LDFLAGS = -m68000 -nostdlib -Wl,--build-id=none -T md.ld -Wl,--gc-sections -Wl,-Map=$(TARGET).map
OBJS    = boot.o main.o vdp.o font.o lib68k.o

all: $(TARGET).bin check

$(TARGET).elf: $(OBJS) md.ld
	$(CC) $(LDFLAGS) -o $@ $(OBJS)

# Pad to the 128 KiB declared in the cartridge header.
$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@
	truncate -s 131072 $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.s
	$(CC) -m68000 -c $< -o $@

# No libgcc (the distro one is 68020+); lib68k.c supplies the helpers.
# Refuse any 68020+ only opcode: long branches (0x6xFF), 32-bit mul/div, bitfields...
check: $(TARGET).elf
	@if $(OBJDUMP) -d $< | grep -Eq '^ +[0-9a-f]+:\s+6[0-9a-f]ff( |$$)|\b(bfffo|bfext[su]|divu\.l|divs\.l|mulu\.l|muls\.l|extb\.l|rtd|cas|chk2|cmp2)\b'; then \
		echo "ERROR: 68020+ instruction in image:"; \
		$(OBJDUMP) -d $< | grep -E '^ +[0-9a-f]+:\s+6[0-9a-f]ff( |$$)|\b(bfffo|divu\.l|divs\.l|mulu\.l|muls\.l|extb\.l)\b'; exit 1; fi
	@echo "68000 opcode check OK"

clean:
	rm -f $(OBJS) $(TARGET).elf $(TARGET).bin $(TARGET).map

.PHONY: all check clean
