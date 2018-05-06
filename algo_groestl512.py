# abstract groestl
# %% only -512 version

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup(8, 'be')

ot_enabled = False

rounds = 14
# rounds = 1

ROWS = 8
columns = 16

def print_state(mark, h):
    print_verbatim(mark)
    for i in range(ROWS):
        for j in range(2):
            print_verbatim('h {0} {1}'.format(i, j))
            print_var(h[i][j])

def print_bytes(mark, x):
    print_verbatim(mark)
    for i in range(ROWS):
        for j in range(columns):
            print_verbatim('x {0} {1}'.format(i, j))
            print_var(x[i][j])

S = [
  0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5,
  0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
  0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0,
  0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
  0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc,
  0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
  0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a,
  0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
  0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0,
  0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
  0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b,
  0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
  0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85,
  0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
  0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5,
  0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
  0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17,
  0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
  0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88,
  0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
  0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c,
  0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
  0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9,
  0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
  0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6,
  0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
  0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e,
  0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
  0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94,
  0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
  0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68,
  0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
]

S = new_array('S', *S)

Shift = [ [0,1,2,3,4,5,6,11], [1,3,5,11,0,2,4,6] ]

def AddRoundConstant(x, round, v):
    # print_bytes('AddRoundConstant inner before', x)
    if v & 1:
        # Q variant
        for i in range(columns):
            for j in range(ROWS - 1):
                x[j][i] ^= 0xff
        for i in range(columns):
            x[ROWS - 1][i] ^= (i << 4) ^ 0xff ^ round
    else:
        # P variant
        for i in range(columns):
            x[0][i] ^= (i << 4) ^ round
    # print_bytes('AddRoundConstant inner after', x)
    # if round == 2:
    #     debug_exit()

def SubBytes(x):
    for i in range(ROWS):
        for j in range(columns):
            x[i][j] = sbox(x[i][j], S)

def ShiftBytes(x, v):
    R = Shift[v & 1]
    temp = [None] * columns
    for i in range(ROWS):
        for j in range(columns):
            temp[j] = x[i][(j + R[i]) % columns]
        for j in range(columns):
            x[i][j] = temp[j]

mul1 = lambda b: b
def mul2(b):
    b7 = b & 0x80
    t = (b << 1) & 0xff
    t ^= (b7 >> 3)
    t ^= (b7 >> 4)
    t ^= (b7 >> 6)
    t ^= (b7 >> 7)
    return t
mul3 = lambda b: mul2(b) ^ mul1(b)
mul4 = lambda b: mul2(mul2(b))
mul5 = lambda b: mul4(b) ^ mul1(b)
mul6 = lambda b: mul4(b) ^ mul2(b)
mul7 = lambda b: mul4(b) ^ mul2(b) ^ mul1(b)
mul = [None] + [eval("mul" + str(i)) for i in range(1, 8, 1)]

# mul1 = lambda b: b
# mul2 = lambda b: ((b << 1) ^ 0x1b if b >> 7 else (b << 1)) & 0xff
# # mul2 = lambda b: ((b << 1) ^ 0x1b if b & 0x80 else (b << 1)) & 0xff
# mul3 = lambda b: mul2(b) ^ mul1(b)
# mul4 = lambda b: mul2(mul2(b))
# mul5 = lambda b: mul4(b) ^ mul1(b)
# mul6 = lambda b: mul4(b) ^ mul2(b)
# mul7 = lambda b: mul4(b) ^ mul2(b) ^ mul1(b)
# mul = [None] + [eval("mul" + str(i)) for i in range(1, 8, 1)]
# mul_tables = []
# for mf in mul[1:]:
#     mul_tables.append([mf(i) for i in range(256)])
# mul_tables = map(lambda t: new_array('t', *t), mul_tables)
# mul = [t.__getitem__ for t in mul_tables]
# mul = [None] + mul

def MixBytes(x):
    temp = [None] * ROWS
    # from copy import deepcopy
    # x = deepcopy(x)
    # print >> sys.stderr, x
    # exit(1)
    # if ot_enabled:
    #     print_bytes('MixBytes inner before', x)
    for i in range(columns):
        # print >> sys.stderr, i
        for j in range(ROWS):
            # temp[j] = (  mul2(x[(j + 0) % ROWS][i])
            #            ^ mul2(x[(j + 1) % ROWS][i])
            #            ^ mul3(x[(j + 2) % ROWS][i])
            #            ^ mul4(x[(j + 3) % ROWS][i])
            #            ^ mul5(x[(j + 4) % ROWS][i])
            #            ^ mul3(x[(j + 5) % ROWS][i])
            #            ^ mul5(x[(j + 6) % ROWS][i])
            #            ^ mul7(x[(j + 7) % ROWS][i]))
            temp[j] = new_const(0)
            # temp[j] = 0
            for m, k in zip([2, 2, 3, 4, 5, 3, 5, 7], range(8)):
                temp[j] ^= mul[m](x[(j + k) % ROWS][i])
        for j in range(ROWS):
            x[j][i] = temp[j]
    # if ot_enabled:
    #     print_bytes('MixBytes inner after', x)
    #     debug_exit()

def PQ(h, v):
    x = h
    # work
    for i in range(rounds):
        AddRoundConstant(x, i, v)
        SubBytes(x)
        ShiftBytes(x, v)
        MixBytes(x)

def P(x):
    v = 0
    PQ(x, v)

def Q(x):
    v = 1
    PQ(x, v)

def f(h, m):
    # P(h ^ m) ^ Q(m) ^ h
    # %% associativity
    # h = xor(xor(P(xor(h, m)), Q(m)), h)

    from copy import deepcopy

    # new_m = [[None] * 2 for i in range(8)]
    # for i in range(ROWS):
    #     for j in range(2):
    #         new_m[i][j] = m[j * ROWS + i]

    new_m = m
    new_m2 = deepcopy(new_m)

    for i in range(ROWS):
        for j in range(columns):
            new_m[i][j] ^= h[i][j]
    P(new_m)
    hp = new_m

    # print_bytes('hp', hp)

    nm = new_m2
    Q(nm)
    hq = nm

    for i in range(ROWS):
        for j in range(columns):
            h[i][j] ^= hq[i][j] ^ hp[i][j]
            # print_var(h[i][j])

    return h

def output_transformation(h):
    global ot_enabled
    ot_enabled = True
    # P(h) ^ h
    h2 = map(list, h)
    # from copy import deepcopy
    # h2 = deepcopy(h)
    P(h2)
    # print_verbatim('h')
    # for i in range(ROWS):
    #     for j in range(2):
    #         print_var(h[i][j])
    # print_verbatim('h2')
    # for i in range(ROWS):
    #     for j in range(2):
    #         print_var(h2[i][j])
    # print_verbatim('h xored')
    for i in range(ROWS):
        for j in range(columns):
            h[i][j] ^= h2[i][j]
            # print_var(h[i][j])
    return h

M = [input() for i in range(16)]
M[14] = new_const(0)
M[15] = new_const(1)
m = [[None] * columns for i in range(ROWS)]
for row in range(ROWS):
    for col in range(columns):
        m[row][col] = (M[col] >> ((8 - 1 - row) * 8)) & 0xff
M = m

# print_bytes('M', M)

h = [[new_const(0)] * columns for i in range(ROWS)]
h[6][15] = new_const(2)

# print_bytes('h', h)

h = f(h, M)

# print_bytes('after f', h)

# print_state('f, before OT', h)

h = output_transformation(h)

# print_bytes('after OT', h)

# Collect bytes by columns from columns 8-15
# %% transpose efficiently here?
out = [new_const(0)] * 8
for col in range(columns / 2):
    for row, l in enumerate(h):
        # out[col] |= ((l[1] >> ((8 - 1 - col) * 8)) & 0xff) << ((8 - 1 - row) * 8)
        out[col] |= l[8 + col] << ((8 - 1 - row) * 8)

for v in out:
    output(v)


