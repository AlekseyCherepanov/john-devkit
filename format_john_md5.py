# -*- coding: utf-8 -*-
# md5 with output to john's format

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
algo_file = 'md5'

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
{"5a105e8b9d40e1329780d62ea2265d8a", "test1"},
{FORMAT_TAG "5a105e8b9d40e1329780d62ea2265d8a", "test1"},
{"098f6bcd4621d373cade4e832627b4f6", "test"},
{FORMAT_TAG "378e2c4a07968da2eca692320136433d", "thatsworking"},
{FORMAT_TAG "8ad8757baa8564dc136c1e07507f4a98", "test3"},
{"d41d8cd98f00b204e9800998ecf8427e", ""},
#ifdef DEBUG
{FORMAT_TAG "c9ccf168914a1bcfc3229f1948e67da0","1234567890123456789012345678901234567890123456789012345"},
#if PLAINTEXT_LENGTH >= 80
{FORMAT_TAG "57edf4a22be3c955ac49da2e2107b67a","12345678901234567890123456789012345678901234567890123456789012345678901234567890"},
#endif
#endif
'''

vs = {
    'fmt_struct_name': 'raw1_md5',
    'format_name': 'Raw-MD5',
    'algo_name': 'MD5',
    'tag': '$dynamic_0$',
    'plaintext_length': '55',
    'binary_form_size': '16',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

code = B.get_code_full(algo_file, **args)

interleave = 4

B.global_vars['batch_size'] = 40

reverse_num = 0

B.global_vars['interleave'] = interleave
B.global_vars['reverse_num'] =  reverse_num

B.global_vars['vectorize'] = 1

d = B.thread_code( code,
    B.replace_state_with_const,
    [ B.dump, 'pure.bytecode' ],
    # [ B.bitslice, 64, size ],

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
