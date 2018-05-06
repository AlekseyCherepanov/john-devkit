# -*- coding: utf-8 -*-
# bit-sliced aes sbox implementation for john-devkit

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import sys

import bytecode_main as B

# AES sbox
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


# Unused
# from common.pq from
# https://cryptojedi.org/crypto/data/aes-gcm-128-const-intel64-20090611.tar.bz2
sbox = r'''

@define sbox(b0, b1, b2, b3, b4, b5, b6, b7, t0, t1, t2, t3, s0, s1, s2, s3) \
	InBasisChange(b0, b1, b2, b3, b4, b5, b6, b7); \
	Inv_GF256(b6, b5, b0, b3, b7, b1, b4, b2, t0, t1, t2, t3, s0, s1, s2, s3); \
	OutBasisChange(b7, b1, b4, b2, b6, b5, b0, b3); \

@define InBasisChange(b0, b1, b2, b3, b4, b5, b6, b7) \
	b5 ^= b6;\
	b2 ^= b1;\
	b5 ^= b0;\
	b6 ^= b2;\
	b3 ^= b0;\
	;\
	b6 ^= b3;\
	b3 ^= b7;\
	b3 ^= b4;\
	b7 ^= b5;\
	b3 ^= b1;\
	;\
	b4 ^= b5;\
	b2 ^= b7;\
	b1 ^= b5;\
 
@define OutBasisChange(b0, b1, b2, b3, b4, b5, b6, b7) \
	b0 ^= b6;\
	b1 ^= b4;\
	b2 ^= b0;\
	b4 ^= b6;\
	b6 ^= b1;\
	;\
	b1 ^= b5;\
	b5 ^= b3;\
	b2 ^= b5;\
	b3 ^= b7;\
	b7 ^= b5;\
	;\
	b4 ^= b7;\
	
@define Mul_GF4(x0, x1, y0, y1, t0) \
	t0 = y0;\
	t0 ^= y1;\
	t0 &= x0;\
	x0 ^= x1;\
	x0 &= y1;\
	x1 &= y0;\
	x0 ^= x1;\
	x1 ^= t0;\
	
@define Mul_GF4_N(x0, x1, y0, y1, t0) \
	t0 = y0;\
	t0 ^= y1;\
	t0 &= x0;\
	x0 ^= x1;\
	x0 &= y1;\
	x1 &= y0;\
	x1 ^= x0;\
	x0 ^= t0;\
	
@define Mul_GF4_2(x0, x1, x2, x3, y0, y1, t0, t1) \
	t0 = y0;\
	t0 ^= y1;\
	t1 = t0;\
	t0 &= x0;\
	t1 &= x2;\
	x0 ^= x1;\
	x2 ^= x3;\
	x0 &= y1;\
	x2 &= y1;\
	x1 &= y0;\
	x3 &= y0;\
	x0 ^= x1;\
	x2 ^= x3;\
	x1 ^= t0;\
	x3 ^= t1;\
	
@define Mul_GF16(x0, x1, x2, x3, y0, y1, y2, y3, t0, t1, t2, t3) \
	t0 = x0;\
	t1 = x1;\
	Mul_GF4(x0, x1, y0, y1, t2);\
	t0 ^= x2;\
	t1 ^= x3;\
	y0 ^= y2;\
	y1 ^= y3;\
	Mul_GF4_N(t0, t1, y0, y1, t2);\
	Mul_GF4(x2, x3, y2, y3, t3);\
	;\
	x0 ^= t0;\
	x2 ^= t0;\
	x1 ^= t1;\
	x3 ^= t1;\
			
@define Mul_GF16_2(x0, x1, x2, x3, x4, x5, x6, x7, y0, y1, y2, y3, t0, t1, t2, t3) \
	t0 = x0;\
	t1 = x1;\
	Mul_GF4(x0, x1, y0, y1, t2);\
	t0 ^= x2;\
	t1 ^= x3;\
	y0 ^= y2;\
	y1 ^= y3;\
	Mul_GF4_N(t0, t1, y0, y1, t3);\
	Mul_GF4(x2, x3, y2, y3, t2);\
	;\
	x0 ^= t0;\
	x2 ^= t0;\
	x1 ^= t1;\
	x3 ^= t1;\
	;\
	t0 = x4;\
	t1 = x5;\
	t0 ^= x6;\
	t1 ^= x7;\
	Mul_GF4_N(t0, t1, y0, y1, t3);\
	Mul_GF4(x6, x7, y2, y3, t2);\
	y0 ^= y2;\
	y1 ^= y3;\
	Mul_GF4(x4, x5, y0, y1, t3);\
	;\
	x4 ^= t0;\
	x6 ^= t0;\
	x5 ^= t1;\
	x7 ^= t1;\
	
@define Inv_GF16(x0, x1, x2, x3, t0, t1, t2, t3) \
	t0 = x1;\
	t1 = x0;\
	t0 &= x3;\
	t1 |= x2;\
	t2 = x1;\
	t3 = x0;\
	t2 |= x2;\
	t3 |= x3;\
	t2 ^= t3;\
	;\
	t0 ^= t2;\
	t1 ^= t2;\
	;\
	Mul_GF4_2(x0, x1, x2, x3, t1, t0, t2, t3);\

	
@define Inv_GF256(x0,  x1, x2, x3, x4, x5, x6, x7, t0, t1, t2, t3, s0, s1, s2, s3) \
	t3 = x4;\
	t2 = x5;\
	t1 = x1;\
	s1 = x7;\
	s0 = x0;\
	;\
	t3 ^= x6;\
	t2 ^= x7;\
	t1 ^= x3;\
	s1 ^= x6;\
	s0 ^= x2;\
	;\
	s2 = t3;\
	t0 = t2;\
	s3 = t3;\
	;\
	t2 |= t1;\
	t3 |= s0;\
	s3 ^= t0;\
	s2 &= s0;\
	t0 &= t1;\
	s0 ^= t1;\
	s3 &= s0;\
	s0 = x3;\
	s0 ^= x2;\
	s1 &= s0;\
	t3 ^= s1;\
	t2 ^= s1;\
	s1 = x4;\
	s1 ^= x5;\
	s0 = x1;\
	t1 = s1;\
	s0 ^= x0;\
	t1 |= s0;\
	s1 &= s0;\
	t0 ^= s1;\
	t3 ^= s3;\
	t2 ^= s2;\
	t1 ^= s3;\
	t0 ^= s2;\
	t1 ^= s2;\
	s0 = x7;\
	s1 = x6;\
	s2 = x5;\
	s3 = x4;\
	s0 &= x3;\
	s1 &= x2;\
	s2 &= x1;\
	s3 |= x0;\
	t3 ^= s0;\
	t2 ^= s1;\
	t1 ^= s2;\
	t0 ^= s3;\
	;\
	s0 = t3;\
	s0 ^= t2;\
	t3 &= t1;\
	s2 = t0;\
	s2 ^= t3;\
	s3 = s0;\
	s3 &= s2;\
	s3 ^= t2;\
	s1 = t1;\
	s1 ^= t0;\
	t3 ^= t2;\
	s1 &= t3;\
	s1 ^= t0;\
	t1 ^= s1;\
	t2 = s2;\
	t2 ^= s1;\
	t2 &= t0;\
	t1 ^= t2;\
	s2 ^= t2;\
	s2 &= s3;\
	s2 ^= s0;\
	;\
	Mul_GF16_2(x0, x1, x2, x3, x4, x5, x6, x7, s3, s2, s1, t1, s0, t0, t2, t3);\


b0, b1, b2, b3, b4, b5, b6, b7 = [input() for i in range(8)]

sbox(b0, b1, b2, b3, b4, b5, b6, b7, t0, t1, t2, t3, s0, s1, s2, s3)

for v in b0, b1, b2, b3, b4, b5, b6, b7: output(v)
'''

import subprocess
sbox = sbox.replace('@', '#')
p = subprocess.Popen(['gcc', '-E', '-'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
p.stdin.write(sbox)
p.stdin.close()
sbox = p.stdout.read()
p.stdout.close()
sbox = sbox.replace(';', '\n')
import re
sbox = re.sub(r'^\s+', '', sbox, flags=re.M)

# print >> sys.stderr, sbox

# http://www.cs.yale.edu/homes/peralta/CircuitStuff/AES_SBox.txt
sbox2 = '''
x0, x1, x2, x3, x4, x5, x6, x7 = [input() for i in range(8)]
def xnor(a, b): return ~(a ^ b)

y14 = x3 + x5;
y13 = x0 + x6;
y9 = x0 + x3;
y8 = x0 + x5;
t0 = x1 + x2;
y1 = t0 + x7;
y4 = y1 + x3;
y12 = y13 + y14;
y2 = y1 + x0;
y5 = y1 + x6;
y3 = y5 + y8;
t1 = x4 + y12;
y15 = t1 + x5;
y20 = t1 + x1;
y6 = y15 + x7;
y10 = y15 + t0;
y11 = y20 + y9;
y7 = x7 + y11;
y17 = y10 + y11;
y19 = y10 + y8;
y16 = t0 + y11;
y21 = y13 + y16;
y18 = x0 + y16;

t2 = y12 X y15;
t3 = y3 X y6;
t4 = t3 + t2;
t5 = y4 X x7;
t6 = t5 + t2; 
t7 = y13 X y16;
t8 = y5 X y1;
t9 = t8 + t7;
t10 = y2 X y7;
t11 = t10 + t7;
t12 = y9 X y11;
t13 = y14 X y17;
t14 = t13 + t12;
t15 = y8 X y10;
t16 = t15 + t12;
t17 = t4 + t14;
t18 = t6 + t16;
t19 = t9 + t14;
t20 = t11 + t16;
t21 = t17 + y20;
t22 = t18 + y19;
t23 = t19 + y21;
t24 = t20 + y18;

t25 = t21 + t22;
t26 = t21 X t23;
t27 = t24 + t26;
t28 = t25 X t27; 
t29 = t28 + t22;
t30 = t23 + t24;
t31 = t22 + t26;
t32 = t31 X t30;
t33 = t32 + t24;
t34 = t23 + t33;
t35 = t27 + t33;
t36 = t24 X t35; 
t37 = t36 + t34;
t38 = t27 + t36;
t39 = t29 X t38;
t40 = t25 + t39;

t41 = t40 + t37;
t42 = t29 + t33;
t43 =  t29 + t40;
t44 =  t33 + t37;
t45 = t42 + t41;
z0 = t44 X y15;
z1 = t37 X y6;
z2 = t33 X x7;
z3 = t43 X y16;
z4 = t40 X y1;
z5 = t29 X y7;
z6 = t42 X y11;
z7 = t45 X y17;
z8 = t41 X y10;
z9 = t44 X y12;
z10 = t37 X y3;
z11 = t33 X y4;
z12 = t43 X y13;
z13 = t40 X y5;
z14 = t29 X y2;
z15 = t42 X y9;
z16 = t45 X y14;
z17 = t41 X y8;

t46 = z15 + z16;
t47 = z10 + z11;
t48 = z5 + z13;
t49 = z9 + z10;
t50 = z2 + z12;
t51 = z2 + z5;
t52 = z7 + z8;
t53 = z0 + z3;
t54 = z6 + z7;
t55 = z16 + z17;
t56 = z12 + t48;
t57 = t50 + t53;
t58 = z4 + t46;
t59 = z3 + t54;
t60 = t46 + t57;
t61 = z14 + t57;
t62 = t52 + t58;
t63 = t49 + t58;
t64 = z4 + t59;
t65 = t61 + t62;
t66 = z1 + t63;
s0 = t59 + t63;
s6 = xnor(t56, t62);
s7 = xnor(t48, t60);
t67 = t64 + t65;
s3 = t53 + t66;
s4 = t51 + t66;
s5 = t47 + t65;
s1 = xnor(t64, s3);
s2 = xnor(t55, t67);

for v in s0, s1, s2, s3, s4, s5, s6, s7: output(v)

'''

sbox2 = sbox2.replace('+', '^')
sbox2 = sbox2.replace('*', '&')
sbox2 = sbox2.replace('X', '&')

sbox = sbox2

code = B.evaluate(sbox)

# code = B.slurp_bytecode("sboxes/7_13_13_8_14_11_3_5_0_6_6_15_9_0_10_3_1_4_2_7_8_2_5_12_11_1_12_10_4_14_15_9_10_3_6_15_9_0_0_6_12_10_11_1_7_13_13_8_15_9_1_4_3_5_14_11_5_12_2_7_8_2_4_14.6_4.33.s4.0")

counts = B.count_instructions(code)
n_inputs = counts['input']
n_outputs = counts['output']

r = []
for i in range(2 ** n_inputs):
    input_bits = [(i >> j) & 1 for j in range(n_inputs)]
    input_bits.reverse()
    output_bits = B.interpret([['var_setup', '4', 'le']] + code, input_bits, 'run')
    rr = 0
    # for b in reversed(output_bits):
    for b in output_bits:
        rr <<= 1
        rr |= (b & 1)
    r.append(rr)
# r = map(lambda a: a ^ (0x63 << 1), r)
# r = map(lambda a: a ^ 0x63, r)
# print >> sys.stderr, r
# print >> sys.stderr, map('{0:02x}'.format, r)

if r != S:
    die('wrong implementation')

table_hash = B.sbox_table_hash_hex(S)
fname = '{0}.{1}_{2}.{3}.aes'.format(table_hash, n_inputs, n_outputs, len(code) - n_inputs - n_outputs)

print >> sys.stderr, len(code)
B.dump(code, 'aes.bytecode')
B.dump(code, 'sboxes/' + fname)
