# -*- coding: utf-8 -*-
# Tool to run tests against bitsliced bytecode without compilation
# %% currently for sha256 only

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from copy import deepcopy
from bytecode_main import bs_swap_bytes
import hashlib

import bytecode_main as B
from util_main import *

bc_file = sys.argv[1]

code = B.slurp_bytecode(bc_file)

# мы загрузили код, теперь мы хотим сделать тесты

# # sha256
# tests = [
#     ["71c3f65d17745f05235570f1799d75e69795d469d9fcb83e326f82f1afa80dea", "epixoip"],
#     ["25b64f637b373d33a8aa2b7579784e99a20e6b7dfea99a71af124394b8958f27", "doesthiswork"],
#     ["5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", "password"]
# ]
# for i in range(64 - 2 * 4 - 1):
#     c = 'x' * i
#     h = hashlib.new('sha256')
#     h.update(c)
#     t = h.hexdigest()
#     tests.append([t, c])

# # full skeincoin
# tests = [
#     ["40d1ccf1ad80966fc41bb8b0b6246bc5ce881accd20d5bb71a35a46300000000", "\x02\x00\x00\x00\x9d\x7a\xd1\xa2\x53\xb0\xa7\x57\x21\x34\x85\xe5\xb0\x23\x3e\xaa\x09\x37\x51\x13\x96\xd9\xbc\xc5\xb0\xf7\x34\x24\x00\x00\x00\x00\x9a\x46\x11\xe0\x25\x34\x27\xec\x6b\x35\x6d\x4b\x61\x52\x14\x34\x32\x7d\xb2\x90\x80\x22\x08\x2f\x40\x43\xe6\xb7\x21\xd8\x84\xf1\xbc\xf0\x02\x56\xe8\xd6\x7b\x1c\x3a\x0b\xc7\x56"],
#     ["4ed421fae24da5b0bfa55c1c01c7b58015726ccba215280a9b832d6925eaa7fe", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
# ]

# # first part of skeincoin
# tests = [
#     ["a2dc7a53be23fc3c2b34b052a7c5d043afa556ba8365064de69ae26794c49eac0809391ba853d29ff258b44198ff16cacea51f1e73dd9514fce35e28f5af11bb", "\x02\x00\x00\x00\x9d\x7a\xd1\xa2\x53\xb0\xa7\x57\x21\x34\x85\xe5\xb0\x23\x3e\xaa\x09\x37\x51\x13\x96\xd9\xbc\xc5\xb0\xf7\x34\x24\x00\x00\x00\x00\x9a\x46\x11\xe0\x25\x34\x27\xec\x6b\x35\x6d\x4b\x61\x52\x14\x34\x32\x7d\xb2\x90\x80\x22\x08\x2f\x40\x43\xe6\xb7"],
#     ["3b04f5126fffb97a2e76906f392c33ab3e1793651ac8457223ad6dcf68572cf0def1642cc95f5db2a2adf3f232a43ff03c4fdc318cfec339b23ea2f212aa574d", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
# ]

# second part of skeincoin
# 16 byte tail of data + output of first part with swapped bytes
tests = [
    ["40d1ccf1ad80966fc41bb8b0b6246bc5ce881accd20d5bb71a35a46300000000", "\x21\xd8\x84\xf1\xbc\xf0\x02\x56\xe8\xd6\x7b\x1c\x3a\x0b\xc7\x56\x3c\xfc\x23\xbe\x53\x7a\xdc\xa2\x43\xd0\xc5\xa7\x52\xb0\x34\x2b\x4d\x06\x65\x83\xba\x56\xa5\xaf\xac\x9e\xc4\x94\x67\xe2\x9a\xe6\x9f\xd2\x53\xa8\x1b\x39\x09\x08\xca\x16\xff\x98\x41\xb4\x58\xf2\x14\x95\xdd\x73\x1e\x1f\xa5\xce\xbb\x11\xaf\xf5\x28\x5e\xe3\xfc"],
    ["4ed421fae24da5b0bfa55c1c01c7b58015726ccba215280a9b832d6925eaa7fe", "xxxxxxxxxxxxxxxx\x7a\xb9\xff\x6f\x12\xf5\x04\x3b\xab\x33\x2c\x39\x6f\x90\x76\x2e\x72\x45\xc8\x1a\x65\x93\x17\x3e\xf0\x2c\x57\x68\xcf\x6d\xad\x23\xb2\x5d\x5f\xc9\x2c\x64\xf1\xde\xf0\x3f\xa4\x32\xf2\xf3\xad\xa2\x39\xc3\xfe\x8c\x31\xdc\x4f\x3c\x4d\x57\xaa\x12\xf2\xa2\x3e\xb2"],
]

# режем тесты в биты

def swap(bits, size):
    bk = size * 8
    for i in range(len(bits) / bk):
        bits[i * bk : i * bk + bk] = bs_swap_bytes(bits[i * bk : i * bk + bk], size)

def single_to_bits(s):
    bits = []
    for c in s:
        ci = ord(c)
        if ci > 0xFF:
            die('encodings!')
        bits += map(int, '{0:08b}'.format(ci))
        # for i in reversed(range(8)):
        #     bits.append(1 if ci & (1 << i) else 0)
    swap(bits, 8)
    return bits

# к тестам надо добавить паддинг, так как его нет в реализации
# алгоритма

# def swap_bytes(a):
#     # return a
#     bits = []
#     for i in reversed(range(32 / 8)):
#         bits += a[i * 8 : i * 8 + 8]
#     return bits

# Merkle-Damgrad block padding for sha256
def pad_md(s):
    l = len(s)
    pl = (64 - l - 1 - 2*4) * 8
    l <<= 3
    bits = single_to_bits(s)
    bits += [1] + [0] * 7
    bits += [0] * pl
    rbits = []
    while l > 0:
        rbits.append(l & 1)
        l >>= 1
    bits += [0] * (64 - len(rbits))
    bits += reversed(rbits)
    # # swap first 14 integers from big endian
    # for i in range(14):
    #     bits[i * 32 : i * 32 + 32] = bs_swap_bytes(bits[i * 32 : i * 32 + 32], 4)
    return bits

def multiple_to_bits(a, single_fun):
    bits = []
    for b in zip(*map(single_fun, a)):
        t = 0
        for i in range(len(b)):
            t |= b[i] << i
        bits.append(t)
    return bits

def print_first(bits):
    bits = deepcopy(bits)
    r = []
    while len(bits):
        c = 0
        for i in reversed(range(8)):
            b = bits.pop(0)
            c |= (b & 1) << i
        r.append(c)
    print >> sys.stderr, ''.join('{0:02x}'.format(c) for c in r)

def run(code, inputs):
    values = {}
    outputs = []
    current_print = None
    # %% most probably 'tests' should be avoided here
    bs_one = 2 ** len(tests) - 1
    for l in code:
        if l[0] != 'bs_print_var' and current_print != None:
            print_first(current_print)
            current_print = None
        if l[0] == 'bs_new_const':
            assert l[2] == '0' or l[2] == '1'
            values[l[1]] = 0 if l[2] == '0' else bs_one
        elif l[0] == 'bs_input':
            values[l[1]] = inputs.pop(0)
        elif l[0] == 'label':
            pass
        elif l[0] == 'bs_xor':
            values[l[1]] = values[l[2]] ^ values[l[3]]
        elif l[0] == 'bs_and':
            values[l[1]] = values[l[2]] & values[l[3]]
        elif l[0] == 'bs_invert':
            values[l[1]] = values[l[2]] ^ bs_one
        elif l[0] == 'bs_output':
            outputs.append(values[l[1]])
        elif l[0] == 'bs_print_var':
            if l[2] == '0':
                if current_print != None:
                    print_first(current_print)
                current_print = []
            current_print.append(values[l[1]])
        elif l[0] == 'may_split_here':
            # noop
            pass
        elif l[0] == 'print_verbatim':
            print >> sys.stderr, l[1].decode('hex')
        else:
            die('unknown op {0}', l)
    return outputs

def print_n(bits, n):
    print_first([i >> n for i in bits])

def print_count(code):
    h = {}
    for l in code:
        if l[0] not in h:
            h[l[0]] = 0
        h[l[0]] += 1
    ks = h.keys()
    ks.sort(lambda a, b: cmp(h[a], h[b]))
    total = 0
    for k in ks:
        print >> sys.stderr, '{1:10d} {0}'.format(k, h[k])
        total += h[k]
    for k in 'label bs_new_const bs_output bs_input bs_input_length'.split(' '):
        if k in h:
            total -= h[k]
    print >> sys.stderr, 'total gates:', total

print_count(code)

# print_first(pad_md(tests[0][1]))

outputs = multiple_to_bits([t[0].decode('hex') for t in tests], single_to_bits)
# inputs = multiple_to_bits([t[1] for t in tests], pad_md)
inputs = multiple_to_bits([t[1] for t in tests], single_to_bits)

# print_first(inputs)
# print_n(inputs, 1)

r = run(code, inputs)

# swap(r, 8)

# print_first(r)
# print_n(r, 1)

# print >> sys.stderr, "need"
# print >> sys.stderr, tests[0][0]
# print >> sys.stderr, tests[1][0]

for a, b, i in zip(r, outputs, xrange(100000)):
    if a != b:
        die('failure: {0} {1}  {2}', a, b, i)

print >> sys.stderr, 'OK'
