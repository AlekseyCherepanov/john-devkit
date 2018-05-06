# -*- coding: utf-8 -*-
# simple hmac-sha512

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import hashlib

hhh = "what do ya want for nothing?#164b7a7bfcf819e2e395fbe73b56e0a387bd64222e831fd610270cd7ea2505549758bf75c05a994a6d034f65f8f0e6fdcaeab1a34d4a6b4b636e070a38bce737"

block_size = 128

# len of sha512 in hex is block_size / 2 * 2
hh = hhh[- block_size : ]
msg = hhh[ : - block_size - 1]
key = "Jefe"

print hh
print msg
print key


import hmac
h = hmac.HMAC(key, msg, hashlib.sha512).hexdigest()
print h


def do_hash(s):
    h = hashlib.new('sha512')
    h.update(s)
    return h.digest()

if len(key) > block_size:
    key = do_hash(key)
if len(key) < block_size:
    key += '\0' * (block_size - len(key))

# def xor(a, b):
#     return ''.join(chr(ord(x) ^ ord(y)) for x, y in zip(a, b))
# opad = ("5c" * block_size).decode('hex')
# ipad = ("36" * block_size).decode('hex')
# o_key_pad = xor(opad, key)
# i_key_pad = xor(ipad, key)

def xxor(n, s):
    return ''.join(chr(n ^ ord(x)) for x in s)
o_key_pad = xxor(0x5c, key)
i_key_pad = xxor(0x36, key)

print key
print o_key_pad
print i_key_pad

r = do_hash(o_key_pad + do_hash(i_key_pad + msg)).encode('hex')

print r
