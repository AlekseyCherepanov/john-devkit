# sha1 abstract, with explicit registers

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup(4, 'be')

# 25 is number of registers we use.
r = [new_register() for i in range(25)]

for i in range(16):
    r[i].input()

H = [
    0x67452301,
    0xefcdab89,
    0x98badcfe,
    0x10325476,
    0xc3d2e1f0
]

f = r[17]
temp = r[18]
t = r[19]
# state variables offset
so = 20
a, b, c, d, e = r[so : so + 5]

for i in range(so, so + 5):
    r[i] // H[i - so]

for i in range(80):
    print_verbatim(str(i))
    print_var(a.var)
    if 0 <= i <= 19:
        f // d
        f ^= c
        f &= b
        f ^= d
        k = 0x5A827999
    elif 20 <= i <= 39:
        f // d
        f ^= c
        f ^= b
        k = 0x6ED9EBA1
    elif 40 <= i <= 59:
        f // d
        f &= c
        t // d
        t &= b
        f |= t
        t // b
        t &= c
        f |= t
        k = 0x8F1BBCDC
    elif 60 <= i <= 79:
        f // d
        f ^= c
        f ^= b
        k = 0xCA62C1D6
    # f += e
    # f += k
    temp // a
    temp.rol(5)
    temp += f
    temp += e
    temp += k
    temp += r[i % 16]
    print_var(temp.var)

    # Update W in cyclic manner
    rr = r[i % 16]
    rr ^= r[(i - 3) % 16]
    rr ^= r[(i - 8) % 16]
    rr ^= r[(i - 14) % 16]
    rr.rol(1)

    # We don't copy between registers, we just rename them.

    # e // d
    # d // c
    # c // b
    # c.rol(30)
    # b // a
    # a // temp

    # tt = e
    # e = d
    # d = c
    # c = b
    # c.rol(30)
    # b = a
    # a = tt
    # a // temp

    tt = e
    e = d
    d = c
    c = b
    c.rol(30)
    b = a
    a = temp
    temp = tt

# We've mixed temporary register into set of state registers, so array
# of registers is not in sync with names.
out = [a, b, c, d, e]

for i, j in zip(out, H):
    i += j

for i in out:
    i.swap_to_be()

for i in out:
    i.output()
