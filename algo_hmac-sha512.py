# hmac-sha512 abstract

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('be', 4)

s = input_salt()
key = input_key()

# print_bytes(s)
# print_bytes(key)

sha512 = load_hfun('sha512')

r = hmac(sha512, key, s)

output_bytes(r)
