# LM abstract
# https://en.wikipedia.org/wiki/LM_hash
# https://en.wikipedia.org/wiki/Data_Encryption_Standard#Overall_structure
# https://en.wikipedia.org/wiki/DES_supplementary_material

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup(8, 'be')

# %% надо проверять, что все использованы, часть продублирована
expand = permute
# %% надо проверять, что использована часть, нет повторов
choice = permute
# %% permute должен проверять, что всё использовано, нет повторов

# def sbox(value, table):
#     return table[value]

# DES

# We'll numerate from 0
def dec1(table):
    for i in range(len(table)):
        table[i] -= 1

# Initial permutation: 1st bit of output <- 58th bit of input
ip = [
    58, 50, 42, 34, 26, 18, 10, 2,
    60, 52, 44, 36, 28, 20, 12, 4,
    62, 54, 46, 38, 30, 22, 14, 6,
    64, 56, 48, 40, 32, 24, 16, 8,
    57, 49, 41, 33, 25, 17,  9, 1,
    59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5,
    63, 55, 47, 39, 31, 23, 15, 7
]
dec1(ip)

def invert_permute(t):
    r = [None for i in range(len(t))]
    for i in range(len(t)):
        r[t[i]] = i
    assert r.count(None) == 0
    return r
ip1 = invert_permute(ip)

# LM specific twist: switch all pairs of adjacent bits
for i in range(0, len(ip1), 2):
    ip1[i], ip1[i + 1] = ip1[i + 1], ip1[i]

# LM specific: 7 bytes -> 8 bytes with 8th to be dropped later
to8 = [
     0,  1,  2,  3,  4,  5,  6, 0,
     7,  8,  9, 10, 11, 12, 13, 0,
    14, 15, 16, 17, 18, 19, 20, 0,
    21, 22, 23, 24, 25, 26, 27, 0,
    28, 29, 30, 31, 32, 33, 34, 0,
    35, 36, 37, 38, 39, 40, 41, 0,
    42, 43, 44, 45, 46, 47, 48, 0,
    49, 50, 51, 52, 53, 54, 55, 0
]

pc1left = [
    57, 49, 41, 33, 25, 17, 9,
     1, 58, 50, 42, 34, 26, 18,
    10,  2, 59, 51, 43, 35, 27,
    19, 11,  3, 60, 52, 44, 36
]
dec1(pc1left)

pc1right = [
    63, 55, 47, 39, 31, 23, 15,
     7, 62, 54, 46, 38, 30, 22,
    14,  6, 61, 53, 45, 37, 29,
    21, 13,  5, 28, 20, 12,  4
]
dec1(pc1right)

pc1 = pc1left + pc1right

pc2 = [
    14, 17, 11, 24,  1,  5,  3, 28,
    15,  6, 21, 10, 23, 19, 12,  4,
    26,  8, 16,  7, 27, 20, 13,  2,
    41, 52, 31, 37, 47, 55, 30, 40,
    51, 45, 33, 48, 44, 49, 39, 56,
    34, 53, 46, 42, 50, 36, 29, 32
]
dec1(pc2)

key_rotations = [ 1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1 ]

E = [
    32 , 1,  2,  3,  4,  5,
     4,  5,  6,  7,  8,  9,
     8,  9, 10, 11, 12, 13,
    12, 13, 14, 15, 16, 17,
    16, 17, 18, 19, 20, 21,
    20, 21, 22, 23, 24, 25,
    24, 25, 26, 27, 28, 29,
    28, 29, 30, 31, 32,  1
]
dec1(E)

P = [
    16,  7, 20, 21, 29, 12, 28, 17,
     1, 15, 23, 26,  5, 18, 31, 10,
     2,  8, 24, 14, 32, 27,  3,  9,
    19, 13, 30,  6, 22, 11,  4, 25
]
dec1(P)

# after `perl -lpe 's/\s+/ /g'`
sboxes_str = '''
S1
 x0000x x0001x x0010x x0011x x0100x x0101x x0110x x0111x x1000x x1001x x1010x x1011x x1100x x1101x x1110x x1111x
0yyyy0 14 4 13 1 2 15 11 8 3 10 6 12 5 9 0 7
0yyyy1 0 15 7 4 14 2 13 1 10 6 12 11 9 5 3 8
1yyyy0 4 1 14 8 13 6 2 11 15 12 9 7 3 10 5 0
1yyyy1 15 12 8 2 4 9 1 7 5 11 3 14 10 0 6 13
S2
 x0000x x0001x x0010x x0011x x0100x x0101x x0110x x0111x x1000x x1001x x1010x x1011x x1100x x1101x x1110x x1111x
0yyyy0 15 1 8 14 6 11 3 4 9 7 2 13 12 0 5 10
0yyyy1 3 13 4 7 15 2 8 14 12 0 1 10 6 9 11 5
1yyyy0 0 14 7 11 10 4 13 1 5 8 12 6 9 3 2 15
1yyyy1 13 8 10 1 3 15 4 2 11 6 7 12 0 5 14 9
S3
 x0000x x0001x x0010x x0011x x0100x x0101x x0110x x0111x x1000x x1001x x1010x x1011x x1100x x1101x x1110x x1111x
0yyyy0 10 0 9 14 6 3 15 5 1 13 12 7 11 4 2 8
0yyyy1 13 7 0 9 3 4 6 10 2 8 5 14 12 11 15 1
1yyyy0 13 6 4 9 8 15 3 0 11 1 2 12 5 10 14 7
1yyyy1 1 10 13 0 6 9 8 7 4 15 14 3 11 5 2 12
S4
 x0000x x0001x x0010x x0011x x0100x x0101x x0110x x0111x x1000x x1001x x1010x x1011x x1100x x1101x x1110x x1111x
0yyyy0 7 13 14 3 0 6 9 10 1 2 8 5 11 12 4 15
0yyyy1 13 8 11 5 6 15 0 3 4 7 2 12 1 10 14 9
1yyyy0 10 6 9 0 12 11 7 13 15 1 3 14 5 2 8 4
1yyyy1 3 15 0 6 10 1 13 8 9 4 5 11 12 7 2 14
S5
 x0000x x0001x x0010x x0011x x0100x x0101x x0110x x0111x x1000x x1001x x1010x x1011x x1100x x1101x x1110x x1111x
0yyyy0 2 12 4 1 7 10 11 6 8 5 3 15 13 0 14 9
0yyyy1 14 11 2 12 4 7 13 1 5 0 15 10 3 9 8 6
1yyyy0 4 2 1 11 10 13 7 8 15 9 12 5 6 3 0 14
1yyyy1 11 8 12 7 1 14 2 13 6 15 0 9 10 4 5 3
S6
 x0000x x0001x x0010x x0011x x0100x x0101x x0110x x0111x x1000x x1001x x1010x x1011x x1100x x1101x x1110x x1111x
0yyyy0 12 1 10 15 9 2 6 8 0 13 3 4 14 7 5 11
0yyyy1 10 15 4 2 7 12 9 5 6 1 13 14 0 11 3 8
1yyyy0 9 14 15 5 2 8 12 3 7 0 4 10 1 13 11 6
1yyyy1 4 3 2 12 9 5 15 10 11 14 1 7 6 0 8 13
S7
 x0000x x0001x x0010x x0011x x0100x x0101x x0110x x0111x x1000x x1001x x1010x x1011x x1100x x1101x x1110x x1111x
0yyyy0 4 11 2 14 15 0 8 13 3 12 9 7 5 10 6 1
0yyyy1 13 0 11 7 4 9 1 10 14 3 5 12 2 15 8 6
1yyyy0 1 4 11 13 12 3 7 14 10 15 6 8 0 5 9 2
1yyyy1 6 11 13 8 1 4 10 7 9 5 0 15 14 2 3 12
S8
 x0000x x0001x x0010x x0011x x0100x x0101x x0110x x0111x x1000x x1001x x1010x x1011x x1100x x1101x x1110x x1111x
0yyyy0 13 2 8 4 6 15 11 1 10 9 3 14 5 0 12 7
0yyyy1 1 15 13 8 10 3 7 4 12 5 6 11 0 14 9 2
1yyyy0 7 11 4 1 9 12 14 2 0 6 10 13 15 3 5 8
1yyyy1 2 1 14 7 4 10 8 13 15 12 9 0 3 5 6 11
'''

def split_sboxes():
    r = []
    ss = sboxes_str.split('S')
    for s in ss[1:]:
        ls = s.split('\n')
        sbox = [0 for i in range(64)]
        # sbox_number = int(ls[0])
        xs = ls[1].split(' ')
        for l in ls[2:-1]:
            ns = l.split(' ')
            y = ns[0]
            for i in range(1, len(xs)):
                idx = y[0] + xs[i][1:-1] + y[-1]
                idx = int(idx, 2)
                sbox[idx] = int(ns[i])
        r.append(sbox)
    return r

sboxes = split_sboxes()

# End of tables

for i in 'ip', 'ip1', 'pc1', 'pc2', 'P', 'E', 'to8':
    exec("{0} = new_array('{0}', *{0})".format(i))

for i in range(len(sboxes)):
    sboxes[i] = new_array('S{0}'.format(i + 1), *sboxes[i])

# Code

def split(d):
    l = d & 0xFFffFFff00000000
    r = d << 32
    return l, r

# 64 bits -> 16 x 48 bits
def key_schedule(key):
    result = []
    key = choice(key, pc1)
    for i in key_rotations:
        if i == 1:
            mask = ((1 << (64 - 28)) | (1 << (64 - 2*28)))
            key = ((key << 1) & ~mask) | ((key >> 27) & mask)
        else: # i == 2
            mask = ((3 << (64 - 28)) | (3 << (64 - 2*28)))
            key = ((key << 2) & ~mask) | ((key >> 26) & mask)
        subkey = choice(key, pc2)
        result.append(subkey)
    return result

def F(half_block, subkey):
    expanded = expand(half_block, E)
    xored = subkey ^ expanded
    parts = []
    xored >>= 64 - 48
    for i in range(8):
        parts.append((xored >> (i * 6)) & 63)
    get_part = lambda: parts.pop()
    r = new_const(0)
    for i in range(8):
        v = get_part()
        n = sbox(v, sboxes[i])
        r <<= 4
        r += n
    # %% биты у нас справа, приходится влево двигать
    r <<= 32
    r = permute(r, P)
    return r

def join(l, r):
    r >>= 32
    l += r
    return l

def des(key, data):
    d = permute(data, ip)
    l, r = split(d)
    subkeys = key_schedule(key)
    get_subkey = lambda: subkeys.pop(0)
    for i in range(16):
        subkey = get_subkey()
        f = F(r, subkey)
        r2 = f ^ l
        l, r = r, r2
    t = join(l, r)
    result = permute(t, ip1)
    return result

# LM

# big endian
def str_to_int(string):
    r = 0
    for c in string:
        r <<= 8
        r += ord(c)
    return r

lm_magic = "KGS!@#$%"
lm_magic = str_to_int(lm_magic)

# We get 1 half on input
candidate = input()
print_var(candidate)
# %% scalar version would be faster if to8 and ip tables are combined.
candidate = expand(candidate, to8)
r = des(candidate, lm_magic)
print_var(r)
output(r)

