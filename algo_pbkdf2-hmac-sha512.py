# pbkdf2-hmac-sha512 abstract

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('be', 4)

s = input_salt()
key = input_key()
rounds = input_rounds()

# print_var(rounds)
# print_bytes(key)
# print_bytes(s)

sha512 = load_hfun('sha512')

# dk_len = hfun_digest_size(sha512)
# r = pbkdf2_hmac(sha512, key, s, rounds, dk_len)
r = pbkdf2_hmac(sha512, key, s, rounds, 1)

output_bytes(r)
