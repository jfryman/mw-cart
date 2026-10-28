/* 68000-safe replacements for the libgcc arithmetic helpers gcc emits for
 * 32-bit multiply/divide on -m68000. The distro m68k libgcc is built for
 * 68020+ (its __umodsi3 uses bsr.l, illegal on a 68000), so we do not link it.
 * Plain shift/add code only: no '*', '/' or '%' on 32-bit values in here. */

static unsigned long udivmod(unsigned long n, unsigned long d, unsigned long *rem)
{
	unsigned long q = 0, r = 0;
	int i;
	if (d == 0) {
		*rem = n;
		return 0xFFFFFFFFUL;
	}
	for (i = 31; i >= 0; i--) {
		r = (r << 1) | ((n >> i) & 1);
		if (r >= d) {
			r -= d;
			q |= 1UL << i;
		}
	}
	*rem = r;
	return q;
}

unsigned long __mulsi3(unsigned long a, unsigned long b)
{
	unsigned long r = 0;
	while (b) {
		if (b & 1)
			r += a;
		a <<= 1;
		b >>= 1;
	}
	return r;
}

unsigned long __udivsi3(unsigned long n, unsigned long d)
{
	unsigned long r;
	return udivmod(n, d, &r);
}

unsigned long __umodsi3(unsigned long n, unsigned long d)
{
	unsigned long r;
	udivmod(n, d, &r);
	return r;
}

long __divsi3(long n, long d)
{
	unsigned long r, q;
	int neg = (n < 0) != (d < 0);
	q = udivmod(n < 0 ? -(unsigned long)n : (unsigned long)n,
		    d < 0 ? -(unsigned long)d : (unsigned long)d, &r);
	return neg ? -(long)q : (long)q;
}

long __modsi3(long n, long d)
{
	unsigned long r;
	udivmod(n < 0 ? -(unsigned long)n : (unsigned long)n,
		d < 0 ? -(unsigned long)d : (unsigned long)d, &r);
	return n < 0 ? -(long)r : (long)r;
}
