/*
 * This file is part of John the Ripper password cracker,
 * Copyright (c) 1996-2001,2005,2010-2012 by Solar Designer
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted.
 *
 * There's ABSOLUTELY NO WARRANTY, express or implied.
 *
 * Modified to be a template for john-devkit in 2016 by Aleksey Cherepanov.
 * Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
 */


#include <stdio.h>
#include <assert.h>

#define printf(...)

/* Comment the above out to enable printf() */

#pragma GCC diagnostic ignored "-Wdeclaration-after-statement"
#pragma GCC diagnostic ignored "-Wstrict-aliasing"

#pragma GCC optimize 3

#define FMT_STRUCT_NAME fmt_${fmt_struct_name}_dk

#if FMT_EXTERNS_H
extern struct fmt_main FMT_STRUCT_NAME;
#elif FMT_REGISTERS_H
john_register_one(&FMT_STRUCT_NAME);
#else

#include "formats.h"
#include "common.h"

#include "pseudo_intrinsics.h"
#define swap_endian32_mask swap_endian_mask

#include "johnswap.h"
#define JOHNSWAP32 JOHNSWAP


/* %% Не надо ли взять type в скобки? */
/* %% Макросы большими буквами? */
#define make_full_static_buf(type, var, len) static type (var)[(len)]
/* %% А мне нужен alignment здесь? */
#define make_dynamic_static_buf(type, var, len)         \
    static type *var;                                   \
    if (!var)                                           \
        var = mem_alloc_tiny((len), MEM_ALIGN_WORD)

#if 1
#define make_static_buf make_dynamic_static_buf
#else
#define make_static_buf make_full_static_buf
#endif



#include <string.h>

#include "arch.h"
#include "misc.h"
#include "memory.h"
#include "common.h"
#include "formats.h"
#include "memdbg.h"

#define FORMAT_LABEL			"LM-bs-dk"
#define FORMAT_NAME			""

#define BENCHMARK_COMMENT		""
#define BENCHMARK_LENGTH		-1

#define PLAINTEXT_LENGTH		7
#define CIPHERTEXT_LENGTH		32

#define LM_EMPTY			"aad3b435b51404ee"

static struct fmt_tests tests[] = {
	{"$LM$a9c604d244c4e99d", "AAAAAA"},
	{"$LM$cbc501a4d2227783", "AAAAAAA"},
	{"$LM$3466c2b0487fe39a", "CRACKPO"},
	{"$LM$dbc5e5cba8028091", "IMPUNIT"},
	{LM_EMPTY LM_EMPTY, ""},
	{"$LM$73cc402bd3e79175", "SCLEROS"},
	{"$LM$5ecd9236d21095ce", "YOKOHAM"},
	{"$LM$A5E6066DE61C3E35", "ZZZZZZZ"}, /* uppercase encoding */
	{"$LM$1FB363feB834C12D", "ZZZZZZ"}, /* mixed case encoding */
	{NULL}
};

#define ALGORITHM_NAME			"dk"

#define BINARY_SIZE			(sizeof(ARCH_WORD_32) * 2)
#define BINARY_ALIGN			sizeof(ARCH_WORD_32)
#define SALT_SIZE			0
#define SALT_ALIGN			1

#define MIN_KEYS_PER_CRYPT		1
#define MAX_KEYS_PER_CRYPT		64

/* #define MIN_KEYS_PER_CRYPT		DES_BS_DEPTH */
/* #define MAX_KEYS_PER_CRYPT		DES_BS_DEPTH */

static $type saved_key[MAX_KEYS_PER_CRYPT] = { 0 };

static $bstype crypt_out[$bits];

static void init(struct fmt_main *self)
{
}

static char *prepare(char *fields[10], struct fmt_main *self)
{
	if (fields[2] && strlen(fields[2]) == 32)
		return fields[2];
	return fields[1];
}

static int valid(char *ciphertext, struct fmt_main *self)
{
	char *pos;
	char lower[CIPHERTEXT_LENGTH - 16 + 1];

	for (pos = ciphertext; atoi16[ARCH_INDEX(*pos)] != 0x7F; pos++);
	if (!*pos && pos - ciphertext == CIPHERTEXT_LENGTH) {
		strcpy(lower, &ciphertext[16]);
		strlwr(lower);
		if (strcmp(lower, LM_EMPTY))
			return 2;
		else
			return 1;
	}

	if (strncmp(ciphertext, "$LM$", 4)) return 0;

	for (pos = &ciphertext[4]; atoi16[ARCH_INDEX(*pos)] != 0x7F; pos++);
	if (*pos || pos - ciphertext != 20) return 0;

	return 1;
}

static char *split(char *ciphertext, int index, struct fmt_main *self)
{
	static char out[21];

/* We don't just "return ciphertext" for already split hashes since we may
 * need to convert hashes stored by older versions of John to all-lowercase. */
	if (!strncmp(ciphertext, "$LM$", 4))
		ciphertext += 4;

	out[0] = '$';
	out[1] = 'L';
	out[2] = 'M';
	out[3] = '$';

	if (index)
		memcpy(&out[4], &ciphertext[16], 16);
	else
		memcpy(&out[4], ciphertext, 16);

	out[20] = 0;

	strlwr(&out[4]);

	return out;
}

static void *binary(char *ciphertext)
{
    make_static_buf(unsigned char, buf, 8);
    size_t len;
    proc_extract(ciphertext, "$LM$%*h", &len, buf);
    *($type *)buf = JOHNSWAP$bits(*($type *)buf);
    return buf;
}

static char *source(char *source, void *binary)
{
	return split(DES_bs_get_source_LM(binary), 0, NULL);
}

static int binary_hash_0(void *binary)
{
	return *(ARCH_WORD_32 *)binary & 0xF;
}

static int binary_hash_1(void *binary)
{
	return *(ARCH_WORD_32 *)binary & 0xFF;
}

static int binary_hash_2(void *binary)
{
	return *(ARCH_WORD_32 *)binary & 0xFFF;
}

static int binary_hash_3(void *binary)
{
	return *(ARCH_WORD_32 *)binary & 0xFFFF;
}

static int binary_hash_4(void *binary)
{
	return *(ARCH_WORD_32 *)binary & 0xFFFFF;
}

static int binary_hash_5(void *binary)
{
	return *(ARCH_WORD_32 *)binary & 0xFFFFFF;
}

static int binary_hash_6(void *binary)
{
	return *(ARCH_WORD_32 *)binary & 0x7FFFFFF;
}

/* #define make_get_hash(size, mask) \ */
/*     static int get_hash_ ## size (int index) { return crypt_out & mask; } */
/* make_get_hash(0, 0xf); */
/* make_get_hash(1, 0xff); */
/* make_get_hash(2, 0xfff); */
/* make_get_hash(3, 0xffff); */
/* make_get_hash(4, 0xfffff); */
/* make_get_hash(5, 0xffffff); */
/* make_get_hash(6, 0x7ffffff); */
/* #undef make_get_hash */

/* битслайс версия */
/* Сделаем, как в DES_bs_get_hash() в DES_bs.c */
static MAYBE_INLINE int bs_get_hash(int index, int count)
{

    int result;

/* #define GET_BIT(i) ((crypt_out[(i)] & (1ULL << index)) >> index) */
#define GET_BIT(i) ((crypt_out[(i)] & 1ULL))
#define MOVE_BIT(bit) (GET_BIT((bit)) << (bit))

    size_t ii;
    result = 0;
    for (ii = 0; ii < count; ii++) {
        result |= ((crypt_out[64 - 1 - ii] >> (index)) & 1) << ii;
    }
    return result;

	result = GET_BIT(0);
	result |= MOVE_BIT(1);
	result |= MOVE_BIT(2);
	result |= MOVE_BIT(3);
	if (count == 4) return result;

	result |= MOVE_BIT(4);
	result |= MOVE_BIT(5);
	result |= MOVE_BIT(6);
	result |= MOVE_BIT(7);
	if (count == 8) return result;

	result |= MOVE_BIT(8);
	result |= MOVE_BIT(9);
	result |= MOVE_BIT(10);
	result |= MOVE_BIT(11);
	if (count == 12) return result;

	result |= MOVE_BIT(12);
	result |= MOVE_BIT(13);
	result |= MOVE_BIT(14);
	result |= MOVE_BIT(15);
	if (count == 16) return result;

	result |= MOVE_BIT(16);
	result |= MOVE_BIT(17);
	result |= MOVE_BIT(18);
	result |= MOVE_BIT(19);
	if (count == 20) return result;

	result |= MOVE_BIT(20);
	result |= MOVE_BIT(21);
	result |= MOVE_BIT(22);
	result |= MOVE_BIT(23);
	if (count == 24) return result;

	result |= MOVE_BIT(24);
	result |= MOVE_BIT(25);
	result |= MOVE_BIT(26);
#undef GET_BIT
#undef MOVE_BIT

	return result;
}

#define make_get_hash(i, count) \
    static int get_hash_ ## i(int index) { return bs_get_hash(index, (count)); }

make_get_hash(0, 4)
make_get_hash(1, 8)
make_get_hash(2, 12)
make_get_hash(3, 16)
make_get_hash(4, 20)
make_get_hash(5, 24)
make_get_hash(6, 27)

#undef make_get_hash

static int cmp_all(void *binary, int count)
{

    /* битслайс версия */
    /* Like DES_bs_cmp_all in DES_bs.c */
    unsigned long long mask, value;
    value = ((unsigned long long *)binary)[0];
    /* %% порядок тут может быть другим, чтобы с кешем лучше было */
#define X(i) crypt_out[64 - 1 - i] ^ -((value >> i) & 1ULL)
#define O mask |= X(idx); idx++
#define C if (mask == ~0ULL) return 0
    mask = X(0);
    int idx = 1;
    O;
    C;
    /* O; O; C; */
    /* O; O; C; */
    /* O; O; C; */
    /* O; O; C; */
    /* O; O; C; */
    O; O; C;
    O; O; C;
    /* O; C; O; C; */
    /* O; C; O; C; */
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
    O; C; O; C;
#undef X
#undef O
#undef C

    return 1;
}

static int cmp_one(void *binary, int index)
{

    /* битслайс версия */
    size_t i, j;
    int myc, bc = 0;
    for (i = 0; i < BINARY_SIZE * 8; i++) {
        /* if (i % 8 == 0) { */
        /*     printf("> > my %x  b %x\n", myc, bc); */
        /*     bc = myc = 0; */
        /* } */
        unsigned long long mybit = ((crypt_out[i - i % 64 + (64 - 1 - i % 64)] >> index) & 1);
        unsigned long long bbit = ((($type *)binary)[i / 64] & (1ULL << (i % 64)));
        mybit = !!mybit;
        bbit = !!bbit;
        myc |= mybit << (i % 8);
        bc |= bbit << (i % 8);
        /* printf(">> i=%d  my %d  b %d\n", i, mybit, bbit); */
        if (bbit != mybit)
        /* if (i == 80) */
            return 0;
    }
    return 1;

}

static int cmp_exact(char *source, int index)
{
	return 1;
}

static char *get_key(int index)
{
    static char out[8] = { 0 };
    index = 64 - index - 1;
    saved_key[index] = JOHNSWAP$bits(saved_key[index]);
    strncpy(out, &saved_key[index], 7);
    return out;
}

static void set_key(char *key, int index) {
    printf("set_key(%d): %s\n", index, key);
    index = 64 - index - 1;
    strncpy(&saved_key[index], key, 7);
    saved_key[index] = JOHNSWAP$bits(saved_key[index]);
}

static int crypt_all(int *pcount, struct db_salt *salt)
{
    int count = *pcount;

    /* Битслайс версия */

    /* printf("%s\n", &saved_key[0]); */

    /* Укладка кандидатов */

    $bstype bits[$bits], t;
    memcpy(bits, saved_key, sizeof(bits));

#define swap1 swap

#define swap(a0, a1, j, m) \
    t = (a0 ^ (a1 >> j)) & m; \
    a0 ^= t; \
    a1 ^= (t << j);

/* #undef swap */
/* #define swap(...) */

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

#define dk_bs_read_input(num) (bits[(num)])
#define dk_bs_put_output(var, num) (crypt_out[(num)] = (var))
    $code;
#undef dk_bs_put_output
#undef dk_bs_read_input

    return count;
}

struct fmt_main FMT_STRUCT_NAME = {
	{
		FORMAT_LABEL,
		FORMAT_NAME,
		ALGORITHM_NAME,
		BENCHMARK_COMMENT,
		BENCHMARK_LENGTH,
		0,
		PLAINTEXT_LENGTH,
		BINARY_SIZE,
		BINARY_ALIGN,
		SALT_SIZE,
		SALT_ALIGN,
		MIN_KEYS_PER_CRYPT,
		MAX_KEYS_PER_CRYPT,
		FMT_8_BIT | /* FMT_BS | */ FMT_SPLIT_UNIFIES_CASE,
#if FMT_MAIN_VERSION > 11
		{ NULL },
#endif
		tests
	}, {
		init,
		fmt_default_done,
		fmt_default_reset,
		prepare,
		valid,
		split,
		binary,
		fmt_default_salt,
#if FMT_MAIN_VERSION > 11
		{ NULL },
#endif
		source,
		{
			binary_hash_0,
			binary_hash_1,
			binary_hash_2,
			binary_hash_3,
			binary_hash_4,
			binary_hash_5,
			binary_hash_6
		},
		fmt_default_salt_hash,
		NULL,
		fmt_default_set_salt,
		set_key,
		get_key,
		fmt_default_clear_keys,
		crypt_all,
		{
			get_hash_0,
			get_hash_1,
			get_hash_2,
			get_hash_3,
			get_hash_4,
			get_hash_5,
			get_hash_6
		},
		cmp_all,
		cmp_one,
		cmp_exact
	}
};

#endif /* plugin stanza */
