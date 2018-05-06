/* Standalone file to develop bit transpose for bitslice implementations */
/* The goal: a faster way to split candidates into bit vectors */
/* In other words, we transpose a 64x64 bit matrix (actually 64x56) */

/* See http://openwall.com/lists/john-dev/2015/07/19/8 */

/* gcc -O3 simple_bit_layout.c && time ./a.out */

/*
 * Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define $bstype unsigned long long
#define $bsbits 64
#define $type unsigned long long
#define $bits 64

int main(void)
{

#define count $bsbits

    char *keys[count];
    size_t i, ki = 0;
    unsigned long long m, t;

#define len 7

#define buf_len ((len + 1) * count)
    char buf[buf_len];
    for (i = 0; i < buf_len; i++) {
        buf[i] = (i % 8 == 7 ? 0 : 'A' + i % 8);
        if (i % 8 == 0)
            keys[ki++] = &buf[i];
    }

    $bstype bits[$bits] = { 0 };

    /* End of initialization, start of implementations */

    size_t test_i;
    for (test_i = 0; test_i < 1e7; test_i++) {

        memcpy(bits, buf, sizeof(bits));

/* #define swap1(a0, a1, j, m) \ */
/*     t = (a0 & m) ^ (a1 >> j); \ */
/*     a0 ^= t; \ */
/*     a1 ^= (t << j); */

#define swap1 swap

#define swap(a0, a1, j, m) \
    t = (a0 ^ (a1 >> j)) & m; \
    a0 ^= t; \
    a1 ^= (t << j);

        /* perl -e 'sub t { my $i = shift; my $j = shift; my $m = shift; return unless $j > 0; for my $k ($i .. $i + $j - 1) { my $s = (($m >> 1) & ~$m) ? "" : "1"; printf "swap$s(bits[%d], bits[%d], %d, 0x%016xULL);\n", $k, $k + $j, $j, $m; } my $nj = $j >> 1; $m ^= $m << $nj; t($i, $nj, $m); t($i + $j, $nj, $m); } t(0, 32, 0x00000000ffffffff)' */

swap1(bits[0], bits[32], 32, 0x00000000ffffffffULL);
swap1(bits[1], bits[33], 32, 0x00000000ffffffffULL);
swap1(bits[2], bits[34], 32, 0x00000000ffffffffULL);
swap1(bits[3], bits[35], 32, 0x00000000ffffffffULL);
swap1(bits[4], bits[36], 32, 0x00000000ffffffffULL);
swap1(bits[5], bits[37], 32, 0x00000000ffffffffULL);
swap1(bits[6], bits[38], 32, 0x00000000ffffffffULL);
swap1(bits[7], bits[39], 32, 0x00000000ffffffffULL);
swap1(bits[8], bits[40], 32, 0x00000000ffffffffULL);
swap1(bits[9], bits[41], 32, 0x00000000ffffffffULL);
swap1(bits[10], bits[42], 32, 0x00000000ffffffffULL);
swap1(bits[11], bits[43], 32, 0x00000000ffffffffULL);
swap1(bits[12], bits[44], 32, 0x00000000ffffffffULL);
swap1(bits[13], bits[45], 32, 0x00000000ffffffffULL);
swap1(bits[14], bits[46], 32, 0x00000000ffffffffULL);
swap1(bits[15], bits[47], 32, 0x00000000ffffffffULL);
swap1(bits[16], bits[48], 32, 0x00000000ffffffffULL);
swap1(bits[17], bits[49], 32, 0x00000000ffffffffULL);
swap1(bits[18], bits[50], 32, 0x00000000ffffffffULL);
swap1(bits[19], bits[51], 32, 0x00000000ffffffffULL);
swap1(bits[20], bits[52], 32, 0x00000000ffffffffULL);
swap1(bits[21], bits[53], 32, 0x00000000ffffffffULL);
swap1(bits[22], bits[54], 32, 0x00000000ffffffffULL);
swap1(bits[23], bits[55], 32, 0x00000000ffffffffULL);
swap1(bits[24], bits[56], 32, 0x00000000ffffffffULL);
swap1(bits[25], bits[57], 32, 0x00000000ffffffffULL);
swap1(bits[26], bits[58], 32, 0x00000000ffffffffULL);
swap1(bits[27], bits[59], 32, 0x00000000ffffffffULL);
swap1(bits[28], bits[60], 32, 0x00000000ffffffffULL);
swap1(bits[29], bits[61], 32, 0x00000000ffffffffULL);
swap1(bits[30], bits[62], 32, 0x00000000ffffffffULL);
swap1(bits[31], bits[63], 32, 0x00000000ffffffffULL);
swap(bits[0], bits[16], 16, 0x0000ffff0000ffffULL);
swap(bits[1], bits[17], 16, 0x0000ffff0000ffffULL);
swap(bits[2], bits[18], 16, 0x0000ffff0000ffffULL);
swap(bits[3], bits[19], 16, 0x0000ffff0000ffffULL);
swap(bits[4], bits[20], 16, 0x0000ffff0000ffffULL);
swap(bits[5], bits[21], 16, 0x0000ffff0000ffffULL);
swap(bits[6], bits[22], 16, 0x0000ffff0000ffffULL);
swap(bits[7], bits[23], 16, 0x0000ffff0000ffffULL);
swap(bits[8], bits[24], 16, 0x0000ffff0000ffffULL);
swap(bits[9], bits[25], 16, 0x0000ffff0000ffffULL);
swap(bits[10], bits[26], 16, 0x0000ffff0000ffffULL);
swap(bits[11], bits[27], 16, 0x0000ffff0000ffffULL);
swap(bits[12], bits[28], 16, 0x0000ffff0000ffffULL);
swap(bits[13], bits[29], 16, 0x0000ffff0000ffffULL);
swap(bits[14], bits[30], 16, 0x0000ffff0000ffffULL);
swap(bits[15], bits[31], 16, 0x0000ffff0000ffffULL);
swap(bits[0], bits[8], 8, 0x00ff00ff00ff00ffULL);
swap(bits[1], bits[9], 8, 0x00ff00ff00ff00ffULL);
swap(bits[2], bits[10], 8, 0x00ff00ff00ff00ffULL);
swap(bits[3], bits[11], 8, 0x00ff00ff00ff00ffULL);
swap(bits[4], bits[12], 8, 0x00ff00ff00ff00ffULL);
swap(bits[5], bits[13], 8, 0x00ff00ff00ff00ffULL);
swap(bits[6], bits[14], 8, 0x00ff00ff00ff00ffULL);
swap(bits[7], bits[15], 8, 0x00ff00ff00ff00ffULL);
swap(bits[0], bits[4], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[1], bits[5], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[2], bits[6], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[3], bits[7], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[0], bits[2], 2, 0x3333333333333333ULL);
swap(bits[1], bits[3], 2, 0x3333333333333333ULL);
swap(bits[0], bits[1], 1, 0x5555555555555555ULL);
swap(bits[2], bits[3], 1, 0x5555555555555555ULL);
swap(bits[4], bits[6], 2, 0x3333333333333333ULL);
swap(bits[5], bits[7], 2, 0x3333333333333333ULL);
swap(bits[4], bits[5], 1, 0x5555555555555555ULL);
swap(bits[6], bits[7], 1, 0x5555555555555555ULL);
swap(bits[8], bits[12], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[9], bits[13], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[10], bits[14], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[11], bits[15], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[8], bits[10], 2, 0x3333333333333333ULL);
swap(bits[9], bits[11], 2, 0x3333333333333333ULL);
swap(bits[8], bits[9], 1, 0x5555555555555555ULL);
swap(bits[10], bits[11], 1, 0x5555555555555555ULL);
swap(bits[12], bits[14], 2, 0x3333333333333333ULL);
swap(bits[13], bits[15], 2, 0x3333333333333333ULL);
swap(bits[12], bits[13], 1, 0x5555555555555555ULL);
swap(bits[14], bits[15], 1, 0x5555555555555555ULL);
swap(bits[16], bits[24], 8, 0x00ff00ff00ff00ffULL);
swap(bits[17], bits[25], 8, 0x00ff00ff00ff00ffULL);
swap(bits[18], bits[26], 8, 0x00ff00ff00ff00ffULL);
swap(bits[19], bits[27], 8, 0x00ff00ff00ff00ffULL);
swap(bits[20], bits[28], 8, 0x00ff00ff00ff00ffULL);
swap(bits[21], bits[29], 8, 0x00ff00ff00ff00ffULL);
swap(bits[22], bits[30], 8, 0x00ff00ff00ff00ffULL);
swap(bits[23], bits[31], 8, 0x00ff00ff00ff00ffULL);
swap(bits[16], bits[20], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[17], bits[21], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[18], bits[22], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[19], bits[23], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[16], bits[18], 2, 0x3333333333333333ULL);
swap(bits[17], bits[19], 2, 0x3333333333333333ULL);
swap(bits[16], bits[17], 1, 0x5555555555555555ULL);
swap(bits[18], bits[19], 1, 0x5555555555555555ULL);
swap(bits[20], bits[22], 2, 0x3333333333333333ULL);
swap(bits[21], bits[23], 2, 0x3333333333333333ULL);
swap(bits[20], bits[21], 1, 0x5555555555555555ULL);
swap(bits[22], bits[23], 1, 0x5555555555555555ULL);
swap(bits[24], bits[28], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[25], bits[29], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[26], bits[30], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[27], bits[31], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[24], bits[26], 2, 0x3333333333333333ULL);
swap(bits[25], bits[27], 2, 0x3333333333333333ULL);
swap(bits[24], bits[25], 1, 0x5555555555555555ULL);
swap(bits[26], bits[27], 1, 0x5555555555555555ULL);
swap(bits[28], bits[30], 2, 0x3333333333333333ULL);
swap(bits[29], bits[31], 2, 0x3333333333333333ULL);
swap(bits[28], bits[29], 1, 0x5555555555555555ULL);
swap(bits[30], bits[31], 1, 0x5555555555555555ULL);
swap(bits[32], bits[48], 16, 0x0000ffff0000ffffULL);
swap(bits[33], bits[49], 16, 0x0000ffff0000ffffULL);
swap(bits[34], bits[50], 16, 0x0000ffff0000ffffULL);
swap(bits[35], bits[51], 16, 0x0000ffff0000ffffULL);
swap(bits[36], bits[52], 16, 0x0000ffff0000ffffULL);
swap(bits[37], bits[53], 16, 0x0000ffff0000ffffULL);
swap(bits[38], bits[54], 16, 0x0000ffff0000ffffULL);
swap(bits[39], bits[55], 16, 0x0000ffff0000ffffULL);
swap(bits[40], bits[56], 16, 0x0000ffff0000ffffULL);
swap(bits[41], bits[57], 16, 0x0000ffff0000ffffULL);
swap(bits[42], bits[58], 16, 0x0000ffff0000ffffULL);
swap(bits[43], bits[59], 16, 0x0000ffff0000ffffULL);
swap(bits[44], bits[60], 16, 0x0000ffff0000ffffULL);
swap(bits[45], bits[61], 16, 0x0000ffff0000ffffULL);
swap(bits[46], bits[62], 16, 0x0000ffff0000ffffULL);
swap(bits[47], bits[63], 16, 0x0000ffff0000ffffULL);
swap(bits[32], bits[40], 8, 0x00ff00ff00ff00ffULL);
swap(bits[33], bits[41], 8, 0x00ff00ff00ff00ffULL);
swap(bits[34], bits[42], 8, 0x00ff00ff00ff00ffULL);
swap(bits[35], bits[43], 8, 0x00ff00ff00ff00ffULL);
swap(bits[36], bits[44], 8, 0x00ff00ff00ff00ffULL);
swap(bits[37], bits[45], 8, 0x00ff00ff00ff00ffULL);
swap(bits[38], bits[46], 8, 0x00ff00ff00ff00ffULL);
swap(bits[39], bits[47], 8, 0x00ff00ff00ff00ffULL);
swap(bits[32], bits[36], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[33], bits[37], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[34], bits[38], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[35], bits[39], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[32], bits[34], 2, 0x3333333333333333ULL);
swap(bits[33], bits[35], 2, 0x3333333333333333ULL);
swap(bits[32], bits[33], 1, 0x5555555555555555ULL);
swap(bits[34], bits[35], 1, 0x5555555555555555ULL);
swap(bits[36], bits[38], 2, 0x3333333333333333ULL);
swap(bits[37], bits[39], 2, 0x3333333333333333ULL);
swap(bits[36], bits[37], 1, 0x5555555555555555ULL);
swap(bits[38], bits[39], 1, 0x5555555555555555ULL);
swap(bits[40], bits[44], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[41], bits[45], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[42], bits[46], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[43], bits[47], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[40], bits[42], 2, 0x3333333333333333ULL);
swap(bits[41], bits[43], 2, 0x3333333333333333ULL);
swap(bits[40], bits[41], 1, 0x5555555555555555ULL);
swap(bits[42], bits[43], 1, 0x5555555555555555ULL);
swap(bits[44], bits[46], 2, 0x3333333333333333ULL);
swap(bits[45], bits[47], 2, 0x3333333333333333ULL);
swap(bits[44], bits[45], 1, 0x5555555555555555ULL);
swap(bits[46], bits[47], 1, 0x5555555555555555ULL);
swap(bits[48], bits[56], 8, 0x00ff00ff00ff00ffULL);
swap(bits[49], bits[57], 8, 0x00ff00ff00ff00ffULL);
swap(bits[50], bits[58], 8, 0x00ff00ff00ff00ffULL);
swap(bits[51], bits[59], 8, 0x00ff00ff00ff00ffULL);
swap(bits[52], bits[60], 8, 0x00ff00ff00ff00ffULL);
swap(bits[53], bits[61], 8, 0x00ff00ff00ff00ffULL);
swap(bits[54], bits[62], 8, 0x00ff00ff00ff00ffULL);
swap(bits[55], bits[63], 8, 0x00ff00ff00ff00ffULL);
swap(bits[48], bits[52], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[49], bits[53], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[50], bits[54], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[51], bits[55], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[48], bits[50], 2, 0x3333333333333333ULL);
swap(bits[49], bits[51], 2, 0x3333333333333333ULL);
swap(bits[48], bits[49], 1, 0x5555555555555555ULL);
swap(bits[50], bits[51], 1, 0x5555555555555555ULL);
swap(bits[52], bits[54], 2, 0x3333333333333333ULL);
swap(bits[53], bits[55], 2, 0x3333333333333333ULL);
swap(bits[52], bits[53], 1, 0x5555555555555555ULL);
swap(bits[54], bits[55], 1, 0x5555555555555555ULL);
swap(bits[56], bits[60], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[57], bits[61], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[58], bits[62], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[59], bits[63], 4, 0x0f0f0f0f0f0f0f0fULL);
swap(bits[56], bits[58], 2, 0x3333333333333333ULL);
swap(bits[57], bits[59], 2, 0x3333333333333333ULL);
swap(bits[56], bits[57], 1, 0x5555555555555555ULL);
swap(bits[58], bits[59], 1, 0x5555555555555555ULL);
swap(bits[60], bits[62], 2, 0x3333333333333333ULL);
swap(bits[61], bits[63], 2, 0x3333333333333333ULL);
swap(bits[60], bits[61], 1, 0x5555555555555555ULL);
swap(bits[62], bits[63], 1, 0x5555555555555555ULL);

    }

    /* Check of results */
    for (i = 0; i < count; i++) {
        $type tmp = 0;
        int j;
        for (j = 0; j < $bits; j++) {
            $type bit = ((bits[j] >> i) & 1);
            tmp |= bit << ($bits - j - 1);
        }
        /* tmp = __builtin_bswap64(tmp); */
        if (memcmp(&tmp, keys[i], 8)) {
            printf("check failed %d: %016llx vs %016llx\n", i, tmp, *($type *)keys[i]);
            return 1;
        }
    }

    return 0;
}
