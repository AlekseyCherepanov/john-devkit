# -*- coding: utf-8 -*-
# md4 with output to john's format

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import util_ui as U
import bytecode_main as B
import output_c as O
# import output_c_sse as O

args = U.parse_args()

c_template = 'raw'
algo_file = 'md4'

c_code = U.load_code_template(c_template)

size = 4
endianity = 'le'

args['args'] = { 'size': size }

O.apply_size(size)
O.apply_endianity(endianity)

bs_size = 64
O.apply_bs_size(bs_size)

# Format setup

tests = '''
{"8a9d093f14f8701df17732b2bb182c74", "password"},
{FORMAT_TAG "6d78785c44ea8dfa178748b245d8c3ae", "magnum" },
{"6d78785c44ea8dfa178748b245d8c3ae", "magnum" },
{FORMAT_TAG "31d6cfe0d16ae931b73c59d7e0c089c0", "" },
{FORMAT_TAG "934eb897904769085af8101ad9dabca2", "John the ripper" },
{FORMAT_TAG "cafbb81fb64d9dd286bc851c4c6e0d21", "lolcode" },
{FORMAT_TAG "585028aa0f794af812ee3be8804eb14a", "123456" },
{FORMAT_TAG "23580e2a459f7ea40f9efa148b63cafb", "12345" },
{FORMAT_TAG "2ae523785d0caf4d2fb557c12016185c", "123456789" },
{FORMAT_TAG "f3e80e83b29b778bc092bf8a7c6907fe", "iloveyou" },
{FORMAT_TAG "4d10a268a303379f224d8852f2d13f11", "princess" },
{FORMAT_TAG "bf75555ca19051f694224f2f5e0b219d", "1234567" },
{FORMAT_TAG "41f92cf74e3d2c3ba79183629a929915", "rockyou" },
{FORMAT_TAG "012d73e0fab8d26e0f4d65e36077511e", "12345678" },
{FORMAT_TAG "0ceb1fd260c35bd50005341532748de6", "abc123" },
'''

vs = {
    'fmt_struct_name': 'raw1_md4',
    'format_name': 'Raw-MD4',
    'algo_name': 'MD4',
    'tag': '$MD4$',
    'plaintext_length': '55',
    'binary_form_size': '16',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

interleave = 4

B.global_vars['batch_size'] = 10

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

    # [ B.unroll_cycle_const_range, 'main' ],
    # [ B.unpack_const_subscripts, 'k' ],
    # B.remove_assignments,
    # B.compute_const_expressions,

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
    B.use_define_for_some,
    [ B.interleave, interleave ],
    [ B.dump, 'code.bytecode' ],
    [ O.gen, c_code, args, B.global_vars ]
)

# print c_code
