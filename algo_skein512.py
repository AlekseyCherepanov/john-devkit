# Abstract skein-512-512

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.
#
# It is based on
# http://www.h2database.com/skein/Skein512.java
# http://www.h2database.com/skein/Skein512Small.java
# Skein 1.3 512-512. Author: Thomas Mueller, 2008-2010. Public domain.

Var.setup(8, 'le')

# R00 = 46, R01 = 36, R02 = 19, R03 = 37;
# R10 = 33, R11 = 27, R12 = 14, R13 = 42;
# R20 = 17, R21 = 49, R22 = 36, R23 = 39;
# R30 = 44, R31 =  9, R32 = 54, R33 = 56;
# R40 = 39, R41 = 30, R42 = 34, R43 = 24;
# R50 = 13, R51 = 50, R52 = 10, R53 = 17;
# R60 = 25, R61 = 29, R62 = 39, R63 = 43;
# R70 =  8, R71 = 35, R72 = 56, R73 = 22;
d = map(lambda c: ord(c) - 32, "ND3EAJ.;1QDGLXV)G>B8-1*R9=GK(6XC")

def block(c, t, b, o, d):
    x = [None] * 8
    # k = [new_const(0)] * 8
    k = b
    # %% c[8] похоже на временную переменную, можно попробовать
    #  % заменить её
    c[8] = new_const(0x1BD11BDAA9FC1A22)
    for i in range(8):
        # for j in reversed(range(8)):
        #     k[i] = (k[i] << 8) + (b[o + i * 8 + j] & 255)
        x[i] = k[i] + c[i]
        c[8] ^= c[i]
    x[5] += t[0]
    x[6] += t[1]
    t[2] = t[0] ^ t[1]

    print_verbatim('k')
    map(print_var, k)
    print_verbatim('t')
    map(print_var, t)
    print_verbatim('x')
    map(print_var, x)

    p = 0
    for r in range(1, 18 + 1, 1):
        # print_verbatim('x ' + str(r))
        # map(print_var, x)
        for i in range(16):
            m = 2 * ((i + (1 + i + i) * (i / 4)) & 3)
            n = (1 + i + i) & 7
            s = d[p + i]
            # print_verbatim('r {0} i {1} s {2} m {3} n {4}'.format(r, i, s, m, n))
            # print_var(x[m])
            # print_var(x[n])
            x[m] += x[n]
            # print_var(x[m])
            # print_var(x[n])
            x[n] = rol(x[n], s) ^ x[m]
            # print_var(x[m])
            # print_var(x[n])
        # print_verbatim('x2 ' + str(r))
        # map(print_var, x)
        for i in range(8):
            x[i] += c[(r + i) % 9]
        x[5] += t[r % 3]
        x[6] += t[(r + 1) % 3]
        x[7] += r
        p ^= 16
    for i in range(8):
        c[i] = k[i] ^ x[i]
    # print_verbatim('c')
    # map(print_var, c)

c = [0] * 9

# это отдельные переменные, однако они "вращаются" в block()
t = [ 32, 0xc4 << 56, 0 ]

# "SHA3\1\0\0\0\0\2"
b = [ 0x0000000133414853, 0x0000000000000200 ] + [0] * 6
b = map(new_const, b)

# map(print_var, b)

# print_verbatim('b')
# map(print_var, b)

block(c, t, b, 0, d)

b = [input() for i in range(8)]

t[0] = 0
t[1] = 0x70 << 56

# %% multiblock here

if args['two_blocks']:
    # first blocks of data if there are more than 1
    t[0] += 64
    block(c, t, b, 0, d)
    t[1] = 0x30 << 56
    may_split_here('before_second_block')
    # %% we don't actually use 2 blocks, that's 80 bytes
    b = [input() for i in range(2)] + [new_const(0)] * 6
    print_verbatim('hi there')
    map(print_var, b)

# last block of data
t[0] = input_length()
t[1] |= 0x80 << 56;
block(c, t, b, 0, d)

# block of zeros
t[0] = 8
t[1] = 0xff << 56
block(c, t, [new_const(0)] * 8, 0, d)

h = c

# There is 1 additional variable. It is not a part of hash
for v in h[:8]:
    print_var(v)
    output(v)
