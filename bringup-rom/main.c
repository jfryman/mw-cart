/* MegaWiFi Rev.C bring-up test ROM.
 *
 * Exercises the TL16C550D (U7) and the ESP32 link on a freshly assembled
 * board, in dependency order:
 *   1 SPR scratch      - 68k <-> UART data bus, CS, RD/WR strobes
 *   2 reg decode       - A0..A2 decode and DLAB (distinct registers hold distinct values)
 *   3 LSR idle         - FIFO reset, transmitter empty
 *   4 loopback data    - 8 KiB through the internal loop at 1.25 Mbaud
 *   5 modem loopback   - MCR -> MSR internal loop paths
 *   6 crystal          - measures the UART clock against the VDP frame rate
 *   9 flash A17-A22    - pattern blocks from tools/fk_hiflash.py: A17-A21 below 4 MiB,
 *                        the flat-8MiB ~CART_IN = A22 hack above it, then ~CART_IN toggling
 *                        (SKIP if no pattern is written). Runs after 6, before 7.
 *   7 ESP32 version    - ESP reset via DTR, LSD/MW_CMD_VERSION at 1.25 Mbaud
 *   8 echo stress      - MW_CMD_ECHO forever, counts errors (RX FIFO / CS-hold check)
 * Press START at any time during the stress test to rerun everything.
 */
#include <stdint.h>
#include "vdp.h"
#include "uart.h"

volatile uint32_t g_frames;	/* incremented by VINT in boot.s */

#define NAME_X	3
#define RES_X	20
#define INFO_X	25
#define FIRST_ROW 4

/* ------------------------------------------------------------------ helpers */

static uint32_t now(void) { return g_frames; }

static void wait_frames(uint32_t n)
{
	uint32_t t = now();
	while (now() - t < n)
		;
}

static int start_pressed(void)
{
	volatile uint8_t *data = (volatile uint8_t *)0xA10003;
	volatile uint8_t *ctrl = (volatile uint8_t *)0xA10009;
	uint8_t v;
	*ctrl = 0x40;
	*data = 0x00;
	__asm__ volatile("nop\n nop");
	v = *data;
	*data = 0x40;
	return !(v & 0x20);
}

static uint16_t lfsr;
static uint8_t rnd(void)
{
	lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u);
	return (uint8_t)lfsr;
}

static void row_name(uint8_t row, const char *num, const char *name)
{
	txt_clear_row(row);
	txt_put(0, row, COL_WHITE, num);
	txt_put(NAME_X, row, COL_WHITE, name);
	txt_put(RES_X, row, COL_YELLOW, "....");
}

static int verdict(uint8_t row, int ok)
{
	txt_put(RES_X, row, ok ? COL_GREEN : COL_RED, ok ? "PASS" : "FAIL");
	return ok;
}

/* "Wxx Rxx" style detail */
static void wr_detail(uint8_t row, uint8_t w, uint8_t r)
{
	txt_put(INFO_X, row, COL_RED, "W");
	txt_hex(INFO_X + 1, row, COL_RED, w, 2);
	txt_put(INFO_X + 4, row, COL_RED, "R");
	txt_hex(INFO_X + 5, row, COL_RED, r, 2);
}

static void uart_setup(uint16_t divisor, uint8_t mcr)
{
	U_LCR = 0x83;		/* DLAB=1, 8N1 */
	U_DLL = divisor & 0xFF;
	U_DLM = divisor >> 8;
	U_LCR = 0x03;		/* DLAB=0, 8N1 */
	U_IER = 0x00;
	U_FCR = FCR_TRIG14_RESET;
	U_MCR = mcr;
}

static void rx_flush(void)
{
	uint16_t n = 0;
	while ((U_LSR & LSR_DR) && n++ < 64)
		(void)U_RHR;
}

/* ------------------------------------------------------------------ tests */

static int t_spr(uint8_t row)
{
	static const uint8_t pat[] = { 0x00, 0xFF, 0x55, 0xAA, 0x01, 0x02, 0x04, 0x08,
		0x10, 0x20, 0x40, 0x80, 0xFE, 0xFD, 0xFB, 0xF7, 0xEF, 0xDF, 0xBF, 0x7F };
	uint8_t i;
	row_name(row, "1", "SPR scratch");
	for (i = 0; i < sizeof(pat); i++) {
		uint8_t r;
		U_SPR = pat[i];
		(void)U_LSR;	/* different register in between: defeats open-bus echo */
		r = U_SPR;
		if (r != pat[i]) {
			wr_detail(row, pat[i], r);
			return verdict(row, 0);
		}
	}
	return verdict(row, 1);
}

static int check_reg(uint8_t row, const char *name, uint8_t want, uint8_t got)
{
	if (want == got)
		return 1;
	txt_put(INFO_X, row, COL_RED, name);
	wr_detail(row + 1, want, got);
	return 0;
}

static int t_decode(uint8_t row)
{
	/* MCR patterns use only OUT1/OUT2/LOOP so the ESP32 EN/GPIO9 pins never move */
	static const uint8_t v[2][4] = {
		/* SPR   LCR   IER   MCR */
		{ 0x3C, 0x1B, 0x05, 0x0C },
		{ 0xC3, 0x24, 0x0A, 0x14 },
	};
	uint8_t i;
	int ok = 1;
	row_name(row, "2", "reg decode");
	txt_clear_row(row + 1);
	for (i = 0; i < 2 && ok; i++) {
		U_SPR = v[i][0];
		U_LCR = v[i][1];
		U_IER = v[i][2];
		U_MCR = v[i][3];
		ok = check_reg(row, "SPR", v[i][0], U_SPR) &&
		     check_reg(row, "LCR", v[i][1], U_LCR) &&
		     check_reg(row, "IER", v[i][2], U_IER & 0x0F) &&
		     check_reg(row, "MCR", v[i][3], U_MCR & 0x1F);
	}
	if (ok) {
		/* divisor latches share addresses 0/1 with RHR/IER */
		U_LCR = 0x83;
		U_DLL = 0x5A;
		U_DLM = 0xA5;
		ok = check_reg(row, "DLL", 0x5A, U_DLL) && check_reg(row, "DLM", 0xA5, U_DLM);
		U_LCR = 0x03;
		ok = ok && check_reg(row, "IER", 0x0A, U_IER & 0x0F);
	}
	U_IER = 0;
	U_MCR = 0;
	U_LCR = 0x03;
	return verdict(row, ok);
}

static int t_lsr_idle(uint8_t row)
{
	uint8_t lsr;
	row_name(row, "3", "LSR idle");
	uart_setup(LINK_DIVISOR, 0);
	wait_frames(1);
	lsr = U_LSR;
	txt_put(INFO_X, row, COL_WHITE, "LSR");
	txt_hex(INFO_X + 4, row, COL_WHITE, lsr, 2);
	return verdict(row, (lsr & 0x7F) == (LSR_THRE | LSR_TEMT));
}

static int t_loop_data(uint8_t row)
{
	const uint16_t total = 8192;
	uint16_t sent = 0, rcvd = 0;
	uint16_t tx_lfsr, rx_lfsr = 0x1D0F;
	row_name(row, "4", "loopback 8K");
	uart_setup(LINK_DIVISOR, MCR_LOOP);
	rx_flush();
	lfsr = 0x1D0F;
	while (rcvd < total) {
		uint8_t i;
		uint32_t t0 = now();
		while (!(U_LSR & LSR_THRE))
			if (now() - t0 > 3) {
				txt_put(INFO_X, row, COL_RED, "TX stuck");
				return verdict(row, 0);
			}
		for (i = 0; i < 8; i++, sent++)
			U_THR = rnd();
		tx_lfsr = lfsr;
		lfsr = rx_lfsr;
		for (i = 0; i < 8; i++, rcvd++) {
			uint8_t lsr, b, want;
			t0 = now();
			while (!((lsr = U_LSR) & LSR_DR))
				if (now() - t0 > 3) {
					txt_put(INFO_X, row, COL_RED, "RX tmo");
					txt_dec(INFO_X + 7, row, COL_RED, rcvd);
					return verdict(row, 0);
				}
			b = U_RHR;
			want = rnd();
			if ((lsr & LSR_ERRS) || b != want) {
				if (lsr & LSR_ERRS) {
					txt_put(INFO_X, row, COL_RED, "LSR");
					txt_hex(INFO_X + 4, row, COL_RED, lsr, 2);
				} else {
					wr_detail(row, want, b);
				}
				return verdict(row, 0);
			}
		}
		rx_lfsr = lfsr;
		lfsr = tx_lfsr;
	}
	(void)sent;
	txt_put(INFO_X, row, COL_WHITE, "8192 B ok");
	return verdict(row, 1);
}

static int t_modem_loop(uint8_t row)
{
	/* in loop mode: DTR->DSR, RTS->CTS, OUT1->RI, OUT2->DCD */
	static const uint8_t mcr[] = { 0, MCR_DTR, MCR_RTS, MCR_OUT1, MCR_OUT2 };
	static const uint8_t msr[] = { 0, MSR_DSR, MSR_CTS, MSR_RI, MSR_DCD };
	uint8_t i;
	int ok = 1;
	row_name(row, "5", "modem loop");
	for (i = 0; i < sizeof(mcr) && ok; i++) {
		uint8_t got;
		U_MCR = MCR_LOOP | mcr[i];
		got = U_MSR & 0xF0;
		if (got != msr[i]) {
			wr_detail(row, msr[i], got);
			ok = 0;
		}
	}
	U_MCR = 0;
	return verdict(row, ok);
}

static int t_crystal(uint8_t row)
{
	/* Keep the TX FIFO topped up in internal loopback at divisor 20
	 * (62.5 kbaud, 6250 B/s): bytes moved per second = clk / (16 * 20 * 10). */
	const uint16_t div = 20;
	const uint32_t frames = 120;
	uint32_t t0, bytes = 0, fps100, bps100, khz;
	int pal = vdp_is_pal();
	row_name(row, "6", "crystal");
	uart_setup(div, MCR_LOOP);
	t0 = now();
	while (now() == t0)
		;
	t0 = now();
	while (now() - t0 < frames) {
		if (U_LSR & LSR_THRE) {
			uint8_t i;
			for (i = 0; i < 16; i++)
				U_THR = 0x55;
			bytes += 16;
		}
		{
			uint8_t n = 16;	/* bounded: a dead bus can read DR stuck high */
			while ((U_LSR & LSR_DR) && n--)
				(void)U_RHR;
		}
	}
	fps100 = pal ? 4970 : 5992;		/* MD field rate x100 */
	bps100 = bytes * fps100 / frames;	/* bytes/s x100, < 1e6 */
	khz = bps100 * (16UL * 10 * div) / 100000UL;
	U_MCR = 0;
	txt_dec(INFO_X, row, COL_WHITE, khz / 1000);
	txt_put(INFO_X + 2, row, COL_WHITE, ".");
	txt_dec(INFO_X + 3, row, COL_WHITE, (khz % 1000) / 100);
	txt_dec(INFO_X + 4, row, COL_WHITE, (khz % 100) / 10);
	txt_put(INFO_X + 6, row, COL_WHITE, pal ? "MHz P" : "MHz N");
	return verdict(row, khz >= 19700 && khz <= 20300);
}

/* ------------------------------------------------------- high flash (9) */

/* 256-byte pattern blocks written by tools/fk_hiflash.py (layout must match
 * pattern() there): "MW" "AT", addr hi/lo, ~addr hi/lo, then 122 LFSR words
 * seeded from the address. The low half proves A17-A21 reach the flash; the
 * high half ($400000+) proves the flat-8MiB hack (R1: ~CART_IN = A22). */
static const uint32_t hb_addr[] = {
	0x020000, 0x040000, 0x080000, 0x100000, 0x200000, 0x3E0000,
	0x400000, 0x420000, 0x440000, 0x480000, 0x500000, 0x600000, 0x7E0000,
};
#define HB_N		(sizeof(hb_addr) / sizeof(hb_addr[0]))
#define HB_LOW_N	6
#define HB_WORDS	128
#define HB_TOGGLE_FRAMES 300

enum hb_res { HB_OK, HB_BLANK, HB_ALIAS, HB_BAD };

struct hb_fail {
	uint32_t addr, alias;
	uint16_t want, got;
};

static uint16_t hb_step(uint16_t s)
{
	return (s >> 1) ^ ((s & 1) ? 0xB400 : 0);
}

static uint16_t hb_seed(uint32_t a)
{
	uint16_t s = 0xACE1 ^ (uint16_t)(a >> 8);
	return s ? s : 1;
}

static enum hb_res hb_check(uint32_t a, struct hb_fail *f)
{
	volatile const uint16_t *p = (volatile const uint16_t *)a;
	uint16_t hdr[6], s = hb_seed(a), i, w;
	hdr[0] = 0x4D57;
	hdr[1] = 0x4154;
	hdr[2] = a >> 16;
	hdr[3] = a & 0xFFFF;
	hdr[4] = ~hdr[2];
	hdr[5] = ~hdr[3];
	if (p[0] == 0xFFFF && p[1] == 0xFFFF && p[2] == 0xFFFF && p[3] == 0xFFFF)
		return HB_BLANK;
	/* a valid block with someone else's address = an address line fault */
	if (p[0] == hdr[0] && p[1] == hdr[1] && p[4] == (uint16_t)~p[2] && p[5] == (uint16_t)~p[3] &&
	    (p[2] != hdr[2] || p[3] != hdr[3])) {
		f->alias = ((uint32_t)p[2] << 16) | p[3];
		return HB_ALIAS;
	}
	for (i = 0; i < HB_WORDS; i++) {
		if (i < 6) {
			w = hdr[i];
		} else {
			s = hb_step(s);
			w = s;
		}
		if (p[i] != w) {
			f->want = w;
			f->got = p[i];
			return HB_BAD;
		}
	}
	return HB_OK;
}

static void hb_detail(uint8_t row, enum hb_res r, const struct hb_fail *f)
{
	txt_clear_row(row);
	txt_put(3, row, COL_RED, "@");
	txt_hex(4, row, COL_RED, f->addr, 6);
	if (r == HB_ALIAS) {
		uint32_t x = f->addr ^ f->alias;
		uint8_t b;
		txt_put(11, row, COL_RED, "reads");
		txt_hex(17, row, COL_RED, f->alias, 6);
		for (b = 17; b <= 22; b++)
			if (x & (1UL << b))
				break;
		txt_put(24, row, COL_RED, "A");
		txt_dec(25, row, COL_RED, b);
		txt_put(28, row, COL_RED, b == 22 ? "(R1/~CIN)" : "open?");
	} else if (r == HB_BAD) {
		txt_put(11, row, COL_RED, "W");
		txt_hex(12, row, COL_RED, f->want, 4);
		txt_put(17, row, COL_RED, "R");
		txt_hex(18, row, COL_RED, f->got, 4);
		if (f->addr >= 0x400000)
			txt_put(24, row, COL_RED, "hi half dead");
	} else if (f->addr >= 0x400000 && f->alias) {
		txt_put(11, row, COL_RED, "blank: R2? no 8MiB map");
	} else {
		txt_put(11, row, COL_RED, "blank: rerun fk_hiflash");
	}
}

/* Reads ROM below 4 MiB and pattern data above it back to back, so the
 * console's ~CART_IN (= A22 via R1) flips on every access. */
static uint32_t hb_toggle(uint32_t *reads)
{
	volatile const uint16_t *lo = (volatile const uint16_t *)0x000100;	/* "SE" of "SEGA" */
	volatile const uint16_t *hi[HB_N - HB_LOW_N];
	uint16_t hi_want[HB_N - HB_LOW_N];
	uint32_t t0, err = 0, n = 0;
	uint8_t i;
	__asm__("" : "+a"(lo));	/* GCC flags constant pointers < 4 KiB as null-ish */
	for (i = 0; i < HB_N - HB_LOW_N; i++) {
		hi[i] = (volatile const uint16_t *)hb_addr[HB_LOW_N + i] + 6;
		hi_want[i] = hb_step(hb_seed(hb_addr[HB_LOW_N + i]));
	}
	t0 = now();
	while (now() - t0 < HB_TOGGLE_FRAMES) {
		for (i = 0; i < HB_N - HB_LOW_N; i++) {
			if (*lo != 0x5345)
				err++;
			if (*hi[i] != hi_want[i])
				err++;
		}
		n += 2 * (HB_N - HB_LOW_N);
	}
	*reads = n;
	return err;
}

static int t_hiflash(uint8_t row)
{
	struct hb_fail f = { 0, 0, 0, 0 }, first = { 0, 0, 0, 0 };
	enum hb_res worst = HB_OK;
	uint8_t i, ok_lo = 0, ok_hi = 0, marked = 0;
	uint32_t reads, err;
	row_name(row, "9", "flash A17-A22");
	txt_clear_row(row + 1);
	for (i = 0; i < HB_N; i++) {
		volatile const uint16_t *p = (volatile const uint16_t *)hb_addr[i];
		enum hb_res r = hb_check(hb_addr[i], &f);
		if (p[0] == 0x4D57 && p[1] == 0x4154)
			marked++;
		if (r == HB_OK) {
			if (i < HB_LOW_N)
				ok_lo++;
			else
				ok_hi++;
			continue;
		}
		/* report the most telling failure: alias > bad data > blank */
		if (worst == HB_OK || (r == HB_ALIAS && worst != HB_ALIAS) ||
		    (r == HB_BAD && worst == HB_BLANK)) {
			worst = r;
			first = f;
			first.addr = hb_addr[i];
		}
	}
	if (worst == HB_BLANK && first.addr >= 0x400000 && ok_lo == HB_LOW_N)
		first.alias = 1;	/* low half fine: the 8 MiB map is missing, not the pattern */
	/* no "MWAT" anywhere: pattern never written (cart blank, or another ROM in it) */
	if (marked == 0) {
		txt_put(INFO_X, row, COL_YELLOW, "no pattern");
		txt_put(3, row + 1, COL_YELLOW, "write it: tools/fk_hiflash.py");
		txt_put(RES_X, row, COL_YELLOW, "SKIP");
		return 1;
	}
	txt_put(INFO_X, row, COL_WHITE, "L");
	txt_dec(INFO_X + 1, row, ok_lo == HB_LOW_N ? COL_WHITE : COL_RED, ok_lo);
	txt_put(INFO_X + 3, row, COL_WHITE, "H");
	txt_dec(INFO_X + 4, row, ok_hi == HB_N - HB_LOW_N ? COL_WHITE : COL_RED, ok_hi);
	if (worst != HB_OK) {
		hb_detail(row + 1, worst, &first);
		return verdict(row, 0);
	}
	txt_put(3, row + 1, COL_WHITE, "~CART_IN toggle...");
	err = hb_toggle(&reads);
	txt_clear_row(row + 1);
	txt_put(3, row + 1, COL_WHITE, "toggle reads");
	txt_dec(16, row + 1, COL_WHITE, reads);
	txt_put(26, row + 1, COL_WHITE, "err");
	txt_dec(30, row + 1, err ? COL_RED : COL_GREEN, err);
	return verdict(row, err == 0);
}

/* ------------------------------------------------------------- LSD / MW */

#define LSD_STX_ETX 0x7E
#define MW_CMD_OK 0
#define MW_CMD_VERSION 1
#define MW_CMD_ECHO 2
#define ECHO_MAX 1024

static uint8_t txbuf[4 + ECHO_MAX] __attribute__((aligned(2)));
static uint8_t rxbuf[4 + ECHO_MAX + 16] __attribute__((aligned(2)));

enum lsd_err { LSD_OK = 0, LSD_TX_TMO, LSD_RX_TMO, LSD_LSR, LSD_FRAMING, LSD_TOOBIG, LSD_MISMATCH };
static uint8_t last_lsr;

static enum lsd_err tx_byte(uint8_t b)
{
	uint32_t t0 = now();
	while (!(U_LSR & LSR_THRE))
		if (now() - t0 > 30)
			return LSD_TX_TMO;	/* auto-CTS held off for 0.5 s */
	U_THR = b;
	return LSD_OK;
}

static enum lsd_err lsd_send(uint8_t ch, const uint8_t *d, uint16_t len)
{
	enum lsd_err e;
	uint16_t i;
	if ((e = tx_byte(LSD_STX_ETX)) || (e = tx_byte((ch << 4) | (len >> 8))) ||
	    (e = tx_byte(len & 0xFF)))
		return e;
	for (i = 0; i < len; i++)
		if ((e = tx_byte(d[i])))
			return e;
	return tx_byte(LSD_STX_ETX);
}

static uint32_t rx_deadline;	/* absolute frame count bounding a whole lsd_recv() */

static enum lsd_err rx_byte(uint8_t *b, uint32_t tmo)
{
	uint32_t t0 = now();
	uint8_t lsr;
	while (!((lsr = U_LSR) & LSR_DR))
		if (now() - t0 > tmo)
			return LSD_RX_TMO;
	if ((int32_t)(now() - rx_deadline) > 0)
		return LSD_RX_TMO;
	*b = U_RHR;
	if (lsr & LSR_ERRS) {
		last_lsr = lsr;
		return LSD_LSR;
	}
	return LSD_OK;
}

static enum lsd_err lsd_recv(uint8_t *d, uint16_t max, uint16_t *len, uint32_t tmo)
{
	enum lsd_err e;
	uint8_t b, hi;
	uint16_t i, n;
	rx_deadline = now() + 2 * tmo;
	do {			/* skip noise until STX */
		if ((e = rx_byte(&b, tmo)))
			return e;
	} while (b != LSD_STX_ETX);
	do {			/* back-to-back 0x7E: previous ETX + STX */
		if ((e = rx_byte(&hi, tmo)))
			return e;
	} while (hi == LSD_STX_ETX);
	if ((e = rx_byte(&b, tmo)))
		return e;
	n = ((uint16_t)(hi & 0x0F) << 8) | b;
	if (n > max)
		return LSD_TOOBIG;
	for (i = 0; i < n; i++)
		if ((e = rx_byte(&d[i], tmo)))
			return e;
	if ((e = rx_byte(&b, tmo)))
		return e;
	*len = n;
	return b == LSD_STX_ETX ? LSD_OK : LSD_FRAMING;
}

static const char *const err_txt[] = { "ok", "CTS held", "no reply", "LSR err", "framing", "too big", "mismatch" };

static void esp_boot(void)
{
	/* SGDK uart_init/uart_reset/uart_start sequence: hold EN low with GPIO9
	 * (RTS) high, release, let it boot, then enable RTS for auto flow. */
	uart_setup(LINK_DIVISOR, MCR_AFE | MCR_DTR);
	wait_frames(3);
	U_MCR = MCR_AFE;
	wait_frames(60);
	U_FCR = FCR_TRIG14_RESET;	/* drop the ROM bootloader's 115200 baud chatter */
	rx_flush();
	U_MCR = MCR_AFE | MCR_RTS;
}

static int t_version(uint8_t row)
{
	uint16_t len = 0;
	enum lsd_err e;
	row_name(row, "7", "ESP32 version");
	txt_clear_row(row + 1);
	esp_boot();
	txbuf[0] = 0; txbuf[1] = MW_CMD_VERSION; txbuf[2] = 0; txbuf[3] = 0;
	e = lsd_send(0, txbuf, 4);
	if (!e)
		e = lsd_recv(rxbuf, sizeof(rxbuf), &len, 60);
	if (e) {
		txt_put(INFO_X, row, COL_RED, err_txt[e]);
		if (e == LSD_RX_TMO)
			txt_put(3, row + 1, COL_YELLOW, "fw must use LSD_UART_BR 1250000");
		if (e == LSD_LSR)
			txt_hex(INFO_X + 8, row, COL_RED, last_lsr, 2);
		return verdict(row, 0);
	}
	if (len < 7 || rxbuf[0] != 0 || rxbuf[1] != MW_CMD_OK) {
		txt_put(INFO_X, row, COL_RED, "bad reply");
		txt_hex(3, row + 1, COL_RED, ((uint32_t)rxbuf[0] << 24) | ((uint32_t)rxbuf[1] << 16) |
			((uint32_t)rxbuf[2] << 8) | rxbuf[3], 8);
		return verdict(row, 0);
	}
	{
		uint8_t x = INFO_X;
		x += txt_dec(x, row, COL_WHITE, rxbuf[4]);
		txt_put(x++, row, COL_WHITE, ".");
		x += txt_dec(x, row, COL_WHITE, rxbuf[5]);
		txt_put(x++, row, COL_WHITE, ".");
		txt_dec(x, row, COL_WHITE, rxbuf[6]);
		rxbuf[len < sizeof(rxbuf) ? len : sizeof(rxbuf) - 1] = 0;
		txt_put(3, row + 1, COL_WHITE, "variant:");
		txt_put(12, row + 1, COL_WHITE, (const char *)rxbuf + 7);
	}
	return verdict(row, 1);
}

/* Echo forever with changing sizes; returns when START is pressed. */
static void t_echo(uint8_t row)
{
	static const uint16_t sizes[] = { 1, 16, 64, 255, 256, 512, 1000, 1024 };
	uint32_t ok = 0, bad = 0, bytes = 0, t_start;
	uint8_t si = 0;
	enum lsd_err last = LSD_OK;
	row_name(row, "8", "echo stress");
	txt_put(3, row + 1, COL_WHITE, "frames      errors      KB/s");
	txt_put(3, row + 3, COL_WHITE, "last error:");
	txt_put(3, row + 5, COL_YELLOW, "START = rerun all tests");
	lfsr = 0xBEEF;
	t_start = now();
	while (!start_pressed()) {
		uint16_t n = sizes[si], i, len = 0;
		enum lsd_err e;
		si = (si + 1) % (sizeof(sizes) / sizeof(sizes[0]));
		txbuf[0] = 0; txbuf[1] = MW_CMD_ECHO; txbuf[2] = n >> 8; txbuf[3] = n & 0xFF;
		for (i = 0; i < n; i++)
			txbuf[4 + i] = rnd();
		e = lsd_send(0, txbuf, 4 + n);
		if (!e)
			e = lsd_recv(rxbuf, sizeof(rxbuf), &len, 60);
		if (!e) {
			if (len != 4 + n || rxbuf[0] || rxbuf[1] != MW_CMD_OK ||
			    rxbuf[2] != txbuf[2] || rxbuf[3] != txbuf[3])
				e = LSD_MISMATCH;
			for (i = 0; !e && i < n; i++)
				if (rxbuf[4 + i] != txbuf[4 + i])
					e = LSD_MISMATCH;
		}
		if (e) {
			bad++;
			last = e;
			txt_clear_row(row + 4);
			txt_put(3, row + 4, COL_RED, err_txt[e]);
			txt_put(12, row + 4, COL_RED, "size");
			txt_dec(17, row + 4, COL_RED, n);
			if (e == LSD_LSR)
				txt_hex(23, row + 4, COL_RED, last_lsr, 2);
			esp_boot();	/* resync after any failure */
		} else {
			ok++;
			bytes += 2UL * (n + 4);
		}
		{
			uint32_t secs100 = (now() - t_start) * 100 / (vdp_is_pal() ? 50 : 60);
			txt_dec(3, row + 2, COL_WHITE, ok);
			txt_dec(15, row + 2, bad ? COL_RED : COL_GREEN, bad);
			if (secs100) {
				txt_put(27, row + 2, COL_WHITE, "      ");
				txt_dec(27, row + 2, COL_WHITE, bytes / 10 / secs100);
			}
		}
		verdict(row, bad == 0 && ok > 0);
	}
	(void)last;
}

/* ------------------------------------------------------------------ main */

int main(void)
{
	vdp_init();
	for (;;) {
		uint8_t r;
		int hw_ok;
		for (r = 0; r < TXT_ROWS; r++)
			txt_clear_row(r);
		txt_put(1, 1, COL_YELLOW, "MegaWiFi Rev.C bring-up");
		txt_put(1, 2, COL_WHITE, "TL16C550D 20MHz, link 1.25 Mbaud");

		r = FIRST_ROW;
		hw_ok = t_spr(r++);
		hw_ok &= t_decode(r); r += 2;
		hw_ok &= t_lsr_idle(r++);
		hw_ok &= t_loop_data(r++);
		hw_ok &= t_modem_loop(r++);
		hw_ok &= t_crystal(r++);
		t_hiflash(r); r += 2;
		txt_put(1, r++, hw_ok ? COL_GREEN : COL_RED,
			hw_ok ? "UART + crystal OK" : "UART checks FAILED");
		r++;
		if (t_version(r)) {
			r += 3;
			t_echo(r);
		} else {
			txt_put(3, r + 3, COL_YELLOW, "START = rerun all tests");
			while (!start_pressed())
				;
		}
		while (start_pressed())
			;
	}
}
