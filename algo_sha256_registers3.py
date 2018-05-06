# sha256 abstract, with explicit registers and load/store, expanded ror

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('be', 4)
bits = 8 * 4

r = [new_memory() for i in range(16)]
out_vars = [new_memory() for i in range(8)]

for i in range(16):
    r[i] // input()

# state variables indexes
svi = list(range(8))
S = [new_register() for i in svi]
# %% some T* may used for w15, w2 and rr.
T1 = new_register()
T2 = new_register()
T3 = new_register()
T4 = new_register()
w15 = new_register()
w2 = new_register()
rr = new_register()
# register for expanded rotations
rotr = new_register()

# overwrite ror
def new_ror_implementation(self, b):
    # global rotr
    rotr // self
    self >>= b
    # rotr <<= bits - b
    rotr.__ilshift__(bits - b)
    self |= rotr
Register.ror = new_ror_implementation

H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]

k = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]

a, b, c, d, e, f, g, h = S

for i in svi:
    S[i] // H[i]

for i in range(64):

    # print_verbatim(str(i))
    # print_var(a.var)

    t = T1
    s0 = T2

    # s0 = ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)
    t // a
    # print_var(t.var)
    t.ror(2)
    # print_var(t.var)
    s0 // t
    t // a
    t.ror(13)
    s0 ^= t
    t // a
    t.ror(22)
    s0 ^= t

    maj = T3

    # maj = (a & b) ^ (a & c) ^ (b & c)
    t // a
    t &= b
    maj // t
    t // a
    t &= c
    maj ^= t
    t // b
    t &= c
    maj ^= t

    # rename
    t2 = s0
    t2 += maj

    # rename
    ch = maj

    # T1 - t, T2 - t2, T3 - ch
    s1 = T4

    # s1 = ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)
    t // e
    t.ror(6)
    s1 // t
    t // e
    t.ror(11)
    s1 ^= t
    t // e
    t.ror(25)
    s1 ^= t

    # ch = (e & f) ^ (~e & g)
    t // e
    t &= f
    ch // t
    # %% use andnot
    t // e
    t.invert()
    t &= g
    ch ^= t

    # t1 = h + s1 + ch + k[i] + w[i]

    # t1 = ch
    # t1 += h
    # t1 += s1
    # t1 += k[i]
    # t1 += r[i % 16]

    # t1 = ch
    # t1 += h
    # s1 += k[i]
    # t1 += r[i % 16]
    # t1 += s1

    t1 = ch
    s1 += h
    t1 += k[i]
    t1 += s1
    rr.load_from(r[i % 16])
    t1 += rr

    # t1 = ch
    # s1 += h
    # t1 += k[i]
    # s1 += r[i % 16]
    # t1 += s1

    # T1 - t, T2 - t2, T3 - t1, T4 - free

    w2.load_from(r[(i - 2) % 16])
    w15.load_from(r[(i - 15) % 16])
    s0 = T4
    # s0 = ror(w[i - 15], 7) ^ ror(w[i - 15], 18) ^ (w[i - 15] >> 3)
    t // w15
    t.ror(7)
    s0 // t
    t // w15
    t.ror(18)
    s0 ^= t
    t // w15
    t >>= 3
    s0 ^= t

    rr += s0
    s1 = T4

    # s1 = ror(w[i - 2], 17) ^ ror(w[i - 2], 19) ^ (w[i - 2] >> 10)
    t // w2
    t.ror(17)
    s1 // t
    t // w2
    t.ror(19)
    s1 ^= t
    t // w2
    t >>= 10
    s1 ^= t

    # w[i] = w[i - 16] + s0 + w[i - 7] + s1
    t.load_from(r[(i - 7) % 16])
    rr += t
    rr += s1
    # Update W in cyclic manner
    rr.store_to(r[i % 16])

    # h // g
    # g // f
    # f // e
    # e // d
    # e += t1
    # d // c
    # c // b
    # b // a
    # a // t1
    # a += t2

    tt = h
    h = g
    g = f
    f = e
    e = d
    e += t1
    d = c
    c = b
    b = a
    a = tt
    a // t1
    a += t2

    # %% it does not work. see _registers variant.
    # tt = h
    # h = g
    # g = f
    # f = e
    # e = d
    # e += t1
    # d = c
    # c = b
    # b = a
    # a = t1
    # a += t2
    # t2 = tt

# We've mixed temporary register into state registers, so S is not in
# sync with names.
S = [a, b, c, d, e, f, g, h]

for i in svi:
    S[i] += H[i]

for i in svi:
    S[i].swap_to_be()

for i in svi:
    S[i].store_to(out_vars[i])

# for i in svi:
#     print_var(S[i].var)

# for i in svi:
#     out_vars[i] = swap_to_be(out_vars[i])

for i in svi:
    # S[i].output()
    output(out_vars[i])
