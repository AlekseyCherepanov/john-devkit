# -*- coding: utf-8 -*-
# Library that is included into environment of all algo_* files

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

def sph_prepare_linear_c_for_import(code):
    code = re.sub(r'^\s+sph_u(?:64|32) .*$', '', code, flags = re.M)
    code = re.sub(r'^\s+', '', code, flags = re.M)
    code = code.replace('do {', '').replace('} while (0)', '')
    pi, po = os.popen2('gcc -E -')
    pi.write(code)
    pi.close()
    r = po.read()
    po.close()
    r = r.replace(';', '\n')
    # === in C for assignment in dk
    r = r.replace('===', '//')
    r = re.sub(r'^\s+', '', r, flags = re.M)
    return r
