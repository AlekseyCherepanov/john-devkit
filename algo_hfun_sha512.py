# sha512 abstract
# without limits on length

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

compression_function = load_plain('sha512')

key = input_key()

Var.setup(8, 'be')
# %% get interface from functions
set_hfun_block_size(str(16 * 8))
set_hfun_digest_size(str(8 * 8))

r = run_merkle_damgard(compression_function, key)

# print_hex(key)
# print_hex(r)
# debug_exit('hi')

output_bytes(r)
