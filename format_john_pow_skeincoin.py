# -*- coding: utf-8 -*-
# skeincoin pow hash with output to john's format
# No comparison with target, it just searches for precise hash.

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
# endianity = 'be'

args['args'] = { 'size': size, 'use_unroll': 1, 'two_blocks': 1 }

# O.apply_size(size)
# O.apply_endianity(endianity)

# bs_size = 64
# O.apply_bs_size(bs_size)

# Format setup

# %% add a test sensitive to byte order, something like "abcdef..."
tests = r'''
{"4ed421fae24da5b0bfa55c1c01c7b58015726ccba215280a9b832d6925eaa7fe", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
//{"9f24d5851f9ac0b114dcdfacc6b8546e9f020cef37645c2227a3de9ebb42a416", "abc"},
//{"67309cc5ded80d88a984217a487939de059862f929f496640f46fb5105d1cce7", "abcd"},
'''

vs = {
    'fmt_struct_name': 'raw1_pow_skeincoin',
    'format_name': 'raw-pow_skeincoin',
    'algo_name': 'SKEINCOIN',
    'tag': '$skeincoin$',
    # %% bump length
    'plaintext_length': '80',
    'binary_form_size': '32',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

interleave = 1

# B.global_vars['batch_size'] = 20
# B.global_vars['batch_size'] = 16
B.global_vars['batch_size'] = 1

B.global_vars['interleave'] = interleave

# skein512 loading

skein = B.thread_code( B.get_code_full(algo_file, **args),
    B.replace_state_with_const,
    [ B.replace_length_with_const, 80 ],
    [ B.dump, 'skein1.bytecode' ],
    [ B.compute_const_expressions, size ],
    # [ B.dump, 'skein2.bytecode' ],
    B.drop_print,
    # [ B.dump, 'skein.bytecode' ]
)

# border of var sizes

border = B.evaluate('''
inputs = [input() for i in range(8)]
inputs = map(swap_to_be, inputs)
map(print_var, inputs)
Var.setup(4, 'le')
outputs = []
for v in inputs:
    outputs.append(high(v))
    outputs.append(low(v))
# print_verbatim('hi')
for v in outputs:
    # v = swap_to_be(v)
    # print_var(v)
    output(v)
''')

# sha256 loading

# B.global_vars['skein'] = 0

sha = B.get_code_full('sha256', **args)

size = 4

sha_first = B.thread_code( sha,
    B.replace_state_with_const,
    [ B.unroll_cycle_const_range, 'setupW' ],
    [ B.unroll_cycle_const_range, 'main' ],
    [ B.unpack_const_subscripts, 'k' ],
    B.remove_assignments,
    [ B.compute_const_expressions, size ],
    B.drop_arrays,
    # B.drop_print,
    [ B.compute_const_expressions, size ],
    B.drop_unused,
)

outputs = B.collect_outputs(sha_first)
sha_first = B.drop_outputs(sha_first)

sha_second = B.thread_code( sha,
    B.rename_uniquely,
    [ B.replace_state_with_vars, outputs ],
    [ B.replace_inputs_with_consts, [ 0x80 << 24 ] + [0] * 14 + [ 512 ] ],
    [ B.unroll_cycle_const_range, 'setupW' ],
    [ B.unroll_cycle_const_range, 'main' ],
    [ B.unpack_const_subscripts, 'k' ],
    B.remove_assignments,
    [ B.compute_const_expressions, size ],
    B.drop_arrays,
    B.drop_print,
    [ B.compute_const_expressions, size ],
    B.drop_unused,
)

# combine 4 byte integers back into 8 byte integers

border2 = B.evaluate('''
inputs = [input() for i in range(8)]
Var.setup(8, 'le')
outputs = []
for i in range(0, len(inputs), 2):
    outputs.append(combine_low_high(inputs[i + 1], inputs[i]))
for v in outputs:
    v = swap_to_be(v)
    # print_var(v)
    output(v)
''')

# crypto scheme: sha256(skein512($p))
# combine everything

B.dump(skein + border + sha_first + sha_second + border2, 'all_dumb.bytecode')

code = B.connect_inputs_outputs(skein, border, sha_first + sha_second, border2)

B.dump(code, 'connected.bytecode')

codes = B.split_at(code, 'before_second_block')

# Print bitslice and exit.
d = B.thread_code( codes[0],
    [ B.bitslice ],
    B.drop_unused,
    [ B.dump, 'skeincoin1.bytecode' ]
)
d = B.thread_code( codes[1],
    [ B.bitslice ],
    B.drop_unused,
    [ B.dump, 'skeincoin2.bytecode' ]
)
exit(1)


# code generation

reverse_num = 0
B.global_vars['reverse_num'] =  reverse_num

d = B.no_reverse(code, reverse_num)

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

B.global_vars['vectorize'] = 0

B.global_vars['skein'] = 1

B.thread_code( code,
    # B.reuse_variables,
    B.vectorize_maybe,
    # B.use_define_for_some,
    [ B.interleave, interleave ],
    [ B.dump, 'code.bytecode' ],
    [ O.gen, c_code, args, B.global_vars ]
)
