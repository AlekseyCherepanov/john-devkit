# abstract SHA512
# http://en.wikipedia.org/wiki/SHA512

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('be', 8)

# key = input_key()

w = make_array('w', 80)

# print_var(0x1234)

# Getting in
for i in range(0, 16):
    print_verbatim(">1> " + str(i))
    t = input()
    # t = get_from_key_0x80_padding_length(key)
    # print_verbatim(">2> " + str(i))
    set_item(w, i, t)
    # print_verbatim(">3> " + str(i))
    print_var(t)
    # print_verbatim(">4> " + str(i))
    # print_var(w[i])

# comment('input: {0}', " ".join(str(v) for v in w[0:16]))

# State, Getting in too
H_default = [0x6a09e667f3bcc908, 0xbb67ae8584caa73b, 0x3c6ef372fe94f82b, 0xa54ff53a5f1d36f1, 0x510e527fade682d1, 0x9b05688c2b3e6c1f, 0x1f83d9abfb41bd6b, 0x5be0cd19137e2179]
H = [new_state_var(v) for v in H_default]

k = [
    0x428a2f98d728ae22, 0x7137449123ef65cd, 0xb5c0fbcfec4d3b2f, 0xe9b5dba58189dbbc, 0x3956c25bf348b538,
    0x59f111f1b605d019, 0x923f82a4af194f9b, 0xab1c5ed5da6d8118, 0xd807aa98a3030242, 0x12835b0145706fbe,
    0x243185be4ee4b28c, 0x550c7dc3d5ffb4e2, 0x72be5d74f27b896f, 0x80deb1fe3b1696b1, 0x9bdc06a725c71235,
    0xc19bf174cf692694, 0xe49b69c19ef14ad2, 0xefbe4786384f25e3, 0x0fc19dc68b8cd5b5, 0x240ca1cc77ac9c65,
    0x2de92c6f592b0275, 0x4a7484aa6ea6e483, 0x5cb0a9dcbd41fbd4, 0x76f988da831153b5, 0x983e5152ee66dfab,
    0xa831c66d2db43210, 0xb00327c898fb213f, 0xbf597fc7beef0ee4, 0xc6e00bf33da88fc2, 0xd5a79147930aa725,
    0x06ca6351e003826f, 0x142929670a0e6e70, 0x27b70a8546d22ffc, 0x2e1b21385c26c926, 0x4d2c6dfc5ac42aed,
    0x53380d139d95b3df, 0x650a73548baf63de, 0x766a0abb3c77b2a8, 0x81c2c92e47edaee6, 0x92722c851482353b,
    0xa2bfe8a14cf10364, 0xa81a664bbc423001, 0xc24b8b70d0f89791, 0xc76c51a30654be30, 0xd192e819d6ef5218,
    0xd69906245565a910, 0xf40e35855771202a, 0x106aa07032bbd1b8, 0x19a4c116b8d2d0c8, 0x1e376c085141ab53,
    0x2748774cdf8eeb99, 0x34b0bcb5e19b48a8, 0x391c0cb3c5c95a63, 0x4ed8aa4ae3418acb, 0x5b9cca4f7763e373,
    0x682e6ff3d6b2b8a3, 0x748f82ee5defb2fc, 0x78a5636f43172f60, 0x84c87814a1f0ab72, 0x8cc702081a6439ec,
    0x90befffa23631e28, 0xa4506cebde82bde9, 0xbef9a3f7b2c67915, 0xc67178f2e372532b, 0xca273eceea26619c,
    0xd186b8c721c0c207, 0xeada7dd6cde0eb1e, 0xf57d4f7fee6ed178, 0x06f067aa72176fba, 0x0a637dc5a2c898a6,
    0x113f9804bef90dae, 0x1b710b35131c471b, 0x28db77f523047d84, 0x32caab7b40c72493, 0x3c9ebe0a15c9bebc,
    0x431d67c49c100d4c, 0x4cc5d4becb3e42b6, 0x597f299cfc657e2a, 0x5fcb6fab3ad6faec, 0x6c44198c4a475817
]
k = new_array('k', *[new_const(v) for v in k])

# comment('before extension of w')

i = cycle_const_range('setupW', 16, 80 - 1, 1)

a = w[i - 15]
s0 = ror(a,  1) ^ ror(a,  8) ^ (a >> 7)
b = w[i - 2]
s1 = ror(b, 19) ^ ror(b, 61) ^ (b >> 6)
# %% Parenthesis are significant here. Though they does not affect much.
set_item(w, i, w[i - 16] + s0 + (w[i - 7] + s1))

cycle_end('setupW')

# for i in range(16, 80):
#     s0 = ror(w[i - 15], 1) ^ ror(w[i - 15], 8) ^ (w[i - 15] >> 7)
#     s1 = ror(w[i - 2], 19) ^ ror(w[i - 2], 61) ^ (w[i - 2] >> 6)
#     w[i] = w[i - 16] + s0 + w[i - 7] + s1
# w = new_array('w', *w)

# comment('after extension of w')
# comment('before main loop')

a, b, c, d, e, f, g, h = [new_var() for i in range(8)]
a // H[0]
b // H[1]
c // H[2]
d // H[3]
e // H[4]
f // H[5]
g // H[6]
h // H[7]
# comment('varsbefore ' + "X" + ' ' + ' '.join(str(v) for v in (a, b, c, d, e, f, g, h)))

# print_var(a)
# s0 = ror(a, 28) ^ ror(a, 34) ^ ror(a, 39)
# print_var(ror(a, 28))
# print_var(s0)
# maj = (a & b) ^ (a & c) ^ (b & c)
# print_var(maj)
# t2 = s0 + maj
# print_var(t2)
# s1 = ror(e, 14) ^ ror(e, 18) ^ ror(e, 41)
# print_var(s1)
# ch = (e & f) ^ (~e & g)
# print_var(ch)
# t1 = h + s1 + ch + k[0] + w[0]
# print_var(t1)
# print_var(0xFFFFFF)

# Main loop
i = cycle_const_range('main', 0, 79, 1)

# print_var(a)

s0 = ror(a, 28) ^ ror(a, 34) ^ ror(a, 39)
maj = (a & b) ^ (a & c) ^ (b & c)
t2 = s0 + maj
s1 = ror(e, 14) ^ ror(e, 18) ^ ror(e, 41)
ch = (e & f) ^ (~e & g)
# ** Parenthesis are significant here unless instruction order is not
#  * changed by optimizations.
t1 = h + (s1 + ch) + (k[i] + w[i])
# %% Other variants may be faster; especially when k[i] is not
#  % replaced by a constant explicitly (e.g. no unroll of 'main').
# t1 = h + (s1 + k[i]) + (ch + w[i])
# t1 = s1 + (h + k[i]) + (ch + w[i])

# print_var(a)

h // g
g // f
f // e
e // (d + t1)
d // c
c // b
b // a
a // (t1 + t2)
# comment('vars ' + "X" + ' ' + ' '.join(str(v) for v in (a, b, c, d, e, f, g, h)))

# End of main loop
cycle_end('main')

# a, b, c, d, e, f, g, h = H
# for i in range(64):
#     s0 = ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)
#     maj = (a & b) ^ (a & c) ^ (b & c)
#     t2 = s0 + maj
#     s1 = ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)
#     ch = (e & f) ^ (~e & g)
#     t1 = h + s1 + ch + k[i] + w[i]
#     h = g
#     g = f
#     f = e
#     e = (d + t1)
#     d = c
#     c = b
#     b = a
#     a = (t1 + t2)

# comment('after main loop')

# Updating state
H[0] += a
H[1] += b
H[2] += c
H[3] += d
H[4] += e
H[5] += f
H[6] += g
H[7] += h

label('before_outputs')

# Getting out
for i, v in enumerate(H):
    print_verbatim(">out>1> " + str(i))
    v = swap_to_be(v)
    print_var(v)
    output(v)
    # print_verbatim(">out>2> " + str(i))
