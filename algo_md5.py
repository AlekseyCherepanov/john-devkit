# md5 abstract
# https://en.wikipedia.org/wiki/Md5

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('le', 4)

# s specifies the per-round shift amounts
s = [
    7, 12, 17, 22,  7, 12, 17, 22,  7, 12, 17, 22,  7, 12, 17, 22,
    5,  9, 14, 20,  5,  9, 14, 20,  5,  9, 14, 20,  5,  9, 14, 20,
    4, 11, 16, 23,  4, 11, 16, 23,  4, 11, 16, 23,  4, 11, 16, 23,
    6, 10, 15, 21,  6, 10, 15, 21,  6, 10, 15, 21,  6, 10, 15, 21
]
# s = new_array('s', *[new_const(v) for v in s])
# %%
# s = my_const_array('s', s)


K = [
    0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee,
    0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
    0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
    0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
    0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa,
    0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
    0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed,
    0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
    0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
    0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
    0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05,
    0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
    0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039,
    0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
    0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
    0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391
]
# K = new_array('K', *[new_const(v) for v in K])
# %%
# K = my_const_array('K', K)

# Initialize variables:
a0 = 0x67452301   # A
b0 = 0xefcdab89   # B
c0 = 0x98badcfe   # C
d0 = 0x10325476   # D

a0 = new_state_var(a0)
b0 = new_state_var(b0)
c0 = new_state_var(c0)
d0 = new_state_var(d0)

# //Pre-processing: adding a single 1 bit
# append "1" bit to message
# /* Notice: the input bytes are considered as bits strings,
#   where the first bit is the most significant bit of the byte.[47]
# %%

# //Pre-processing: padding with zeros
# append "0" bit until message length in bits ≡ 448 (mod 512)
# append original length in bits mod (2 pow 64) to message
# %%

# Process the message in successive 512-bit chunks:
# %% add support for multiple chunks
for unused in range(1):
    # %% at the moment, padding is out of this code
    M = []
    for i in range(16):
        t = input()
        print_var(t)
        M.append(t)
    # M = make_array('M', 16)
    # for i in range(16):
    #     t = input()
    #     print_var(t)
    #     set_item(M, i, t)
# Initialize hash value for this chunk:
    A = a0
    B = b0
    C = c0
    D = d0
# Main loop:
    for i in range(64):
        # print_verbatim('iter ' + str(i))
        # for v in A, B, C, D:
        #     print_var(v)
        if 0 <= i <= 15:
            # F = (B & C) | ((~B) & D)
            # %% cmov may be used here
            F = D ^ (B & (C ^ D))
            g = i
        elif 16 <= i <= 31:
            # F = (D & B) | ((~D) & C)
            # %% cmov may be used here
            F = C ^ (D & (B ^ C))
            g = (5 * i + 1) % 16
        elif 32 <= i <= 47:
            F = B ^ C ^ D
            g = (3 * i + 5) % 16
        elif 48 <= i <= 63:
            F = C ^ (B | (~D))
            g = (7 * i) % 16
        dTemp = D
        D = C
        C = B
        B = B + rol((A + F + K[i] + M[g]), s[i])
        # print_verbatim("B is " + B.name + "  C is " + C.name)
        A = dTemp
# Add this chunk's hash to result so far:
    a0 = a0 + A
    b0 = b0 + B
    c0 = c0 + C
    d0 = d0 + D
    # a0 // a0 + A
    # b0 // b0 + B
    # c0 // c0 + C
    # d0 // d0 + D

for v in a0, b0, c0, d0:
    # print_var(v)
    output(v)
