# -*- coding: utf-8 -*-
# TrueCrypt format for john

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from dk import *

# B.thread_code(B.evaluate('''
# Var.setup(4, 'be')
# m = module_begin('plain', 'm1')
# Var.setup(4, 'be')
# a = input()
# b = input()
# output(a + b + 1)
# module_end(m)
# r1 = invoke_plain(m, 3, 4)
# r2 = invoke_plain(m, 1, 2)
# print_many(r1[0], r2[0])
# '''),
# B.check_types,
# [ B.inline_function, 'plain', 'm1' ],
# B.dump,
# [ B.interpret, [], 'run' ],
# B.my_exit)

# B.thread_code(B.evaluate('''
# m = module_begin('hfun', 'm1')
# k = input_key()
# o = bytes_concat(k, k)
# output_bytes(o)
# module_end(m)
# kk = input_key()
# r = invoke_hfun(m, kk)
# print_bytes(r)
# output_bytes(r)
# '''),
# B.check_types,
# [ B.inline_hfun, 'm1' ],
# B.dump,
# [ B.interpret, [], 'run', 'hi there!' ],
# B.my_exit)

# B.thread_code(B.evaluate('''
# m = module_begin('plain', 'm1')
# Var.setup('be', 8)
# a = input()
# b = input()
# output(a + b)
# module_end(m)
# k = input_key()
# run_merkle_damgard_with_state(m, k, 0, 11, 22)
# '''),
# B.dump,
# B.unroll_block_from_merkle_damgard,
# B.dump,
# B.my_exit)

# B.thread_code(B.evaluate('''
# m = module_begin('plain', 'm1')
# m2 = module_begin('plain', 'm2')
# module_end(m2)
# module_end(m)
# '''),
# B.dump,
# B.flatten_modules,
# B.dump,
# B.my_exit)

john_base = 'JohnTheRipper/src/'

c_template = 'john_truecrypt'
c_code = U.load_code_template(c_template)

algo_file = 'truecrypt_sha512'
# %% это должно быть, как в джоне
algo_name = 'TrueCrypt_SHA512'
algo_upper = algo_name.upper()

args = {}

algo_code = B.get_code_full(algo_file, **args)
d = algo_code

tests = slurp_file(get_dk_path('hash_tests/john_truecrypt_sha512.c'))

tag = 'truecrypt_SHA_512$'

fmt_name = 'dk-' + algo_name

vs = {
    'fmt_struct_name': 'dk1_' + algo_name,
    'format_name': fmt_name,
    'algo_name': 'dk ' + algo_name,
    'tag': tag,
    # 'plaintext_length': (inputs - 2) * size - 1,
    # 'binary_form_size': outputs * size,
    'tests': tests
}
bs_size = 64
O.apply_bs_size(bs_size)
U.setup_vars(vs)
out_file = U.fmt_file(vs['format_name'])

d = B.thread_code(
    d,
    B.check_types,

    # B.flatten_modules,
    B.compute_hfun_sizes,
    B.flatten_modules,
    [ B.inline_function, 'hfun', 'sha512' ],
    B.unroll_merkle_damgard,
    B.opt_bytes_concat_split,
    B.opt_bytes_join_split,
    B.fix_run_merkle_damgard,
    # B.print_bytes_lengths,
    # B.unroll_block_from_merkle_damgard,

    B.compute_const_lengths,
    B.opt_bytes_concat_slice,
    [ B.lift_from_cycle, 'rounds' ],
    [ B.unroll_cycle_const_range, 'main' ],
    B.drop_unused,
    B.split_bytes_pbkdf2,

    [ B.dump, 'before1.bytecode' ],
    [ B.inline_function, 'plain', 'sha512' ],
    [ B.dump, 'before2.bytecode' ],

    # [ B.unroll_cycle_const_range_partly, 'setupW', 4 ],
    # [ B.dump, 'before1.bytecode' ],
    # B.print_bytes,

    [ B.dump, 'all.bytecode' ],
    B.check_types,

    # [ B.interpret, [], None, 'password', None, '\xaaX*\xfed\x19z<\xfdO\xafv\x97g>^\x14ACi\xda?qd\x00AOc\xf7TG\xda}:\xbd\xc6Z%\xeaQ\x1b\x17r\xd6sp\xd6\xc3I\xd8\x00\r\xe6me\x86\x14\x03\t?\xec\xfb\x85q', None, '\x9e\x1dF\x15\x8d$2NZ,\x0e\xe5\x98!K\x1b' ],
    # B.my_exit,

    [ O.gen, out_file, c_code, args, B.global_vars ]
)

if U.build_john():
    U.run_test(fmt_name)
    U.count_bytes(U.fmt_file(fmt_name, ext = 'o'))
