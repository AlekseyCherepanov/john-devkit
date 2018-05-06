# temp file to test 'with code' feature

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import lang_main as L
import bytecode_main as B

code = []

with L.evaluate_to(code, 'var'):
    a = L.input()
    b = L.input()
    two = L.new_const(2)
    print two
    c = a + b + 1
B.dump(code)
