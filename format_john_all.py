# -*- coding: utf-8 -*-
# script to output various formats for John the Ripper

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import util_ui as U
import bytecode_main as B
import output_c as O
from util_main import *

# args = U.parse_args()

bs_size = 64

def fmt_name_raw(algo):
    return 'dk-raw-' + algo

john_base = 'JohnTheRipper/src/'

def fmt_file(fmt_name, ext = 'c'):
    return john_base + 'dk_{0}_fmt_plug.{1}'.format(fmt_name, ext)

def gen_raw_format(c_template, algo_file, tests, tag = None, special1 = None, special2 = None, special0 = None, reverse_num = 0, algo_override = None):
    c_code = U.load_code_template(c_template)

    args = {}

    # # %% extract that from code
    # size = 4
    # endianity = 'be'

    algo_name = algo_file
    algo_upper = algo_name.upper()

    algo_code = B.get_code_full(algo_override or algo_file, **args)
    d = algo_code
    if special0:
        d = B.thread_code(d, *special0)

    interface = B.get_interface(d)
    size = interface['size']
    endianity = interface['endianity']
    inputs = interface['inputs']
    outputs = interface['outputs']

    print interface

    if not tag:
        tag = '$' + algo_upper + '$'

    vs = {
        'fmt_struct_name': 'raw1_' + algo_name,
        'format_name': fmt_name_raw(algo_name),
        'algo_name': 'dk ' + algo_upper,
        'tag': tag,
        'plaintext_length': (inputs - 2) * size - 1,
        'binary_form_size': outputs * size,
        'tests': tests
    }
    O.apply_bs_size(bs_size)

    U.setup_vars(vs)

    # Optimizations and code generation

    interleave = 1
    B.global_vars['batch_size'] = 1
    # reverse_num = 7
    B.global_vars['interleave'] = interleave
    B.global_vars['reverse_num'] =  reverse_num

    B.global_vars['vectorize'] = 1

    d = B.thread_code(d, B.replace_state_with_const)

    if special1:
        d = B.thread_code(d, *special1)

    d = B.thread_code( d,
        B.remove_assignments,
        [ B.compute_const_expressions, size ],
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

    out_file = fmt_file(vs['format_name'])

    d = B.thread_code( code,
        B.vectorize)

    if special2:
        d = B.thread_code(d, *special2)

    d = B.thread_code( d,
        B.use_define_for_some,
        [ B.interleave, interleave ],
        [ O.gen, out_file, c_code, args, B.global_vars ]
    )

def count_bytes(name):
    print name
    a = shell_quote(name)
    os.system('objdump -d ' + a + ''' | perl -ne 'if (/<crypt_all>/ .. /^$/) { $a .= $_; } END { $_ = $a; warn s/\n/\n/g, " asm\n"; s/^[^\t]*\t//gm; s/\t.*$//gm; s/\s+//g; print(length($_) / 2, " bytes of code\n") }' ''')

def build_john():
    return not os.system(''' cd JohnTheRipper/src/ && RELEASE_BLD="-Wfatal-errors -g -Wno-unused-but-set-variable" make -s ''')

def run_test(format_name):
    os.system(''' JohnTheRipper/run/john --test=5 --format={0} '''.format(shell_quote(format_name)))

sha2_special = { 'special1' :
                    [ [ B.unroll_cycle_const_range, 'main' ],
                      [ B.unpack_const_subscripts, 'k' ] ],
                 'special2' :
                    [ [ B.unroll_cycle_const_range_partly, 'setupW', 16 ] ] }

fmts = [

    # [ 'sha256', 7, sha2_special ],
    # [ 'sha512', 7, sha2_special ],
    # [ 'md5', 0, {} ],
    # [ 'md4', 0, {} ],
    # [ 'sha224', 6, dict(sha2_special.items() + [('special0', [
    #     [ B.override_state, [ 0xc1059ed8, 0x367cd507, 0x3070dd17, 0xf70e5939, 0xffc00b31, 0x68581511, 0x64f98fa7, 0xbefa4fa4 ] ],
    #     B.drop_last_output ]),
    #                                             ('algo_override', 'sha256')]) ],
    # [ 'sha384', 4, dict(sha2_special.items() + [('special0', [
    #     [ B.override_state, [ 0xcbbb9d5dc1059ed8, 0x629a292a367cd507, 0x9159015a3070dd17, 0x152fecd8f70e5939, 0x67332667ffc00b31, 0x8eb44a8768581511, 0xdb0c2e0d64f98fa7, 0x47b5481dbefa4fa4 ] ],
    #     B.drop_last_output,
    #     B.drop_last_output,
    #     B.drop_last_output ]),
    #                                             ('algo_override', 'sha512')]) ],

    [ 'sha1', 4, { 'tag' : '$dynamic_26$' } ]

]

for f in fmts:
    special = {}
    rn = 0
    if type(f) != str:
        f, rn, special = f
    special['reverse_num'] = rn
    gen_raw_format('raw', f, slurp_file(get_dk_path('hash_tests/john_raw-' + f + '.c')), **special)

if build_john():
    for f in fmts:
        f = f[0]
        print '>>', f
        fn = fmt_name_raw(f)
        run_test(fn)
        count_bytes(fmt_file(fn, ext = 'o'))
