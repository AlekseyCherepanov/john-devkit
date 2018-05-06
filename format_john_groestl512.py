# -*- coding: utf-8 -*-
# groestl with output to john's format

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import util_ui as U
import bytecode_main as B
import output_c as O
# import output_c_sse as O

# args = U.parse_args()

c_template = 'raw'
algo_file = 'groestl512'

c_code = U.load_code_template(c_template)

size = 8
endianity = 'le'

args = {}
args['args'] = { 'size': size }

bs_size = 64
O.apply_bs_size(bs_size)

# Format setup

tests = r'''
{"6d3ad29d279110eef3adbd66de2a0345a77baede1557f5d099fce0c03d6dc2ba8e6d4a6633dfbd66053c20faa87d1a11f39a7fbe4a6c2f009801370308fc4ad8", ""},
{"70e1c68c60df3b655339d67dc291cc3f1dde4ef343f11b23fdd44957693815a75a8339c682fc28322513fd1f283c18e53cff2b264e06bf83a2f0ac8c1f6fbff6", "abc"},
'''

vs = {
    'fmt_struct_name': 'raw1_groestl512',
    'format_name': 'Raw-groestl512',
    'algo_name': 'GROESTL512',
    'tag': '$groestl512$',
    'plaintext_length': '111',
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

B.global_vars['vectorize'] = 0
# B.global_vars['groestl'] = 1

d = B.thread_code( B.get_code_full(algo_file, **args),

    # [ B.interpret, [0x80 << 56] + [0] * 14 + [1] ],
    # B.my_exit,

    # [ B.interpret, [0x61626380 << 32] + [0] * 14 + [1] ],
    # B.my_exit,

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

    # B.vectorize,

    # B.use_define_for_some,
    [ B.interleave, interleave ],
    [ B.dump, 'code.bytecode' ],
    [ O.gen, c_code, args, B.global_vars ]
)
