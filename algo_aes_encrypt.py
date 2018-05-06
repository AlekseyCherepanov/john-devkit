# AES encryption, abstract

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('be', 4)

msg = input_salt()
key = input_key()

assume_length(msg, 16, 16)
assume_length(key, 16, 16)

include('aes')

r = AES(key).encrypt(msg)

# We've got 16 ints with 1 bytes. Let's pack them.

# print_many(*r)

o = []
for i in range(0, 16, 4):
    o.append((r[i + 0] << 24) ^ (r[i + 1] << 16) ^ (r[i + 2] << 8) ^ r[i + 3])

s = bytes_join_nums(*o)
output_bytes(s)
