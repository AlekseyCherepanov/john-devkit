# sha1 abstract
# https://en.wikipedia.org/wiki/Sha1

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup(4, 'be')

H = [
    0x67452301,
    0xefcdab89,
    0x98badcfe,
    0x10325476,
    0xc3d2e1f0
]
H = [new_state_var(v) for v in H]

w = make_array('w', 80)
for i in range(16):
    t = input()
    # print_var(t)
    set_item(w, i, t)
# i = cycle_const_range('setupW', 16, 32 - 1, 1)
i = cycle_const_range('setupW', 16, 80 - 1, 1)
set_item(w, i, rol((w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]), 1))
cycle_end('setupW')
# i = cycle_const_range('setupW2', 32, 79, 1)
# set_item(w, i, rol((w[i - 6] ^ w[i - 16] ^ w[i - 28] ^ w[i - 32]), 2))
# cycle_end('setupW2')

# w = []
# for i in range(16):
#     t = input()
#     # print_var(t)
#     w.append(t)
# for i in range(16, 80):
#     w.append(rol((w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]), 1))
# # for i in range(16, 32):
# #     w.append(rol((w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]), 1))
# # for i in range(32, 80):
# #     w.append(rol((w[i - 6] ^ w[i - 16] ^ w[i - 28] ^ w[i - 32]), 2))

a, b, c, d, e = H

for i in range(80):
    # print_verbatim('i = ' + str(i))
    # print_var(a)
    if 0 <= i <= 19:
        # f = (b & c) | ((~b) & d)
        f = d ^ (b & (c ^ d))
        k = 0x5A827999
    elif 20 <= i <= 39:
        f = b ^ c ^ d
        k = 0x6ED9EBA1
    elif 40 <= i <= 59:
        f = (b & c) | (b & d) | (c & d)
        # f = (b & c) | (d & (b ^ c))
        # f = (b & c) ^ (b & d) ^ (c & d)
        k = 0x8F1BBCDC
    elif 60 <= i <= 79:
        f = b ^ c ^ d
        k = 0xCA62C1D6
    temp = rol(a, 5) + f + e + k + w[i]
    # print_verbatim('i = ' + str(i))
    # for j in a, b, c, d, e: print_var(j)
    e = d
    d = c
    c = rol(b, 30)
    b = a
    a = temp

# print_verbatim('end')
# for j in a, b, c, d, e: print_var(j)

H[0] += a
H[1] += b
H[2] += c
H[3] += d
H[4] += e

for v in H:
    # v = swap_to_be(v)
    # print_var(v)
    output(v)
