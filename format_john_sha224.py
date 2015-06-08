# -*- coding: utf-8 -*-
# sha224 with output to john's format

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
algo_file = 'sha256'

c_code = U.load_code_template(c_template)

size = 4
endianity = 'be'

args['args'] = { 'size': size }

O.apply_size(size)
O.apply_endianity(endianity)

bs_size = 64
O.apply_bs_size(bs_size)

# Format setup

tests = '''
{"d63dc919e201d7bc4c825630d2cf25fdc93d4b2f0d46706d29038d01", "password"},
{"$SHA224$d63dc919e201d7bc4c825630d2cf25fdc93d4b2f0d46706d29038d01", "password"},
{"$SHA224$7e6a4309ddf6e8866679f61ace4f621b0e3455ebac2e831a60f13cd1", "12345678"},
{"$SHA224$d14a028c2a3a2bc9476102bb288234c415a2b01f828ea62ac5b3e42f", ""},
'''

vs = {
    'fmt_struct_name': 'raw1_sha224',
    'format_name': 'Raw-SHA224',
    'algo_name': 'SHA224',
    'tag': '$SHA224$',
    'plaintext_length': '55',
    'binary_form_size': '28',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

# http://en.wikipedia.org/wiki/SHA256
# sha224 is sha256 with other initial values and one output dropped

state = [
    0xc1059ed8, 0x367cd507, 0x3070dd17, 0xf70e5939, 0xffc00b31, 0x68581511, 0x64f98fa7, 0xbefa4fa4
]

code = B.thread_code( B.get_code_full(algo_file, **args),
    [ B.override_state, state ],
    B.drop_last_output
)

interleave = 1

B.global_vars['batch_size'] = 20

reverse_num = 6

B.global_vars['interleave'] = interleave
B.global_vars['reverse_num'] =  reverse_num

B.global_vars['vectorize'] = 1

d = B.thread_code( code,
    B.replace_state_with_const,
    [ B.dump, 'pure.bytecode' ],
    # [ B.bitslice, 64, size ],
    # [ B.unroll_cycle_const_range, 'setupW' ],
    # [ B.unroll_cycle_const_range_partly, 'setupW', 16 ],
    # [ B.unroll_cycle_const_range_partly, 'main', 40 ],

    [ B.unroll_cycle_const_range, 'main' ],
    [ B.unpack_const_subscripts, 'k' ],
    B.remove_assignments,
    B.compute_const_expressions,

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
    [ B.unroll_cycle_const_range_partly, 'setupW', 16 ],
    # [ B.unroll_cycle_const_range, 'setupW' ],
    # [ B.unroll_cycle_const_range_partly, 'main', 2 ],
    B.use_define_for_some,
    [ B.interleave, interleave ],
    [ B.dump, 'code.bytecode' ],
    [ O.gen, c_code, args, B.global_vars ]
)
