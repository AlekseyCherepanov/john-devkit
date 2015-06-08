# -*- coding: utf-8 -*-

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import sys

import bytecode_main as B

# %% файл надо переименовать в util

# %% надо бы это убрать
def parse_args():
    # %% improve it
    use_tracer = False
    use_bitslice = False
    if len(sys.argv) > 1:
        use_tracer = sys.argv[1] == "t"
    if len(sys.argv) > 2:
        use_bitslice = sys.argv[2] == "b"
    return {'use_tracer': use_tracer, 'use_bitslice': use_bitslice}


def load_code_template(name):
    with file('/home/a/d/john-devkit-dirty/t_{0}.c'.format(name), 'r') as f:
        c_code = f.read()
    return c_code

def setup_vars(vs):
    for v in vs:
        B.global_vars[v] = vs[v]
