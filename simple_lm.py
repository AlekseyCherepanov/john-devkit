# -*- coding: utf-8 -*-
# Simple LM implementation
# Straight-forward port from C to Python, see simple_lm.c for origin
# The code may be broken, it was not tested well.
#
# Copyright (C) 2003, 2004 by Christopher R. Hertel
# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# * License:
# *
# *  This library is free software; you can redistribute it and/or
# *  modify it under the terms of the GNU Lesser General Public
# *  License as published by the Free Software Foundation; either
# *  version 2.1 of the License, or (at your option) any later version.
# *
# *  This library is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# *  Lesser General Public License for more details.
# *
# *  You should have received a copy of the GNU Lesser General Public
# *  License along with this library; if not, write to the Free Software
# *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

def dprint(a):
    r = 0
    for v in a:
        r <<= 8
        r += v
    print >> sys.stderr, "{0:016x}".format(r)

import sys

# DES
# http://www.ubiqx.org/proj/libcifs/source/Auth/DES.c

InitialPermuteMap = [
  57, 49, 41, 33, 25, 17,  9, 1,
  59, 51, 43, 35, 27, 19, 11, 3,
  61, 53, 45, 37, 29, 21, 13, 5,
  63, 55, 47, 39, 31, 23, 15, 7,
  56, 48, 40, 32, 24, 16,  8, 0,
  58, 50, 42, 34, 26, 18, 10, 2,
  60, 52, 44, 36, 28, 20, 12, 4,
  62, 54, 46, 38, 30, 22, 14, 6
]

KeyPermuteMap = [
  49, 42, 35, 28, 21, 14,  7,  0,
  50, 43, 36, 29, 22, 15,  8,  1,
  51, 44, 37, 30, 23, 16,  9,  2,
  52, 45, 38, 31, 55, 48, 41, 34,
  27, 20, 13,  6, 54, 47, 40, 33,
  26, 19, 12,  5, 53, 46, 39, 32,
  25, 18, 11,  4, 24, 17, 10,  3,
]

KeyRotation = [ 1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1 ]

KeyCompression = [
  13, 16, 10, 23,  0,  4,  2, 27,
  14,  5, 20,  9, 22, 18, 11,  3,
  25,  7, 15,  6, 26, 19, 12,  1,
  40, 51, 30, 36, 46, 54, 29, 39,
  50, 44, 32, 47, 43, 48, 38, 55,
  33, 52, 45, 41, 49, 35, 28, 31
]

DataExpansion = [
  31,  0,  1,  2,  3,  4,  3,  4,
   5,  6,  7,  8,  7,  8,  9, 10,
  11, 12, 11, 12, 13, 14, 15, 16,
  15, 16, 17, 18, 19, 20, 19, 20,
  21, 22, 23, 24, 23, 24, 25, 26,
  27, 28, 27, 28, 29, 30, 31,  0
]

SBox = [
    [  # S0
    14,  0,  4, 15, 13,  7,  1,  4,  2, 14, 15,  2, 11, 13,  8,  1,
     3, 10, 10,  6,  6, 12, 12, 11,  5,  9,  9,  5,  0,  3,  7,  8,
     4, 15,  1, 12, 14,  8,  8,  2, 13,  4,  6,  9,  2,  1, 11,  7,
    15,  5, 12, 11,  9,  3,  7, 14,  3, 10, 10,  0,  5,  6,  0, 13
    ],
    [  # S1
    15,  3,  1, 13,  8,  4, 14,  7,  6, 15, 11,  2,  3,  8,  4, 14,
     9, 12,  7,  0,  2,  1, 13, 10, 12,  6,  0,  9,  5, 11, 10,  5,
     0, 13, 14,  8,  7, 10, 11,  1, 10,  3,  4, 15, 13,  4,  1,  2,
     5, 11,  8,  6, 12,  7,  6, 12,  9,  0,  3,  5,  2, 14, 15,  9
    ],
    [  # S2
    10, 13,  0,  7,  9,  0, 14,  9,  6,  3,  3,  4, 15,  6,  5, 10,
     1,  2, 13,  8, 12,  5,  7, 14, 11, 12,  4, 11,  2, 15,  8,  1,
    13,  1,  6, 10,  4, 13,  9,  0,  8,  6, 15,  9,  3,  8,  0,  7,
    11,  4,  1, 15,  2, 14, 12,  3,  5, 11, 10,  5, 14,  2,  7, 12
    ],
    [  # S3
     7, 13, 13,  8, 14, 11,  3,  5,  0,  6,  6, 15,  9,  0, 10,  3,
     1,  4,  2,  7,  8,  2,  5, 12, 11,  1, 12, 10,  4, 14, 15,  9,
    10,  3,  6, 15,  9,  0,  0,  6, 12, 10, 11,  1,  7, 13, 13,  8,
    15,  9,  1,  4,  3,  5, 14, 11,  5, 12,  2,  7,  8,  2,  4, 14
    ],
    [  # S4
     2, 14, 12, 11,  4,  2,  1, 12,  7,  4, 10,  7, 11, 13,  6,  1,
     8,  5,  5,  0,  3, 15, 15, 10, 13,  3,  0,  9, 14,  8,  9,  6,
     4, 11,  2,  8,  1, 12, 11,  7, 10,  1, 13, 14,  7,  2,  8, 13,
    15,  6,  9, 15, 12,  0,  5,  9,  6, 10,  3,  4,  0,  5, 14,  3
    ],
    [  # S5
    12, 10,  1, 15, 10,  4, 15,  2,  9,  7,  2, 12,  6,  9,  8,  5,
     0,  6, 13,  1,  3, 13,  4, 14, 14,  0,  7, 11,  5,  3, 11,  8,
     9,  4, 14,  3, 15,  2,  5, 12,  2,  9,  8,  5, 12, 15,  3, 10,
     7, 11,  0, 14,  4,  1, 10,  7,  1,  6, 13,  0, 11,  8,  6, 13
    ],
    [  # S6
     4, 13, 11,  0,  2, 11, 14,  7, 15,  4,  0,  9,  8,  1, 13, 10,
     3, 14, 12,  3,  9,  5,  7, 12,  5,  2, 10, 15,  6,  8,  1,  6,
     1,  6,  4, 11, 11, 13, 13,  8, 12,  1,  3,  4,  7, 10, 14,  7,
    10,  9, 15,  5,  6,  0,  8, 15,  0, 14,  5,  2,  9,  3,  2, 12
    ],
    [  # S7
    13,  1,  2, 15,  8, 13,  4,  8,  6, 10, 15,  3, 11,  7,  1,  4,
    10, 12,  9,  5,  3,  6, 14, 11,  5,  0,  0, 14, 12,  9,  7,  2,
     7,  2, 11,  1,  4, 14,  1,  7,  9,  4, 12, 10, 14,  8,  2, 13,
     0, 15,  6, 12, 10,  9, 13,  0, 15,  3,  3,  5,  5,  6,  8, 11
    ]
]

PBox = [
  15,  6, 19, 20, 28, 11, 27, 16,
   0, 14, 22, 25,  4, 17, 30,  9,
   1,  7, 23, 13, 31, 26,  2,  8,
  18, 12, 29,  5, 21, 10,  3, 24
]

FinalPermuteMap = [
   7, 39, 15, 47, 23, 55, 31, 63,
   6, 38, 14, 46, 22, 54, 30, 62,
   5, 37, 13, 45, 21, 53, 29, 61,
   4, 36, 12, 44, 20, 52, 28, 60,
   3, 35, 11, 43, 19, 51, 27, 59,
   2, 34, 10, 42, 18, 50, 26, 58,
   1, 33,  9, 41, 17, 49, 25, 57,
   0, 32,  8, 40, 16, 48, 24, 56
]

def clear_bit(string, idx):
    string[idx / 8] &= ~(0x01 << (7 - (idx % 8)))

def set_bit(string, idx):
    string[idx / 8] |= 0x01 << (7 - (idx % 8))

def get_bit(string, idx):
    return (string[idx / 8] >> (7 - (idx % 8))) & 0x01

def Permute(src, map, mapsize):
    dst = [0 for i in range(mapsize)]
    bitcount = mapsize * 8
    # print >> sys.stderr, bitcount
    for i in range(bitcount):
        # print >> sys.stderr, i, map, src
        if get_bit(src, map[i]):
            set_bit(dst, i)
    return dst

def KeyShift(key, numbits):
    keep = key[0]
    for i in range(numbits):
        for j in range(7):
            if j and (key[j] & 0x80):
                key[j - 1] |= 0x01
            key[j] <<= 1
            key[j] %= 256
        if get_bit(key, 27):
            clear_bit(key, 27)
            set_bit(key, 55)
        if keep & 0x80:
            set_bit(key, 27)
        keep <<= 1
        keep %= 256

def sbox(src):
    dst = [0, 0, 0, 0]
    for i in range(8):
        Snum = 0
        bitnum = i * 6
        for j in range(6):
            Snum <<= 1
            Snum %= 256
            Snum |= get_bit(src, bitnum)
            bitnum += 1
        if 0 == i % 2:
            dst[i / 2] |= ((SBox[i][Snum]) << 4)
        else:
            dst[i / 2] |= SBox[i][Snum]
    return dst

def xor(a, b, count):
    return [a[i] ^ b[i] for i in range(count)]

def des_hash(key, src):
    K = Permute(key, KeyPermuteMap, 7)
    D = Permute(src, InitialPermuteMap, 8)
    L = D[0:4]
    R = D[4:8]
    for i in range(16):
        # Key schedule
        KeyShift(K, KeyRotation[i])
        SubK = Permute(K, KeyCompression, 6)
        # Feistel function
        Rexp = Permute(R, DataExpansion, 6)
        Rexp = xor(Rexp, SubK, 6)
        Rn = sbox(Rexp)
        Rexp = Permute(Rn, PBox, 4)
        # End of Feistel function
        Rn = xor(L, Rexp, 4)
        for j in range(4):
            L[j] = R[j]
            R[j] = Rn[j]
    dprint(L + R)
    dst = Permute(L + R, FinalPermuteMap, 8)
    dprint(dst)
    return dst

# LM
# http://www.ubiqx.org/proj/libcifs/source/Auth/LMhash.c

def to_bytes(string):
    return [ord(c) for c in string]

lm_magic = "KGS!@#$%"

lm_magic = to_bytes(lm_magic)

def lm_hash(pwd):
    pwd = to_bytes(pwd)
    pwd += [0 for i in range(14)]
    p1 = pwd[0:7]
    p2 = pwd[7:14]
    h1 = des_hash(p1, lm_magic)
    h2 = des_hash(p2, lm_magic)
    return h1, h2

# Test code

def to_hex(h):
    return "".join(map("{0:02x}".format, h))

# h1, h2 = lm_hash("POLITIS")
h1, h2 = lm_hash("AAAAAA")
print >> sys.stderr, to_hex(h1), to_hex(h2)
# for i in range(1000):
#     lm_hash("POLITIS")
