# -*- coding: utf-8 -*-
# sha256, file for experiments

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import util_ui as U
import bytecode_main as B
import output_c as O
# import output_c_sse as O

# args = U.parse_args()

c_template = 'ocl_test'
algo_file = 'sha256'

# c_code = U.load_code_template(c_template)
c_code = U.load_cl_template(c_template)

size = 4
endianity = 'be'

args = {}
args['args'] = { 'size': size }

# O.apply_size(size)
# O.apply_endianity(endianity)

# bs_size = 64
bs_size = 32
O.apply_bs_size(bs_size)

# Format setup

tests = '''
#define HEX_TAG "$SHA256$"
/* No cisco hashes in this version */
{"71c3f65d17745f05235570f1799d75e69795d469d9fcb83e326f82f1afa80dea", "epixoip"},
{HEX_TAG "71c3f65d17745f05235570f1799d75e69795d469d9fcb83e326f82f1afa80dea", "epixoip"},
{"25b64f637b373d33a8aa2b7579784e99a20e6b7dfea99a71af124394b8958f27", "doesthiswork"},
{"5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", "password"},
{"27c6794c8aa2f70f5f6dc93d3bfb25ca6de9b0752c8318614cbd4ad203bea24c", "ALLCAPS"},
{"04cdd6c523673bf448efe055711a9b184817d7843b0a76c2046f5398b5854152", "TestTESTt3st"},
{HEX_TAG "ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f", "12345678"},
{HEX_TAG "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", ""},
{HEX_TAG "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855", ""},
{"a49c2c9d0c006c8cb55a9a7a38822b83e0cd442614cb416af952fa50156761dc", "openwall"},
{"9e7d3e56996c5a06a6a378567e62f5aa7138ebb0f55c0bdaf73666bf77f73380", "mot\xf6rhead"},
{"1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014", "test1"},
{"fd61a03af4f77d870fc21e05e7e80678095c92d808cfb3b5c279ee04c74aca13", "test3"},
{"d150eb0383c8ef7478248d7e6cf18db333e8753d05e15a8a83714b7cf63922b3", "thatsworking"},
{"c775e7b757ede630cd0aa1113bd102661ab38829ca52a6422ab782862f268646", "1234567890"},
#if PLAINTEXT_LENGTH > 19 //Has to be inside a header, it check againt a #define.
{"6ed645ef0e1abea1bf1e4e935ff04f9e18d39812387f63cda3415b46240f0405", "12345678901234567890"},
{"f54e5c8f810648e7638d25eb7ed6d24b7e5999d588e88826f2aa837d2ee52ecd", "123456789012345678901234567890"},
{"a4ebdd541454b84cc670c9f1f5508baf67ffd3fe59b883267808781f992a0b1d", "1234567890123456789012345678901234567890"},
{"f58fffba129aa67ec63bf12571a42977c0b785d3b2a93cc0538557c91da2115d", "12345678901234567890123456789012345678901234567890"},
{"3874d5c9cc5ab726e6bbebadee22c680ce530004d4f0bb32f765d42a0a6c6dc1", "123456789012345678901234567890123456789012345678901"},
{"03c3a70e99ed5eeccd80f73771fcf1ece643d939d9ecc76f25544b0233f708e9", "1234567890123456789012345678901234567890123456789012345"},
{"0f46e4b0802fee6fed599682a16287d0397699cfd742025482c086a70979e56a", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}, // 31
{"c62e4615bd39e222572f3a1bf7c2132ea1e65b17ec805047bd6b2842c593493f", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}, // 32
{"d5e285683cd4efc02d021a5c62014694958901005d6f71e89e0989fac77e4072", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}, // 55
#endif
'''

vs = {
    'fmt_struct_name': 'raw1_sha256',
    'format_name': 'Raw-SHA256',
    'algo_name': 'SHA256',
    'tag': '$SHA256$',
    'plaintext_length': '55',
    'binary_form_size': '32',
    'tests': tests
}

U.setup_vars(vs)


# Optimizations and code generation

# http://en.wikipedia.org/wiki/SHA256
# sha224 is sha256 with other initial values and one output dropped

interleave = 1

# B.global_vars['batch_size'] = 20
# B.global_vars['batch_size'] = 16
B.global_vars['batch_size'] = 1

reverse_num = 7

B.global_vars['interleave'] = interleave
B.global_vars['reverse_num'] =  reverse_num

B.global_vars['vectorize'] = 1


# B.thread_code( B.get_code_full(algo_file, **args),
#     B.drop_print,
#     B.replace_state_with_const,

#     # [ B.unroll_cycle_const_range, 'setupW' ],
#     # [ B.unroll_cycle_const_range, 'main' ],
#     # [ B.unpack_const_subscripts, 'k' ],
#     # B.remove_assignments,
#     # [ B.compute_const_expressions, size ],
#     # B.drop_arrays,
#     # [ B.compute_const_expressions, size ],

#     [ B.dump, 'pre.bytecode' ],
#     [ B.bitslice ],
#     B.drop_unused,
#     [ B.dump, 'test.bytecode' ],
#     [ B.interpret,
#       [ 0x65706978, 0x6f697080, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000038 ],
#       [ 0x71c3f65d, 0x17745f05, 0x235570f1, 0x799d75e6, 0x9795d469, 0xd9fcb83e, 0x326f82f1, 0xafa80dea ]],
#     B.my_exit,
# )


# d = B.thread_code( B.get_code_full(algo_file, **args),
#     B.replace_state_with_const,
#     [ B.dump, 'pure.bytecode' ],
#     # [ B.unroll_cycle_const_range, 'setupW' ],
#     # [ B.unroll_cycle_const_range_partly, 'setupW', 16 ],
#     # [ B.unroll_cycle_const_range_partly, 'main', 40 ],

#     # B.drop_print,

#     # [ B.unroll_cycle_const_range, 'main' ],
#     # [ B.unpack_const_subscripts, 'k' ],
#     # B.remove_assignments,
#     # [ B.compute_const_expressions, size ],

#     # [ B.reduce_assignments, 'main', 'main_end' ],
#     # [ B.dump, 'all.bytecode' ],
#     # B.research_reverse,
#     # [ B.reverse_ops, reverse_num ],

#     # [ B.no_reverse, reverse_num ],
# )

# code = d['code']
# code = d

code = B.get_code_full(algo_file, **args)

B.global_vars['bs'] = 0

B.global_vars['bs'] = 1

if B.global_vars['bs']:
    code = B.thread_code( code,
        B.replace_state_with_const,

        # B.drop_print,

        # [ B.unroll_cycle_const_range, 'setupW' ],
        # [ B.unroll_cycle_const_range, 'main' ],
        # [ B.unpack_const_subscripts, 'k' ],
        # B.remove_assignments,
        # [ B.compute_const_expressions, size ],
        # B.drop_arrays,
        # [ B.compute_const_expressions, size ],

        [ B.bitslice ],

        B.drop_unused,

        # [ B.dump, "int.bytecode" ],
        # [ B.interpret,
        #   [ 0x61626364, 0x00000000, 0x71776572, 0x80000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000060 ],
        #   [ 0x0166844e, 0x6a0f4428, 0xf75ed9da, 0x4fb2c503, 0x0d4e393c, 0xd699502a, 0xf618aa33, 0x43c9f865 ]],
        # B.my_exit,

        # [ B.interpret,
        #   [ 0x65706978, 0x6f697080, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000038 ],
        #   [ 0x71c3f65d, 0x17745f05, 0x235570f1, 0x799d75e6, 0x9795d469, 0xd9fcb83e, 0x326f82f1, 0xafa80dea ]],
        # B.my_exit,

        # [ B.dump, 'post.bytecode' ],
    )

code = B.thread_code( code,
    # [ B.unroll_cycle_const_range_partly, 'main', 2 ],

    # B.use_define_for_some,

    [ B.interleave, interleave ],
    [ B.dump, 'code.bytecode' ],
)

# code = B.slurp_bytecode('myrgr_optimized.bytecode')

B.thread_code( code,
    [ O.gen, c_code, args, B.global_vars ]
)
