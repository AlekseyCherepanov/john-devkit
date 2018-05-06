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

/* #define printf(...) */

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

#define FORMAT_LABEL			"LM-dk"
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
#define MAX_KEYS_PER_CRYPT		1

/* #define MIN_KEYS_PER_CRYPT		DES_BS_DEPTH */
/* #define MAX_KEYS_PER_CRYPT		DES_BS_DEPTH */

static $type saved_key = 0;
static $type crypt_out = 0;


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

#define make_get_hash(size, mask) \
    static int get_hash_ ## size (int index) { return crypt_out & mask; }

make_get_hash(0, 0xf);
make_get_hash(1, 0xff);
make_get_hash(2, 0xfff);
make_get_hash(3, 0xffff);
make_get_hash(4, 0xfffff);
make_get_hash(5, 0xffffff);
make_get_hash(6, 0x7ffffff);

#undef make_get_hash

static int cmp_all(void *binary, int count)
{
    return *($type *)binary == crypt_out;
}

static int cmp_one(void *binary, int index)
{
    return *($type *)binary == crypt_out;
}

static int cmp_exact(char *source, int index)
{
	return 1;
}

static char *get_key(int index)
{
    static char out[8] = { 0 };
    saved_key = JOHNSWAP$bits(saved_key);
    strncpy(out, &saved_key, 7);
    return out;
}

static void set_key(char *key, int index) {
    strncpy(&saved_key, key, 7);
    saved_key = JOHNSWAP$bits(saved_key);
}

static int crypt_all(int *pcount, struct db_salt *salt)
{
    int count = *pcount;

#define dk_read_input(num) saved_key
#define dk_put_output(var, num) crypt_out = (var)
    $code;
#undef dk_put_output
#undef dk_read_input

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
