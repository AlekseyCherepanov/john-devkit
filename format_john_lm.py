# -*- coding: utf-8 -*-
# LM with output to john's format

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import util_ui as U
import bytecode_main as B
import output_c as O
# import output_c_sse as O

args = U.parse_args()

c_template = 'lm'
algo_file = 'lm'

c_code = U.load_code_template(c_template)

size = 8
endianity = 'be'

args['args'] = { 'size': size }

O.apply_size(size)
O.apply_endianity(endianity)

bs_size = 64
O.apply_bs_size(bs_size)

# Format setup

tests = '''
'''

vs = {
    'fmt_struct_name': 'raw1_LM',
    'format_name': 'LM',
    'algo_name': 'LM',
    'tag': '$LM$',
    'plaintext_length': '7',
    'binary_form_size': '8',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

code = B.get_code_full(algo_file, **args)

interleave = 1

B.global_vars['batch_size'] = 1

B.global_vars['interleave'] = interleave

# B.global_vars['vectorize'] = 1

d = B.thread_code( code,
    B.replace_state_with_const,
    [ B.dump, 'pure.bytecode' ],
    [ O.gen, c_code, args, B.global_vars ]
)
