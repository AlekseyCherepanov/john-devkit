/*
 * The template is based on rawSHA512_fmt_plug.c from John the Ripper.
 */
/*
 * This file is part of John the Ripper password cracker,
 * Copyright (c) 2010 by Solar Designer
 * based on rawMD4_fmt.c code, with trivial changes by groszek.
 *
 * Rewritten Spring 2013, JimF. SSE code added and released with the following terms:
 * No copyright is claimed, and the software is hereby placed in the public domain.
 * In case this attempt to disclaim copyright and place the software in the public
 * domain is deemed null and void, then the software is Copyright (c) 2011 JimF
 * and it is hereby released to the general public under the following
 * terms:
 *
 * This software may be modified, redistributed, and used for any
 * purpose, in source and binary forms, with or without modification.
 *
 * Modified to be a template for john-devkit in 2015 by Aleksey Cherepanov.
 * Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted.
 *
 *
 * After all, this piece of code is a subject for license of John the Ripper.
 * See LICENSE.jtr in john-devkit or doc/LICENSE in John the Ripper.
 */


#include <stdio.h>
#include <assert.h>

#define printf(...)

/* Comment the above out to enable printf() */

#pragma GCC diagnostic ignored "-Wdeclaration-after-statement"
#pragma GCC diagnostic ignored "-Wstrict-aliasing"

/* #pragma GCC diagnostic ignored "-Wincompatible-pointer-types" */

#pragma GCC diagnostic ignored "-Wunused-but-set-variable"

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

#include "parsing.h"

/* Используется, если в crypt_all() есть проверка результатов */
#include "loader.h"

#if defined __XOP__
#include <x86intrin.h>
#elif defined __SSSE3__
#include <tmmintrin.h>
#endif

#define FORMAT_LABEL		"$format_name"
#define FORMAT_NAME		""
#define ALGORITHM_NAME          "$algo_name"

#define FORMAT_TAG              "$tag"
#define TAG_LENGTH    (sizeof(FORMAT_TAG) - 1)

#define BENCHMARK_COMMENT		""
#define BENCHMARK_LENGTH		-1

#define PLAINTEXT_LENGTH        $plaintext_length
/* Decoded hash is 64 bytes long */
#define BINARY_FORM_SIZE        $binary_form_size
/* After reverse of ops, we store 1 more int. */
#define BINARY_SIZE			BINARY_FORM_SIZE + $size
#define BINARY_ALIGN			MEM_ALIGN_WORD
#define SALT_SIZE				0
#define SALT_ALIGN				1

#define MIN_KEYS_PER_CRYPT		1

/* #if $vectorize */
#define MAX_KEYS_PER_CRYPT		($interleave * $vsize * $batch_size)
/* #else */
/* #define MAX_KEYS_PER_CRYPT		1 */
/* #endif */

/* #define MAX_KEYS_PER_CRYPT		64 */

/* #define CIPHERTEXT_LENGTH		128 */
#define CIPHERTEXT_LENGTH		BINARY_FORM_SIZE * 2


static struct fmt_tests tests[] = {
    $tests
    {NULL}
};


/* from rawSHA512_ng_fmt_plug.c */
/* %% fixed, did not work, why? due to ULL for all constants? */
        /* _mm_srli_epi64(x, ~n + 1), */
        /* _mm_slli_epi64(x, 64 + n) */
#ifndef __XOP__
#define _mm_roti_epi64(x, n)                                              \
(                                                                         \
    _mm_xor_si128 (                                                       \
        _mm_srli_epi64(x, n),                                        \
        _mm_slli_epi64(x, 64 - n)                                         \
    )                                                                     \
)
#define _mm_cmov_si128(y, z, x)                                           \
(                                                                         \
    _mm_xor_si128 (z,                                                     \
        _mm_and_si128 (x,                                                 \
            _mm_xor_si128 (y, z)                                          \
        )                                                                 \
    )                                                                     \
)
#define _mm_roti_epi32(x, n)                                              \
(                                                                         \
    _mm_xor_si128 (                                                       \
        _mm_srli_epi32(x, n),                                        \
        _mm_slli_epi32(x, 32 - n)                                         \
    )                                                                     \
)
#define my_rol_epi32(x, n)                                              \
(                                                                         \
    _mm_xor_si128 (                                                       \
        _mm_slli_epi32(x, n),                                           \
        _mm_srli_epi32(x, 32 - n)                                         \
    )                                                                     \
)
#endif

/* /\* %% это для использования в ассемблере; а если в разных файлах такое будет? *\/ */
/* const unsigned int dk_all_one[] = { 0xFFffFFffU, 0xFFffFFffU, 0xFFffFFffU, 0xFFffFFffU }; */
/* const unsigned int dk_byte_swap_mask[] = { 0x0c0d0e0fU, 0x08090a0bU, 0x04050607U, 0x00010203U }; */
/* const unsigned int dk_asm_byte_swap_mask[] = { 0x00010203U, 0x04050607U, 0x08090a0bU, 0x0c0d0e0fU }; */
/* %% это стоит добавлять через g.asm_global_vars в b_a_begin() */

$asm_global_vars;

/* $constants */
/*         ; */


/* Глобальные переменные для "общения" методов */
/* %% нужен alignment */
/* %% Длина должна быть длиной блока, нужна константа для этого */
/* %% хорошо бы выделять память в init'е, чтобы сократить размер бинарника */

/* static unsigned char saved_key[MAX_KEYS_PER_CRYPT][PLAINTEXT_LENGTH + 1 + 16]; */
/* static $type saved_key[$interleave][(PLAINTEXT_LENGTH + 1 + 16) / $size][$vsize]; */
static $type saved_key[$batch_size][(PLAINTEXT_LENGTH + 1 + 2 * $size) / $size][$interleave][$vsize] $align;

#define saved_key_by_index(i, num) (saved_key[(i) / $vsize / $interleave][(num)][(i) / $vsize % $interleave][(i) % $vsize])

/* static $type crypt_out[MAX_KEYS_PER_CRYPT][1]; */
/* static $type crypt_out[9][MAX_KEYS_PER_CRYPT]; */
/* static $type crypt_out[$interleave][1][$vsize]; */
static $type crypt_out[MAX_KEYS_PER_CRYPT][1][$interleave][$vsize] $align;

#define crypt_out_by_index(i, num) (crypt_out[(i) / $vsize / $interleave][(num)][(i) / $vsize % $interleave][(i) % $vsize])

static void init(struct fmt_main *self)
{
    /* Выделяем память под saved_key, crypt_out и, возможно, saved_key_length. */
}

#define HASH_FORMAT "%*h"
#define HASH_FORMAT_TAGGED FORMAT_TAG HASH_FORMAT

static int valid(char *ciphertext, struct fmt_main *self)
{
    /* Проверка, что хеш данного типа. */

    printf(" valid(): %s\n", ciphertext);

    /* %% Текущий hex проверяет, что длина <= заданной, мне же нужна фиксированная длина. */
    return proc_valid(ciphertext, HASH_FORMAT, BINARY_SIZE)
        || proc_valid(ciphertext, HASH_FORMAT_TAGGED, BINARY_SIZE);
}


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

/* Оригинальный split() */
/* %% было бы отлично делать такое при помощи parsing_plug */
static char *split(char *ciphertext, int index, struct fmt_main *self)
{
    make_static_buf(char, out, TAG_LENGTH + CIPHERTEXT_LENGTH + 1);
	if (!strncmp(ciphertext, FORMAT_TAG, TAG_LENGTH))
		ciphertext += TAG_LENGTH;
	memcpy(out, FORMAT_TAG, TAG_LENGTH);
	memcpy(out + TAG_LENGTH, ciphertext, CIPHERTEXT_LENGTH + 1);
	strlwr(out + TAG_LENGTH);

        /* printf("cip split %s\n", out); */

	return out;
}


static void *binary(char *ciphertext)
{
    /* Декодируем из hex в бинарный хеш в статическом буфере, возвращаем этот буфер. */
    /* Вначале мы положим один инт для реверса и быстрой проверки */
    make_static_buf(unsigned char, buf, BINARY_SIZE);

    /* printf(" binary(): \n"); */
    /* printf("cip1 %s\n", ciphertext); */

    size_t len;
    proc_extract(ciphertext, HASH_FORMAT_TAGGED, &len, buf + $size);

    size_t ii;
#if $input_swap
    for (ii = 1; ii < 9; ii++) {
        (($type *)buf)[ii] = JOHNSWAP$bits((($type *)buf)[ii]);
    }
#endif

/* #if $input_swap */
/* #  define dk_read_input(num) (JOHNSWAP$bits((($type *)buf)[$reverse_num + 1])) */
/* #else */
#  define dk_read_input(num) ((($type *)buf)[$reverse_num + 1])
/* #endif */

#define dk_put_output(var, num) (($type *)buf)[0] = (var)
    $reverse;
#undef dk_put_output
#undef dk_read_input

    {
        printf(">> ");
        for (i = 0; i < BINARY_SIZE; i++) {
            printf("%02x", buf[i]);
        }
        printf("\n");
    }

    return buf;
}


#define make_get_hash(size, mask) \
    static int get_hash_ ## size (int index) { return crypt_out_by_index(index, 0) & mask; }

make_get_hash(0, 0xf);
make_get_hash(1, 0xff);
make_get_hash(2, 0xfff);
make_get_hash(3, 0xffff);
make_get_hash(4, 0xfffff);
make_get_hash(5, 0xffffff);
make_get_hash(6, 0x7ffffff);

#undef make_get_hash


static void set_key(char *key, int index) {
    printf(" set_key(index = %d): %s\n", index, key);
    size_t i;

    const $type *wkey = ($type *)key;

    unsigned int len;
    $type temp;

    len = 0;
    while((unsigned char)(temp = *wkey++)) {

#define make_if(shift, mask) \
        if (!(temp & (0xffULL << ((shift) * 8)))) { \
            saved_key_by_index(index, len / $size) = ((temp & (mask)) | (0x80ULL << ((shift) * 8))); \
            len += (shift); \
            goto key_cleaning; \
        }
        make_if(1, 0xffU);
        make_if(2, 0xffffU);
        make_if(3, 0xffffffU);
#if $size == 8
        make_if(4, 0xffffffffULL);
        make_if(5, 0xffffffffffULL);
        make_if(6, 0xffffffffffffULL);
        make_if(7, 0xffffffffffffffULL);
#endif
#undef make_if

        saved_key_by_index(index, len / $size) = (temp);
        len += $size;
    }
    saved_key_by_index(index, len / $size) = 0x80;

key_cleaning:
    for (i = len / $size + 1; saved_key_by_index(index, i); i++) {
        saved_key_by_index(index, i) = 0;
    }
#if $input_swap
#  define LEN_POS 15
#else
#  define LEN_POS 14
#endif
    saved_key_by_index(index, LEN_POS) = (len << 3);
}

static char *get_key(int index) {
    printf(" get_key(index = %d)\n", index);
    $type s;
    static $type out[(PLAINTEXT_LENGTH + 1) / $size];

    s = saved_key_by_index(index, LEN_POS) >> 3;

    size_t i;
    for (i = 0; i < s / $size + 1; i++) {
        out[i] = saved_key_by_index(index, i);
    }

    ((unsigned char *)out)[s] = 0;
    printf("get_key out %s\n", out);
    return (char*) out;
}

static int crypt_all(int *pcount, struct db_salt *salt)
{
    /* Вычисление хешей: берём из saved_key, результат кладём в crypt_out. */
    int count = *pcount;

    printf("crypt_all(count = %d): \n", count);
    /* fprintf(stdout, "crypt_all(count = %d): \n", count); */

/* #define dk_put_output(var, num) crypt_out[index][(num) + 1] = (var) */

    printf("crypt_all(): before\n");

    size_t batch_index;
    for (batch_index = 0; batch_index < $batch_size; batch_index++) {
    /* for (global_index = 0; global_index < count / $vsize + 1; global_index++) { */

/* #define dk_v_read_input(num) (vshuffle_epi8(_mm_load_si128((__m128i *)saved_key[(num) / $interleave][(num) % $interleave]), swap_endian64_mask)) */
/* #define dk_v_read_input(num) (vshuffle_epi8(_mm_load_si128((__m128i *)saved_key[batch_index][(num) / $interleave][(num) % $interleave]), swap_endian64_mask)) */
#define dk_v_read_input_as_is(num) (_mm_load_si128((__m128i *)saved_key[batch_index][(num) / $interleave][(num) % $interleave]))
/* #define dk_v_read_input(num) (((num) == 14) ? _mm_set1_epi64x(0ULL) : (((num) == 15) ? dk_v_read_input_as_is((num)) : (vshuffle_epi8(dk_v_read_input_as_is((num)), swap_endian64_mask)))) */

#if $input_swap
#  define dk_read_input(num) (((num) == LEN_POS) ? (saved_key_by_index(batch_index, (num))) : (JOHNSWAP$bits(saved_key_by_index(batch_index, (num)))))
#else
#  define dk_read_input(num) (saved_key_by_index(batch_index, (num)))
#endif

#if $input_swap
#  define dk_v_read_input(num) (((num) / $interleave == LEN_POS) ? dk_v_read_input_as_is((num)) : (vshuffle_epi8(dk_v_read_input_as_is((num)), swap_endian${bits}_mask)))
#else
#  define dk_v_read_input(num) dk_v_read_input_as_is((num))
#endif

#define dk_quick_output(var, num) crypt_out[batch_index][0][(num)][0] = (var)
#define dk_put_output(var, num)
#define dk_v_quick_output(var, num) (_mm_store_si128((__m128i *)crypt_out[batch_index][0][(num)], (var)))

/* #define dk_v_put_output(var, num) _mm_store_si128((__m128i *)&(crypt_out[(num) + 1]), (var)) */
#define dk_v_put_output(var, num)
    $code;
#undef dk_put_output
#undef dk_quick_output
#undef dk_read_input

    }

    printf("crypt_all(): after\n");

    /* printf("after crypt_all, with index = 0: %08x\n", get_hash_6(0)); */
    /* printf("after crypt_all, with index = 1: %08x\n", get_hash_6(1)); */
    /* printf("after crypt_all, with index = 63: %08x\n", get_hash_6(63)); */

    return count;
}


static int cmp_all(void *binary, int count)
{
    int i;

    printf("cmp_all($b, count = %d): \n", count);

    /* Without it, gcc gives warning: "array subscript is above array bounds [-Warray-bounds]" */
    assert(count <= MAX_KEYS_PER_CRYPT);

    $type b = (($type *)binary)[0];
    int ii;
    for (ii = 0; ii < count; ii++) {
        $type v = crypt_out_by_index(ii, 0);
        printf("cmp_all loop: my $formatx  b $formatx\n", v, b);
        if (v == b)
            return 1;
    }
    return 0;
}


static int cmp_one(void *binary, int index)
{
    /* quick check */
    if ((($type *)binary)[0] != crypt_out_by_index(index, 0))
        return 0;

    $type out[BINARY_FORM_SIZE / $size + 1];

    /* full computation */
#if $input_swap
#  define dk_read_input(num) (((num) == LEN_POS) ? (saved_key_by_index(index, (num))) : (JOHNSWAP$bits(saved_key_by_index(index, (num)))))
#else
#  define dk_read_input(num) (saved_key_by_index(index, (num)))
#endif

#define dk_quick_output(var, num)
#define dk_put_output(var, num) out[(num) + 1] = (var)
    $scalar;
#undef dk_put_output
#undef dk_quick_output

    {
        int i;
        printf("b  = ");
        for (i = 0; i < BINARY_SIZE; i++) {
            printf("%02x", ((unsigned char *)binary)[i]);
        }
        printf("\nmy = ");
        for (i = 0; i < BINARY_SIZE; i++) {
            printf("%02x", ((unsigned char *)out)[i]);
        }
        printf("\n");
    }

    /* full check */
    for (i = 1; i < BINARY_FORM_SIZE / $size; i++) {
        if ((($type *)binary)[i] != out[i])
            return 0;
    }
    return 1;
}

static int cmp_exact(char *source, int index)
{
    /* cmp_one() checks everything. */
    return 1;
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
		FMT_CASE | FMT_8_BIT | FMT_SPLIT_UNIFIES_CASE /* | FMT_BS */,
#if FMT_MAIN_VERSION > 11
		{ NULL },
#endif
		tests
	}, {
		init,
		fmt_default_done,
		fmt_default_reset,
		fmt_default_prepare,
		valid,
		split,
		binary,
		fmt_default_salt,
#if FMT_MAIN_VERSION > 11
		{ NULL },
#endif
		fmt_default_source,
		{
			fmt_default_binary_hash_0,
			fmt_default_binary_hash_1,
			fmt_default_binary_hash_2,
			fmt_default_binary_hash_3,
			fmt_default_binary_hash_4,
			fmt_default_binary_hash_5,
			fmt_default_binary_hash_6
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
