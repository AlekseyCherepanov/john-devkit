# -*- coding: utf-8 -*-
# Example of john-devkit's usage

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from dk import *

code = []
with L.evaluate_to(code):
    L.Var.setup(4, 'le')
    a, b = L.input(), L.input()
    c = a + b
    print c   # says <lang_main.Var object at 0x...>
    L.output(c)

for instruction in code:
    print instruction

c_template = r'''
#include <stdio.h>
int main(void)
{
    $type out, in[2] = { 11, 22 };
#define dk_input(i) (in[(i)])
#define dk_output(v, i) (out = (v))
    $code
    printf("from C: %d\n", out);
}'''

O.gen(code, 't.c', c_template, {}, {})

print "END of Python"
os.system('gcc t.c -o t && ./t')
