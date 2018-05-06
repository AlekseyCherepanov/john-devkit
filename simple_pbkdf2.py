# -*- coding: utf-8 -*-
# simple pbkdf2-hmac-sha512

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import hashlib
import hmac

# hhh = "$pbkdf2-hmac-sha512$10000.82dbab96e072834d1f725db9aded51e703f1d449e77d01f6be65147a765c997d8865a1f1ab50856aa3b08d25a5602fe538ad0757b8ca2933fe8ca9e7601b3fbf.859d65960e6d05c6858f3d63fa35c6adfc456637b4a0a90f6afa7d8e217ce2d3dfdc56c8deaca217f0864ae1efb4a09b00eb84cf9e4a2723534f34e26a279193"
# password = "openwall"

hhh = "$pbkdf2-hmac-sha512$1000.6b635263736c70346869307a304b5276.80cf814855f2299103a6084366e41d7e14f9894b05ed77fa19881d28f06cde18da9ab44972cd00496843371ce922c70e64f3862b036b59b581fe32fc4408fe49"
password = "magnum"

digest_size = 64

h = hhh.split('$')[-1]
rounds, salt, h = h.split('.')
rounds = int(rounds)
dk_len = len(h) / 2

print rounds
print salt
print h
print

salt = salt.decode('hex')


import pbkdf2
# print pbkdf2.crypt(password, salt)

r = pbkdf2.PBKDF2(password, salt, iterations = rounds, digestmodule = hashlib.sha512, macmodule = hmac)
print r.hexread(digest_size)
print

def bytes_xor(a, b):
    return ''.join(chr(ord(x) ^ ord(y)) for x, y in zip(a, b))

def prf(p, s):
    return hmac.HMAC(p, s, hashlib.sha512).digest()

def f(p, s, c, i):
    # ксорим с 1 до 'c'
    u1 = prf(p, s + '{0:08x}'.format(i).decode('hex'))
    print u1.encode('hex')
    uj = u1
    r = u1
    for j in range(2, c + 1):
        uj = prf(p, uj)
        r = bytes_xor(r, uj)
    return r

# o = ''
# for j in range(1, dk_len / digest_size + 1):
#     o += f(password, salt, rounds, j)

print 'begin debug'
o = f(password, salt, rounds, 1)
r = o.encode('hex')
print 'end debug'

print
print r
assert r == h
