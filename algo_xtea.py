# XTEA abstract
# https://en.wikipedia.org/wiki/XTEA

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('le', 4)

def encipher(num_rounds, v, key):
    v0, v1 = v
    s = 0
    delta = 0x9E3779B9
    for i in range(num_rounds):
        # v0 += (((v1 << 4) ^ (v1 >> 5)) + v1) ^ (s + key[s & 3])
        v0 += (((v1 << 4) ^ (v1 >> 5)) + v1) ^ (s + key[s & 3])
        s += delta
        v1 += (((v0 << 4) ^ (v0 >> 5)) + v0) ^ (key[(s >> 11) & 3] + s)
    return v0, v1

# We abuse state var as interface for key
key = [new_state_var(0) for i in range(4)]

v = [input() for i in range(2)]

# Number of rounds from "unholy" task in BKP CTF 2016
r = encipher(32, v, key)

for o in r:
    # print_var(o)
    output(o)
