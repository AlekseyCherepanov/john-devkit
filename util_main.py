# -*- coding: utf-8 -*-
# Common function useful anywhere
# %% maybe "_main" is wrong, maybe "_common" would be better, because
#  % it is not the 'import all' file for utility functions.

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import os
import sys
import re
from string import Template


def die(msg, *args):
    raise Exception(msg.format(*args))

def slurp_file(fname):
    with open(fname, 'r') as f:
        return f.read()

def get_dk_path(name):
    d = os.path.dirname(__file__)
    n = os.path.join(d, name)
    return n

def slurp_dk_file(name):
    return slurp_file(get_dk_path(name))

# http://stackoverflow.com/questions/967443/python-module-to-shellquote-unshellquote
try:
    from shlex import quote as shell_quote
except ImportError:
    from pipes import quote as shell_quote

def not_implemented():
    raise Exception('not implemented')

