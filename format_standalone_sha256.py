# -*- coding: utf-8 -*-
# sha-512 with output to standalone binary

import util_ui as U
import bytecode_main as B
import output_standalone as O

args = U.parse_args()

size = 4

args['args'] = { 'size': size }

sha256 = B.get_code_full('sha256', **args)
padding = B.get_code_full('padding', **args)

code = B.join_parts(padding, sha256)

O.apply_size(size)
O.main(code, args)
