#! /usr/bin/python
# -*- coding: utf-8 -*-

import sys
import subprocess

Code = []
Steps = {}

# %% Per var endianness and size

class Var(object):
    endianness = 'not set'
    size = 0
    count = 0
    @staticmethod
    def setup(e, s):
        if e not in ['le', 'be']:
            raise ValueError('endianness should be either "le" or "be"')
        Var.endianness = e
        Var.size = s
    def __init__(self, arg1 = None, op = None, arg2 = None):
        self.name = "var" + str(Var.count)
        Var.count += 1
        if arg1:
            if op != "getitem":
                arg1 = to_const_maybe(arg1)
                arg2 = to_const_maybe(arg2)
            Code.append("op {0} {1} {3} {2}".format(self.name, arg1.name, op, arg2.name))
        else:
            Code.append("op {0} None None noop".format(self.name))
    def __str__(self):
        return self.name
    # Binary
    def __add__(self, b):
        return Var(self, "+", b)
    def __sub__(self, b):
        return Var(self, "-", b)
    def __mul__(self, b):
        return Var(self, "*", b)
    def __xor__(self, b):
        return Var(self, "^", b)
    def __rshift__(self, b):
        return Var(self, ">>", b)
    def __and__(self, b):
        return Var(self, "&", b)
    def __or__(self, b):
        return Var(self, "|", b)
    def __floordiv__(self, b):
        # Means assignment, a // b is equal to a = b; in C
        # %% Bad priority: a // (b + c) is for a = b + c, not nice
        # %% raise error on assignment to const
        # %% user has to create a variable before assignment
        Code.append("assign {0} {1}".format(self, b))
        return self
    # Unary
    def __invert__(self):
        return Var(self, "~", D)
    # With assignment, like +=
    def __iadd__(self, b):
        # %% а присваивать тут не надо?!
        return self + b

class Dummy(Var):
    def __init__(self):
        pass
D = Dummy()
D.name = "None"

class Const(Var):
    count = 0
    def __init__(self, c):
        if c == None:
            self.name = "None"
        else:
            self.name = "const" + str(Const.count)
            Code.append("const {0} {1} {2} {3}".format(self.name, c, Var.endianness, Var.size))
            self.value = c
            Const.count += 1

def to_const_maybe(a):
    if not isinstance(a, Var):
        a = Const(a)
    return a

# rotate right
def ror(a, b):
    return Var(a, "ror", b)

# rotate left
def rol(a, b):
    return Var(a, "rol", b)

# to big endian
def to_be(v):
    return Var(v, "to_be")

class input(Var):
    count = 0
    def __init__(self):
        self.name = "input" + str(input.count)
        Code.append("declare {0} {1} {2}".format(self.name, Var.endianness, Var.size))
        input.count += 1

# byte string, no endianness, no size
class input_string(Var):
    count = 0
    def __init__(self):
        self.name = "input_string" + str(input_string.count)
        Code.append("declare_string {0}".format(self.name))
        input_string.count += 1
    def get_ints_with_bit_on_the_end(self, number):
        vs = [Var() for i in range(number)]
        # %% update instruction to be like in bitslice
        # ** string_get_ints implies endianness conversion.
        Code.append("string_get_ints {0} {1} {2} {3} {4}".format(self.name, Var.endianness, Var.size, number, " ".join(str(v) for v in vs)))
        return vs
    def get_bit_length(self):
        return Var(self, 'bit_length')

class state(Var):
    count = 0
    def __init__(self, default):
        self.name = "state" + str(state.count)
        Code.append("declare {0} {1} {2} {3}".format(self.name, default, Var.endianness, Var.size))
        state.count += 1

def output(a):
    Code.append("output " + a.name)

def my_const_array(name, arr):
    return MyArray(name, [Const(v) for v in arr])

class MyArray(object):
    # %% make arrays writable
    def __init__(self, name, arr):
        self.name = "array_" + name
        Code.append("array {0} {1}".format(self.name, " ".join(str(v) for v in arr)))
    def __getitem__(self, i):
        # %% regular num index
        if not isinstance(i, CycleVar):
            raise ValueError("index is not cycle var")
        return Var(self, "getitem", i)

class CycleVar(object):
    # %% CycleVar is limited to cycle_const_range
    count = 0
    def __init__(self, cycle_name, min, max, step):
        self.name = "cyclevar" + str(CycleVar.count)
        Code.append("cycle_const_range {0} {1} {2} {3} {4}".format(self.name, cycle_name, min, max, step))
        CycleVar.count += 1

def cycle_const_range(name, min, max, step):
    # min and max are inclusive (unlike in python's range)
    return CycleVar(name, min, max, step)

def cycle_end(name):
    # %% check parity
    Code.append("cycle_end " + name)

def comment(text, *args):
    # %% check for new lines
    Code.append("comment " + text.format(*args))

code = sys.stdin.read()
exec(code)
for i in Code:
    print i
