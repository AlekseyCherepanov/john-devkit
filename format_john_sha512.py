# -*- coding: utf-8 -*-
# sha512 with output to john's format

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
{"f342aae82952db35b8e02c30115e3deed3d80fdfdadacab336f0ba51ac54e297291fa1d6b201d69a2bd77e2535280f17a54fa1e527abc6e2eddba79ad3be11c0", "epixoip"},
{FORMAT_TAG "f342aae82952db35b8e02c30115e3deed3d80fdfdadacab336f0ba51ac54e297291fa1d6b201d69a2bd77e2535280f17a54fa1e527abc6e2eddba79ad3be11c0", "epixoip"},
{"b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb980b1d7785e5976ec049b46df5f1326af5a2ea6d103fd07c95385ffab0cacbc86", "password"},
{"2c80f4c2b3db6b677d328775be4d38c8d8cd9a4464c3b6273644fb148f855e3db51bc33b54f3f6fa1f5f52060509f0e4d350bb0c7f51947728303999c6eff446", "john-user"},
{"71ebcb1eccd7ea22bd8cebaec735a43f1f7164d003dacdeb06e0de4a6d9f64d123b00a45227db815081b1008d1a1bbad4c39bde770a2c23308ff1b09418dd7ed", "ALLCAPS"},
{"82244918c2e45fbaa00c7c7d52eb61f309a37e2f33ea1fba78e61b4140efa95731eec849de02ee16aa31c82848b51fb7b7fbae62f50df6e150a8a85e70fa740c", "TestTESTt3st"},
{"fa585d89c851dd338a70dcf535aa2a92fee7836dd6aff1226583e88e0996293f16bc009c652826e0fc5c706695a03cddce372f139eff4d13959da6f1f5d3eabe", "12345678"},
{FORMAT_TAG "fa585d89c851dd338a70dcf535aa2a92fee7836dd6aff1226583e88e0996293f16bc009c652826e0fc5c706695a03cddce372f139eff4d13959da6f1f5d3eabe", "12345678"},
{FORMAT_TAG "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e", ""},
{"c96f1c1260074832bd3068ddd29e733090285dfc65939555dbbcafb27834957d15d9c509481cc7df0e2a7e21429783ba573036b78f5284f9928b5fef02a791ef", "mot\xf6rhead"},
{"aa3b7bdd98ec44af1f395bbd5f7f27a5cd9569d794d032747323bf4b1521fbe7725875a68b440abdf0559de5015baf873bb9c01cae63ecea93ad547a7397416e", "12345678901234567890"},
{"db9981645857e59805132f7699e78bbcf39f69380a41aac8e6fa158a0593f2017ffe48764687aa855dae3023fcceefd51a1551d57730423df18503e80ba381ba", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
{"7aba4411846c61b08b0f2282a8a4600232ace4dd96593c755ba9c9a4e7b780b8bdc437b5c55574b3e8409c7b511032f98ef120e25467678f0458643578eb60ff", "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901"},
// this one DOES NOT work for a 1 limb. Only 111 bytes max can be used, unless we do 2 sha512 limbs.
//{"a5fa73a3c9ca13df56c2cb3ae6f2e57671239a6b461ef5021a65d08f40336bfb458ec52a3003e1004f1a40d0706c27a9f4268fa4e1479382e2053c2b5b47b9b2", "12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789"},
#ifdef DEBUG //Special test cases.
{"12b03226a6d8be9c6e8cd5e55dc6c7920caaa39df14aab92d5e3ea9340d1c8a4d3d0b8e4314f1f6ef131ba4bf1ceb9186ab87c801af0d5c95b1befb8cedae2b9", "1234567890"},
{"eba392e2f2094d7ffe55a23dffc29c412abd47057a0823c6c149c9c759423afde56f0eef73ade8f79bc1d16a99cbc5e4995afd8c14adb49410ecd957aecc8d02", "123456789012345678901234567890"},
{"3a8529d8f0c7b1ad2fa54c944952829b718d5beb4ff9ba8f4a849e02fe9a272daf59ae3bd06dde6f01df863d87c8ba4ab016ac576b59a19078c26d8dbe63f79e", "1234567890123456789012345678901234567890"},
{"49c1faba580a55d6473f427174b62d8aa68f49958d70268eb8c7f258ba5bb089b7515891079451819aa4f8bf75b784dc156e7400ab0a04dfd2b75e46ef0a943e", "12345678901234567890123456789012345678901234567890"},
{"8c5b51368ec88e1b1c4a67aa9de0aa0919447e142a9c245d75db07bbd4d00962b19112adb9f2b52c0a7b29fe2de661a872f095b6a1670098e5c7fde4a3503896", "123456789012345678901234567890123456789012345678901"},
{"35ea7bc1d848db0f7ff49178392bf58acfae94bf74d77ae2d7e978df52aac250ff2560f9b98dc7726f0b8e05b25e5132074b470eb461c4ebb7b4d8bf9ef0d93f", "1234567890123456789012345678901234567890123456789012345"},
#endif
'''

vs = {
    'fmt_struct_name': 'raw1_sha512',
    'format_name': 'Raw-SHA512',
    'algo_name': 'SHA512',
    'tag': '$SHA512$',
    'plaintext_length': '111',
    'binary_form_size': '64',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

code = B.get_code_full(algo_file, **args)

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
