# -*- coding: utf-8 -*-
# skein with output to john's format

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
algo_file = 'skein512'

c_code = U.load_code_template(c_template)

size = 8
endianity = 'be'

args['args'] = { 'size': size, 'use_unroll': 1, 'two_blocks': 0 }

# O.apply_size(size)
# O.apply_endianity(endianity)

# bs_size = 64
# O.apply_bs_size(bs_size)

# Format setup

tests = r'''
//{"d578679d76b51f6a79904a3a9b58bc4fc3f6d1b6812411fcf5840570353c7fe5dbfa7b539a707abe464dfcbb691ad97b6d0da7b419e16780f68a2ed8ef250c2e", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
{"8f5dd9ec798152668e35129496b029a960c9a9b88662f7f9482f110b31f9f93893ecfb25c009baad9e46737197d5630379816a886aa05526d3a70df272d96e75", "abc"},
{"bc5b4c50925519c290cc634277ae3d6257212395cba733bbad37a4af0fa06af41fca7903d06564fea7a2d3730dbdb80c1f85562dfcc070334ea4d1d9e72cba7a", ""},
{"94c2ae036dba8783d0b3f7d6cc111ff810702f5c77707999be7e1c9486ff238a7044de734293147359b4ac7e1d09cd247c351d69826b78dcddd951f0ef912713", "The quick brown fox jumps over the lazy dog"},
{"658223cb3d69b5e76e3588ca63feffba0dc2ead38a95d0650564f2a39da8e83fbb42c9d6ad9e03fbfde8a25a880357d457dbd6f74cbcb5e728979577dbce5436", "The quick brown fox jumps over the lazy dog."},
'''

vs = {
    'fmt_struct_name': 'raw1_skein512',
    'format_name': 'Raw-skein512',
    'algo_name': 'SKEIN512',
    'tag': '$skein512$',
    # %% bump length
    # 'plaintext_length': '47',
    'plaintext_length': '80' if args['args']['two_blocks'] else '47',
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

B.global_vars['skein'] = 1

# # Print bitslice and exit.
# d = B.thread_code( B.get_code_full(algo_file, **args),
#     B.replace_state_with_const,
#     [ B.unpack_const_subscripts, 'k' ],
#     B.remove_assignments,
#     [ B.compute_const_expressions, size ],
#     B.drop_arrays,
#     B.drop_print,
#     [ B.compute_const_expressions, size ],
#     # [ B.dump, 'before.bytecode' ],
#     [ B.bitslice, size ],
#     B.drop_unused,
#     [ B.dump, 'skein512bs.bytecode' ]
# )
# exit(1)

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
    [ B.compute_const_expressions, size ],

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

B.global_vars['vectorize'] = 1

B.thread_code( code,
    # B.reuse_variables,
    B.vectorize_maybe,
    B.use_define_for_some,
    [ B.interleave, interleave ],
    [ B.dump, 'code.bytecode' ],
    [ O.gen, c_code, args, B.global_vars ]
)
