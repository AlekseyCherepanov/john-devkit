/* Simple template: single data / scalar code */
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
 * Modified to be a template for john-devkit by Aleksey Cherepanov.
 * Copyright © 2015,2016 Aleksey Cherepanov <lyosha@openwall.com>
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
#include "base64_convert.h"

#include "pseudo_intrinsics.h"
#define swap_endian32_mask swap_endian_mask

#include "johnswap.h"
#define JOHNSWAP32 JOHNSWAP

#define dk_ror32(a, b) (((a) << (32 - (b))) | ((a) >> (b)))
#define dk_rol32(a, b) (((a) >> (32 - (b))) | ((a) << (b)))
#define dk_ror64(a, b) (((a) << (64 - (b))) | ((a) >> (b)))
#define dk_rol64(a, b) (((a) >> (64 - (b))) | ((a) << (b)))

/* #include "parsing.h" */

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
#if $salted
/* %% how about iterated hash without salt?! */
#define BENCHMARK_LENGTH		0
#else
#define BENCHMARK_LENGTH		-1
#endif

#define PLAINTEXT_LENGTH        $plaintext_length
/* Decoded hash is 64 bytes long */
#define BINARY_FORM_SIZE        $binary_form_size

#define BINARY_SIZE			BINARY_FORM_SIZE
/* %% we make room for 00000000 in skype md5 */
/* #define BINARY_SIZE			(BINARY_FORM_SIZE + 8) */

#define BINARY_ALIGN			MEM_ALIGN_WORD

#if $salted
#define SALT_SIZE				(sizeof(struct cust_salt))
#define SALT_ALIGN				4
#else
#define SALT_SIZE				0
#define SALT_ALIGN				1
#endif

#define MIN_KEYS_PER_CRYPT		1

/* #if $vectorize */
/* #define MAX_KEYS_PER_CRYPT		($interleave * $vsize * $batch_size) */
/* #else */
#define MAX_KEYS_PER_CRYPT		1
/* #endif */

/* #define MAX_KEYS_PER_CRYPT		64 */

/* %% у меня проблема с размером хеша */
#define CIPHERTEXT_LENGTH		2000
/* %% это вариант, когда нет ни соли, ни пользователя */
/* #define CIPHERTEXT_LENGTH		BINARY_FORM_SIZE */


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

#if 0
/* static unsigned char saved_key[MAX_KEYS_PER_CRYPT][PLAINTEXT_LENGTH + 1 + 16]; */
/* static $type saved_key[$interleave][(PLAINTEXT_LENGTH + 1 + 16) / $size][$vsize]; */
static $type saved_key[$batch_size][(PLAINTEXT_LENGTH + 1 + 2 * $size) / $size][$interleave][$vsize] $align;

#define saved_key_by_index(i, num) (saved_key[(i) / $vsize / $interleave][(num)][(i) / $vsize % $interleave][(i) % $vsize])

/* static $type crypt_out[MAX_KEYS_PER_CRYPT][1]; */
/* static $type crypt_out[9][MAX_KEYS_PER_CRYPT]; */
/* static $type crypt_out[$interleave][1][$vsize]; */
static $type crypt_out[MAX_KEYS_PER_CRYPT][1][$interleave][$vsize] $align;

#define crypt_out_by_index(i, num) (crypt_out[(i) / $vsize / $interleave][(num)][(i) / $vsize % $interleave][(i) % $vsize])
#endif

static unsigned char saved_key_bytes[$batch_size][PLAINTEXT_LENGTH + 1];
static unsigned char crypt_out_bytes[$batch_size][BINARY_FORM_SIZE];


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

    $code_valid;
    int res = (r0 == len0);
    printf(" valid() res: %d\n", res);
    return res;

    /* if (strncmp(ciphertext, FORMAT_TAG, TAG_LENGTH)) */
    /*     return 0; */

    /* ciphertext += TAG_LENGTH; */

    /* /\* $tag$hash$salt *\/ */
    /* /\* $tag$hash$salt$$Uusername *\/ */
    /* /\* $tag$hash$HEX$hexed_salt_and_maybe_username *\/ */

    /* size_t i; */
    /* // Not hexadecimal characters */
    /* for (i = 0; ciphertext[i] != '\0' && ciphertext[i] != '$'; i++) { */
    /*     /\* %% we accept lower and upper hex always; it is needed for ColdFusion 11 (dynamic_1588) *\/ */
    /*     if (atoi16[ARCH_INDEX(ciphertext[i])] == 0x7F) */
    /*         return 0; */
    /* } */
    /* if (strcmp(FORMAT_TAG, "$dynamic_1401$") == 0) { */
    /*     if (i != BINARY_FORM_SIZE + 8) */
    /*         return 0; */
    /* } else { */
    /*     if (i != BINARY_FORM_SIZE) */
    /*         return 0; */
    /* } */

    /* ciphertext += i; */
    /* if (ciphertext[0] != '$') */
    /*     return 0; */

    /* /\* skip $ *\/ */
    /* ciphertext += 1; */
    /* if (ciphertext[0] == '\0') */
    /*     return 0; */

    /* if (strncmp(ciphertext, "HEX$", 4) == 0) { */
    /*     ciphertext += 4; */
    /*     // Not hexadecimal characters */
    /*     for (i = 0; ciphertext[i] != '\0'; i++) { */
    /*         /\* printf("hi there %c %d\n", ciphertext[i], atoi16l[ARCH_INDEX(ciphertext[i])]); *\/ */
    /*         if (atoi16[ARCH_INDEX(ciphertext[i])] == 0x7F) */
    /*             return 0; */
    /*     } */
    /*     /\* %% check parity *\/ */
    /* } */

    /* printf("valid end\n"); */
    /* return 1; */

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
	/* if (!strncmp(ciphertext, FORMAT_TAG, TAG_LENGTH)) */
	/* 	ciphertext += TAG_LENGTH; */
	/* memcpy(out, FORMAT_TAG, TAG_LENGTH); */
	/* memcpy(out + TAG_LENGTH, ciphertext, CIPHERTEXT_LENGTH + 1); */
        /* fix for case */
        /* %% proper way */
        /* strcpy(out + TAG_LENGTH, ciphertext); */
        strcpy(out, ciphertext);
        if (strcmp(FORMAT_TAG, "$dynamic_1010$") == 0)
            strlwr(out + TAG_LENGTH);

        printf("cip split %s\n", out);

	return out;
}


static void *binary(char *ciphertext)
{
    /* Декодируем из hex в бинарный хеш в статическом буфере, возвращаем этот буфер. */
    /* Вначале мы положим один инт для реверса и быстрой проверки */
    make_static_buf(unsigned char, buf, BINARY_SIZE);

    /* printf(" binary(): \n"); */
    /* printf("cip1 %s\n", ciphertext); */

    /* memcpy(buf, ciphertext + TAG_LENGTH, BINARY_SIZE); */
    int len;
#define hash buf
#define hash_len len
    $code_binary;
#undef hash
#undef hash_len
    /* valid() should catch all other variants! */
    printf("pre assert: %d, %d\n", len, BINARY_SIZE);
    assert(len == BINARY_SIZE);

    {
        printf("binary: ");
        int i;
        for (i = 0; i < BINARY_SIZE; i++) {
            printf("%02x", buf[i]);
        }
        printf("\n");
    }

    return buf;
}


#define make_get_hash(size, mask) \
    static int get_hash_ ## size (int index) { return ((int *)crypt_out_bytes[index])[0] & mask; }

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
    /* puts(key); */
    strcpy((char *)saved_key_bytes[index], key);
}

static char *get_key(int index) {
    printf(" get_key(index = %d)\n", index);
    static char out[PLAINTEXT_LENGTH + 1];

    strcpy(out, (char *)saved_key_bytes[index]);

    return (char*) out;
}


#if $salted
struct cust_salt {
    /* %% avoid such len */
    unsigned char salt[2000];
    size_t salt_len;
    unsigned char salt2[2000];
    size_t salt2_len;
    unsigned long long rounds;
} *psalt;

static void set_salt(void *salt)
{
	psalt = salt;
}

static void* get_salt(char *ciphertext)
{
    static struct cust_salt s;
    printf("get_salt, begin: %s\n", ciphertext);
    memset(&s, 0, sizeof(struct cust_salt));

#define salt s.salt
#define salt2 s.salt2
#define salt_len s.salt_len
#define salt2_len s.salt2_len
#define rounds s.rounds
    $code_get_salt;
#undef salt
#undef salt2
#undef salt_len
#undef salt2_len
#undef rounds

    /* if (strncmp(ciphertext, FORMAT_TAG, TAG_LENGTH)) */
    /*     return 0; */
    /* ciphertext += TAG_LENGTH; */
    /* ciphertext += BINARY_FORM_SIZE; */
    /* ciphertext += 1; */
    /* printf("gs(): ciph %s\n", ciphertext); */
    /* if (strncmp(ciphertext, "HEX$", 4) == 0) { */
    /*     ciphertext += 4; */
    /*     s.salt_len = strlen(ciphertext) / 2; */
    /*     size_t i; */
    /*     for (i = 0; i < s.salt_len; i++) { */
    /*         s.salt[i] = (atoi16[ARCH_INDEX(ciphertext[i * 2])] << 4) | atoi16[ARCH_INDEX(ciphertext[i * 2 + 1])]; */
    /*     } */
    /* } else { */
    /*     strncpy((char *)s.salt, ciphertext, sizeof(s.salt)); */
    /*     s.salt_len = strlen(ciphertext); */
    /* } */
    /* /\* handle username if any *\/ */
    /* unsigned char * user = (unsigned char *)strstr((char *)s.salt, "$$U"); */
    /* if (user) { */
    /*     user += 3 - 1; */
    /*     strcpy((char *)s.salt2, (char *)user); */
    /*     s.salt2_len = &s.salt[s.salt_len - 1] - user + 1; */
    /*     s.salt_len = user - &s.salt[0] - 3; */
    /* } else { */
    /*     s.salt2_len = 0; */
    /* } */

    /* border for printing */
    s.salt[s.salt_len] = 0;
    s.salt2[s.salt2_len] = 0;

    printf("salt %zd: %s\n", s.salt_len, s.salt);
    printf("salt2 %zd: %s\n", s.salt2_len, s.salt2);
    /* size_t i; */
    /* for (i = 0; ciphertext[i * 2] != '$'; i++) { */
    /*     s.salt[i] = (atoi16l[ARCH_INDEX(ciphertext[i * 2])] << 4) | (atoi16l[ARCH_INDEX(ciphertext[i * 2 + 1])]); */
    /* } */

    return &s;
}
#endif


$functions

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

#define dk_input_key() (saved_key_bytes[batch_index])
#define dk_input_key_len() (strlen((char *)saved_key_bytes[batch_index]))
#define dk_output_bytes(b) (memcpy(crypt_out_bytes[batch_index], (b), BINARY_FORM_SIZE))
#if $salted
#define dk_input_salt() (psalt->salt)
#define dk_input_salt_len() (psalt->salt_len)
#define dk_input_salt2() (psalt->salt2)
#define dk_input_salt2_len() (psalt->salt2_len)
#define dk_input_rounds() (psalt->rounds)
#else
        /* dummy, to not fail linking after mistakes in generator */
#define dk_input_salt() "salt"
#define dk_input_salt_len() 1
#define dk_input_salt2() "salt"
#define dk_input_salt2_len() 1
#define dk_input_rounds() 0
#endif
        $code;

    }

    printf("crypt_all(): after\n");

    return count;
}


static int cmp_all(void *binary, int count)
{
    printf("cmp_all($b, count = %d): \n", count);

    /* Without it, gcc gives warning: "array subscript is above array bounds [-Warray-bounds]" */
    assert(count <= MAX_KEYS_PER_CRYPT);

    int ii;
    for (ii = 0; ii < count; ii++) {
        printf(">> %s\n", binary);
        printf(">> %s\n", crypt_out_bytes[ii]);
        if (!memcmp(crypt_out_bytes[ii], binary, BINARY_FORM_SIZE))
            return 1;
    }
    return 0;
}


static int cmp_one(void *binary, int index)
{
    return !memcmp(crypt_out_bytes[index], binary, BINARY_FORM_SIZE);
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
		FMT_CASE | FMT_8_BIT /* | FMT_SPLIT_UNIFIES_CASE */ /* | FMT_BS */,
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
#if $salted
		get_salt,
#else
		fmt_default_salt,
#endif
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
#if $salted
		set_salt,
#else
		fmt_default_set_salt,
#endif
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
