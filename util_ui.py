# -*- coding: utf-8 -*-

import sys

def parse_args():
    # %% improve it
    use_tracer = False
    use_bitslice = False
    if len(sys.argv) > 1:
        use_tracer = sys.argv[1] == "t"
    if len(sys.argv) > 2:
        use_bitslice = sys.argv[2] == "b"
    return {'use_tracer': use_tracer, 'use_bitslice': use_bitslice}

