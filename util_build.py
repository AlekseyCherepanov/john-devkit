# -*- coding: utf-8 -*-

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from util_main import *

# %% a lot of hardcoded paths

john_base = 'JohnTheRipper/src/'

def fmt_file(fmt_name, ext = 'c'):
    return john_base + 'dk_{0}_fmt_plug.{1}'.format(fmt_name, ext)

def count_bytes(name):
    print name
    a = shell_quote(name)
    os.system('objdump -d ' + a + ''' | perl -ne 'if (/<crypt_all>/ .. /^$/) { $a .= $_; } END { $_ = $a; warn s/\n/\n/g, " asm\n"; s/^[^\t]*\t//gm; s/\t.*$//gm; s/\s+//g; print(length($_) / 2, " bytes of code\n") }' ''')

def build_john():
    return not os.system(''' cd JohnTheRipper/src/ && RELEASE_BLD="-Wfatal-errors -g -Wno-unused-but-set-variable" make -s ''')

def run_test(format_name, time = 5):
    os.system(''' JohnTheRipper/run/john --test={0} --format={1} '''.format(time, shell_quote(format_name)))
