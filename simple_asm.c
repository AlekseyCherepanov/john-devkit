/* Try out of inline assembler */

/* Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted. */

#include <stdio.h>

#include <tmmintrin.h>


register void *rsp asm("rsp");

int main(int argc, char *argv[])
{
    volatile unsigned int a[4] = { 1, 2, 3, 4 };
    volatile unsigned int b[4] = { 0, 0, 0, 0 };

    a[0] = argc;
    a[1] = argc * 2;
    a[2] = argc * 3;
    a[3] = argc * 4;

    printf("a %p(%%rsp)  b %p(%%rsp)\n", (void *)&a - rsp, (void *)&b - rsp);

    /* asm volatile ("movdqa (%rsp), %xmm0\t\n" */
    /*               "movaps %xmm0, 0x10(%rsp)\t\n"); */

    /* asm volatile ("movaps %0, %1" */
    /*               : "=x" (b) : "x" (a)); */

    /* asm volatile ("movdqa %0, %%xmm0\t\n" */
    /*               "movaps %%xmm0, 0x10(%%rsp)\t\n" :: "x" (a) : "memory"); */

    __m128i va, vb;
    va = _mm_load_si128((__m128i *)&a);
    vb = _mm_load_si128((__m128i *)&b);
    /* vb = _mm_add_epi32(va, _mm_set1_epi32(0x1234)); */
    /* vb = _mm_slli_epi32(va, 2); */

    vb = _mm_shuffle_epi8(va, _mm_set_epi32(0x0c0d0e0f, 0x08090a0b, 0x04050607, 0x00010203));

    _mm_store_si128((__m128i *)&b, vb);

    printf("%08x %08x %08x %08x\n", b[0], b[1], b[2], b[3]);

    return 0;
}
