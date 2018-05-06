/* Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted. */

#pragma OPENCL EXTENSION cl_amd_printf : enable

#define SWAP4(x) as_uint(as_uchar4(x).wzyx)
#define SWAP8(x) as_ulong(as_uchar8(x).s76543210)

#define JOHNSWAP64 SWAP8
#define JOHNSWAP32 SWAP4

#if $bs

/* #define printf(...) printf((__constant char *)__VA_ARGS__) */

$constants;

__kernel void compute_bs(__global uint* in, volatile __global uint* result)
{
    uint gid = get_global_id(0);

    /* if (gid != 0) */
    /*     return; */

    /* printf((__constant char *)"hi there %u\n", gid); */

    /* for (int i = 0; i < 16 * 32; i++) { */
    /*     printf("%08x", in[i]); */
    /* } */
    /* printf("\n"); */

#define dk_bs_read_input(num) (in[(num)])
#define dk_bs_put_output(var, num) result[gid * 8 * 32 + (num)] = (var)
/* #define dk_bs_put_output(var, num) result[gid] = var */
/* #define dk_bs_put_output(var, num) result[gid] = 0 */

/*     uint test_res = 0; */
/* #define dk_bs_put_output(var, num) test_res += var */

/* #define dk_bs_put_output(var, num) */
#define dk_quick_output(var, num)

    $code;

    /* result[gid] = 0; */
    /* result[gid] = test_res; */

    /* for (int i = 0; i < 32 * 8; i++) { */
    /*     out[i] = in[i]; */
    /* } */

}

#else

/* #ifndef WORKSIZE */
/* #define WORKSIZE 256 */
/* #endif */
/*  */
/* __attribute__((reqd_work_group_size(WORKSIZE, 1, 1))) */
__kernel void compute(__global uint* in, volatile __global uint* out)
{
    uint gid = get_global_id(0);

#define dk_read_input(num) JOHNSWAP32(in[(num)])
#define dk_put_output(var, num) out[gid * 8 + (num)] = JOHNSWAP32(var)
#define dk_quick_output(var, num)
    $code;

    /* if (gid == 0) { */
    /*     for (int i = 0; i < 16; i++) { */
    /*         printf("%08x", dk_read_input(i)); */
    /*     } */
    /*     printf("\n"); */
    /* } */
    /* printf("%d\n", gid); */

}

#endif
