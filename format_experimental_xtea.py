# -*- coding: utf-8 -*-
# not a real format, just experiment with XTEA and interpreter

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import util_ui as U
import bytecode_main as B
from util_main import *

code = B.get_code_full('xtea')

# values from "unholy" task in BKP CTF 2016
key = [ 0x74616877, 0x696f6773, 0x6e6f676e, 0x65726568 ]

# Computation forward
encrypt = B.thread_code( code,
    [ B.override_state, key ],
    B.replace_state_with_const,
    [ B.interpret,
      # values from "unholy" task in BKP CTF 2016
      [ 1129335618, 1752909396 ],
      [ 2990080719, 722035088 ] ]
)

# B.dump(encrypt, 'forward.bytecode')

# Computation backwards
decrypt = B.reverse_full(B.deep_copy(encrypt))
B.thread_code( decrypt,
    [ B.interpret,
      # values from "unholy" task in BKP CTF 2016
      [ 2990080719, 722035088 ],
      [ 1129335618, 1752909396 ] ]
)
