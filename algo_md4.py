# md4 abstract
# https://en.wikipedia.org/wiki/Md4
# https://tools.ietf.org/html/rfc1320

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('le', 4)

X = []
for j in range(16):
    t = input()
    X.append(t)

A = new_state_var(0x67452301)
B = new_state_var(0xefcdab89)
C = new_state_var(0x98badcfe)
D = new_state_var(0x10325476)

# F = lambda x, y, z: (x & y) | (~x & z)
F = lambda x, y, z: z ^ (x & (y ^ z))
G = lambda x, y, z: (x & y) | (x & z) | (y & z)
H = lambda x, y, z: x ^ (y ^ z)

AA = A
BB = B
CC = C
DD = D

import re
def make_round(func, code):
    res = ''
    func = re.sub('([abcdks])', r'{\1}', func)
    parts = re.compile(r'\[(.)(.)(.)(.)\s+(\d+)\s+(\d+)\]').findall(code)
    for a, b, c, d, k, s in parts:
        res += func.format(**vars()) + "\n"
    return res

# for i in A, B, C, D: print_var(i)

# X2 = []
# X3 = []
# for i in range(16):
#     X2.append(X[i] + 0x5A827999)
#     X3.append(X[i] + 0x6ED9EBA1)

exec make_round('a = rol((a + F(b, c, d) + X[k]), s)',
'''
        [ABCD  0  3]  [DABC  1  7]  [CDAB  2 11]  [BCDA  3 19]
        [ABCD  4  3]  [DABC  5  7]  [CDAB  6 11]  [BCDA  7 19]
        [ABCD  8  3]  [DABC  9  7]  [CDAB 10 11]  [BCDA 11 19]
        [ABCD 12  3]  [DABC 13  7]  [CDAB 14 11]  [BCDA 15 19]
''')

# for i in A, B, C, D: print_var(i)

exec make_round('a = rol((a + G(b, c, d) + (X[k] + 0x5A827999)), s)',
# exec make_round('a = rol((a + G(b, c, d) + X2[k]), s)',
'''
        [ABCD  0  3]  [DABC  4  5]  [CDAB  8  9]  [BCDA 12 13]
        [ABCD  1  3]  [DABC  5  5]  [CDAB  9  9]  [BCDA 13 13]
        [ABCD  2  3]  [DABC  6  5]  [CDAB 10  9]  [BCDA 14 13]
        [ABCD  3  3]  [DABC  7  5]  [CDAB 11  9]  [BCDA 15 13]
''')

# for i in A, B, C, D: print_var(i)

exec make_round('a = rol((a + H(b, c, d) + (X[k] + 0x6ED9EBA1)), s)',
# exec make_round('a = rol((a + H(b, c, d) + X3[k]), s)',
'''
        [ABCD  0  3]  [DABC  8  9]  [CDAB  4 11]  [BCDA 12 15]
        [ABCD  2  3]  [DABC 10  9]  [CDAB  6 11]  [BCDA 14 15]
        [ABCD  1  3]  [DABC  9  9]  [CDAB  5 11]  [BCDA 13 15]
        [ABCD  3  3]  [DABC 11  9]  [CDAB  7 11]  [BCDA 15 15]
''')

# for i in A, B, C, D: print_var(i)

A += AA
B += BB
C += CC
D += DD

# for i in A, B, C, D: print_var(i)

for v in A, B, C, D:
    output(v)
