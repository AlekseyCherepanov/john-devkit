/* Template for testing */

/* Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted. */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define JOHNSWAP32(x)  (__builtin_bswap32((x)))
#define JOHNSWAP64(x)  (__builtin_bswap64((x)))


unsigned long long pick_number(char * s)
{
    if (s[0] != 'u') {
        printf("wrong, read num from %s\n", s);
        exit(1);
    }
    unsigned long long t = 0;
    size_t i = 1;
    while (s[i] != 0) {
        t <<= 4;
        if ('0' <= s[i] && s[i] <= '9') {
            t += s[i] - '0';
        } else if ('a' <= s[i] && s[i] <= 'f') {
            t += s[i] - 'a' + 10;
        } else {
            printf("bad hex: %s\n", s);
            exit(1);
        }
        i += 1;
    }
    return t;
}

int err(char * msg)
{
    printf("%s\n", msg);
    exit(1);
}

$functions

/* args: f key salt rounds salt2 *data_nums [f ...] */
int main(int argc, char *argv[])
{
    int argv_i = 1;

    unsigned char hex[256] = { 0 };
    for (size_t i = '0'; i <= '9'; i++) {
        hex[i] = i - '0';
    }
    for (size_t i = 'a'; i <= 'f'; i++) {
        hex[i] = i - 'a' + 10;
    }

    size_t sizes[argc];
    for (size_t i = 1; i < argc; i++) {
        sizes[i] = -1;
        if (argv[i][0] == 'b') {
            size_t j;
            for (j = 1; argv[i][j] != 0 && argv[i][j + 1] != 0; j += 2) {
                argv[i][1 + (j - 1) / 2] = (hex[argv[i][j]] << 4) + hex[argv[i][j + 1]];
            }
            sizes[i] = (j - 1) / 2;
            /* printf("%zd: %zd\n", i, sizes[i]); */
        }
    }

    /* for (size_t i = 0; i < argc; i++) { */
    /*     printf("%zd: %s\n", i, argv[i]); */
    /* } */

    /* printf("test %llx test\n", pick_number("u0abcde07")); */
#define get_arg(i) ((i) < argc ? argv[(i)] : (err("out of args"), argv[(i)]))
    while (argv_i < argc) {
        while (argv_i < argc && argv[argv_i][0] != 'f') {
            argv_i++;
        }
        if (argv_i == argc) {
            break;
        }

        /* We may overflow. */
        unsigned char out_buf[1000];
        unsigned char *out_ptr;
        size_t out_ptr_len;

        /* We are on base "pointer" in arg list */
#define dk_input_key() (get_arg(argv_i + 1) + 1)
#define dk_input_key_len() (sizes[(argv_i + 1)])
#define dk_input_salt() (get_arg(argv_i + 2) + 1)
        /* %% вот это не хорошо, соль может содержать нули... */
#define dk_input_salt_len() (sizes[(argv_i + 2)])
#define dk_input_rounds() (pick_number(get_arg(argv_i + 3)))
#define dk_input_salt2() (get_arg(argv_i + 4) + 1)
#define dk_input_salt2_len() (sizes[(argv_i + 4)])
#define dk_output_bytes(s) (out_ptr = s, out_ptr_len = s ## _len)
#define dk_read_input(n) (pick_number(get_arg(argv_i + 5 + (n))))
#define dk_put_output(v, i) ((($type *)out_buf)[(i)] = (v))
        $code;
#undef dk_put_output
#undef dk_read_input

        /* /\* printf("hi there\n"); *\/ */
        /* for (size_t i = 0; i < $output_count * $size; i++) { */
        /*     /\* printf(">>>\n"); *\/ */
        /*     /\* printf("%c", out_buf[i]); *\/ */
        /*     /\* printf("<<<\n"); *\/ */
        /*     fprintf(stderr, "%c", out_buf[i]); */
        /* } */

        /* printf("hi there\n"); */
        for (size_t i = 0; i < out_ptr_len; i++) {
            fprintf(stderr, "%c", out_ptr[i]);
        }

        return 0;

        argv_i++;
    }
    return 0;
}
