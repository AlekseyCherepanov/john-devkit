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
algo_file = 'sha1'

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
{"c3e337f070b64a50e9d31ac3f9eda35120e29d6c", "digipalmw221u"},
{ "da39a3ee5e6b4b0d3255bfef95601890afd80709", ""                },
{ "AC80BAA235B7FB7BDFC593A976D40B24B851F924", "CAPSLOCK"        },
{ "86f7e437faa5a7fce15d1ddcb9eaeaea377667b8", "a"               },
{ "da23614e02469a0d7c7bd1bdab5c9c474b1904dc", "ab"              },
{ "a9993e364706816aba3e25717850c26c9cd0d89d", "abc"             },
{ "81fe8bfe87576c3ecb22426f8e57847382917acf", "abcd"            },
{ "03de6c570bfe24bfc328ccd7ca46b76eadaf4334", "abcde"           },
{ "1f8ac10f23c5b5bc1167bda84b833e5c057a77d2", "abcdef"          },
{ "2fb5e13419fc89246865e7a324f476ec624e8740", "abcdefg"         },
{ "425af12a0743502b322e93a015bcf868e324d56a", "abcdefgh"        },
{ "c63b19f1e4c8b5f76b25c49b8b87f57d8e4872a1", "abcdefghi"       },
{ "d68c19a0a345b7eab78d5e11e991c026ec60db63", "abcdefghij"      },
{ "5dfac39f71ad4d35a153ba4fc12d943a0e178e6a", "abcdefghijk"     },
{ "eb4608cebfcfd4df81410cbd06507ea6af978d9c", "abcdefghijkl"    },
{ "4b9892b6527214afc655b8aa52f4d203c15e7c9c", "abcdefghijklm"   },
{ "85d7c5ff403abe72df5b8a2708821ee33cd0bcce", "abcdefghijklmn"  },
{ "2938dcc2e3aa77987c7e5d4a0f26966706d06782", "abcdefghijklmno" },
{ "f8252c7b6035a71242b4047782247faabfccb47b", "taviso"          },
{ "b47f363e2b430c0647f14deea3eced9b0ef300ce", "is"              },
{ "03d67c263c27a453ef65b29e30334727333ccbcd", "awesome"         },
{ "7a73673e78669ea238ca550814dca7000d7026cc", "!!!!1111eleven"  },
// repeat last hash in exactly the same format that is used for john.pot
{"$dynamic_26$7a73673e78669ea238ca550814dca7000d7026cc", "!!!!1111eleven"},
'''

vs = {
    'fmt_struct_name': 'raw1_sha1',
    'format_name': 'Raw-SHA1',
    'algo_name': 'SHA1',
    'tag': '$dynamic_26$',
    'plaintext_length': '55',
    'binary_form_size': '20',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

interleave = 1
# interleave = 2

B.global_vars['batch_size'] = 1
B.global_vars['batch_size'] = 10
B.global_vars['batch_size'] = 20
B.global_vars['batch_size'] = 16

reverse_num = 4

B.global_vars['interleave'] = interleave
B.global_vars['reverse_num'] =  reverse_num

B.global_vars['vectorize'] = 1

d = B.thread_code( B.get_code_full('sha1_registers', **args),

# d = B.thread_code( B.get_code_full(algo_file, **args),
#     B.replace_state_with_const,
#     [ B.unroll_cycle_const_range, 'setupW' ],
#     B.remove_assignments,
#     [ B.compute_const_expressions, size ],
#     B.drop_arrays,
#     B.drop_print,
#     [ B.compute_const_expressions, size ],
#     B.drop_unused,
#     [ B.dump, 'all.bytecode' ],
#     B.gen_asm,
#     [ B.dump, 'asm.bytecode' ],
# )
# exit(0)

# d = B.thread_code( B.get_code_full(algo_file, **args),

    B.replace_state_with_const,
    [ B.dump, 'pure.bytecode' ],
    # [ B.bitslice, 64, size ],

    # [ B.unroll_cycle_const_range, 'setupW' ],
    # [ B.unroll_cycle_const_range_partly, 'setupW', 16 ],

    # [ B.unroll_cycle_const_range, 'setupW' ],
    # B.remove_assignments,
    # [ B.compute_const_expressions, size ],
    # B.drop_arrays,
    # B.drop_print,
    # [ B.compute_const_expressions, size ],
    # B.drop_unused,

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
    # [ B.unroll_cycle_const_range_partly, 'setupW', 2 ],
    # [ B.unroll_cycle_const_range, 'setupW' ],
    # [ B.unroll_cycle_const_range_partly, 'main', 2 ],
    # B.use_define_for_some,
    [ B.interleave, interleave ],
    [ B.dump, 'code.bytecode' ],
    [ O.gen, c_code, args, B.global_vars ]
)
