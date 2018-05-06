# -*- coding: utf-8 -*-
# JH with output to john's format

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import util_ui as U
import bytecode_main as B
import output_c as O
# import output_c_sse as O

args = U.parse_args()

c_template = 'raw2'
algo_file = 'jh512'

c_code = U.load_code_template(c_template)

size = 8
endianity = 'le'

args['args'] = { 'size': size, 'use_unroll': 0 }

O.apply_size(size)
O.apply_endianity(endianity)

bs_size = 64
O.apply_bs_size(bs_size)

# Format setup

# %% zero length, empty password is not handled properly
tests = r'''
{"c6bebe231a6cd5f49a7b5557567946fbf9c1221f92112cc429e0f223fb54323ddea7b6d326b5e84beb72c4f813036a0036da5ce8df6b135204a4efb4a49b0e03", "\xEA\xEE\xD5\xCD\xFF\xD8\x9D\xEC\xE4\x55\xF1"},
{"277c93806945992a7f10102f28471af2783fe32003b3f63320810e74f1bc233bf8669ab4b922db9ef13fcdcd4d31193b731eedde98fc87c129c04a4a1071f66f", "\xCC"},
//{"90ecf2f76f9d2c8017d979ad5ab96b87d58fc8fc4b83060f3f900774faa2c8fabe69c5f4ff1ec2b61d6b316941cedee117fb04b1f4c5bc1b919ae841c50eec4f", ""},
'''

vs = {
    'fmt_struct_name': 'raw1_jh512',
    'format_name': 'Raw-jh512',
    'algo_name': 'JH512',
    'tag': '$jh512$',
    # %% bump length
    'plaintext_length': '47',
    'binary_form_size': '64',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

interleave = 1

# B.global_vars['batch_size'] = 20
# B.global_vars['batch_size'] = 16
B.global_vars['batch_size'] = 1

reverse_num = 0

B.global_vars['interleave'] = interleave
B.global_vars['reverse_num'] =  reverse_num

B.global_vars['vectorize'] = 1

d = B.thread_code( B.get_code_full(algo_file, **args),
    B.replace_state_with_const,
    [ B.dump, 'pure.bytecode' ],
    # [ B.bitslice, 64, size ],
    # [ B.unroll_cycle_const_range, 'setupW' ],
    # [ B.unroll_cycle_const_range_partly, 'setupW', 16 ],
    # [ B.unroll_cycle_const_range_partly, 'main', 40 ],

    # [ B.unroll_cycle_const_range_partly, 'main', 2 ],

    # [ B.unroll_cycle_const_range, 'main' ],

    # B.remove_assignments,
    # [ B.compute_const_expressions, size ],

    # B.drop_print,

    # [ B.reduce_assignments, 'main', 'main_end' ],
    [ B.dump, 'all.bytecode' ],
    # B.research_reverse,
    # [ B.reverse_ops, reverse_num ],
    [ B.no_reverse, reverse_num ],
)

reverse = d['reverse']
code = d['code']
scalar = B.deep_copy(code)

reverse_str = B.thread_code( reverse,
    [ B.dump, 'reverse.bytecode' ],
    [ O.gen_to_str, '$code', args ]
)
B.global_vars['reverse'] = reverse_str

scalar_str = B.thread_code( scalar,
    [ B.dump, 'scalar.bytecode' ],
    [ O.gen_to_str, '$code', args ]
)
B.global_vars['scalar'] = scalar_str

B.thread_code( code,
    # B.reuse_variables,

    B.vectorize,

    # B.use_define_for_some,
    [ B.interleave, interleave ],
    [ B.dump, 'code.bytecode' ],
    [ O.gen, c_code, args, B.global_vars ]
)
