# -*- coding: utf-8 -*-
# sha384 with output to john's format

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
algo_file = 'sha512'

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
{"a8b64babd0aca91a59bdbb7761b421d4f2bb38280d3a75ba0f21f2bebc45583d446c598660c94ce680c47d19c30783a7", "password"},
{"$SHA384$a8b64babd0aca91a59bdbb7761b421d4f2bb38280d3a75ba0f21f2bebc45583d446c598660c94ce680c47d19c30783a7", "password"},
{"$SHA384$8cafed2235386cc5855e75f0d34f103ccc183912e5f02446b77c66539f776e4bf2bf87339b4518a7cb1c2441c568b0f8", "12345678"},
{"$SHA384$38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6e1da274edebfe76f65fbd51ad2f14898b95b", ""},
'''

vs = {
    'fmt_struct_name': 'raw1_sha384',
    'format_name': 'Raw-SHA384',
    'algo_name': 'SHA384',
    'tag': '$SHA384$',
    'plaintext_length': '111',
    'binary_form_size': '48', # 64 - 2*8
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

# http://en.wikipedia.org/wiki/SHA2
# sha384 is sha512 with other initial values and 2 outputs dropped

state = [
    0xcbbb9d5dc1059ed8, 0x629a292a367cd507,
    0x9159015a3070dd17, 0x152fecd8f70e5939,
    0x67332667ffc00b31, 0x8eb44a8768581511,
    0xdb0c2e0d64f98fa7, 0x47b5481dbefa4fa4
]

code = B.thread_code( B.get_code_full(algo_file, **args),
    [ B.override_state, state ],
# %% there should 3 such filter, where is the last? typo?
    B.drop_last_output,
    B.drop_last_output
)

interleave = 1

B.global_vars['batch_size'] = 20

reverse_num = 5

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
