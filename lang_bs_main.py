#! /use/bin/python
# -*- coding: utf-8 -*-

# def большими буквами содержит описание инструкции байткода

import sys
import subprocess

Code = []
Steps = {}

# %% Per var endianness and size

class Var(object):
    endianness = 'not set'
    size = 0
    bits = 0
    count = 0
    @staticmethod
    def new_name():
        n = "var" + str(Var.count)
        Var.count += 1
        return n
    @staticmethod
    def setup(e, s):
        if e not in ['le', 'be']:
            raise ValueError('endianness should be either "le" or "be"')
        Var.endianness = e
        Var.size = s
        Var.bits = s * 8
    def __init__(self, arg1=None, op=None, arg2=None, init=True):
        self.names = []
        if init:
            for i in range(Var.bits):
                self.names.append(Var.new_name())
            for i in range(Var.bits):
                if arg1:
                    if op == 'getitem':
                        # %% specific for bitslice, update regular version
                        # to support that op
                        # DEF getitem: target_name array_name index_name bit_index
                        Code.append("getitem {0} {1} {2} {3}".format(self.names[i], arg1.name, arg2.name, i))
                    elif op == 'bit_length':
                        # %% specific for bitslice, update regular version
                        # to support that op
                        # DEF bit_length: target_name string_name bit_index
                        Code.append("bit_length {0} {1} {2}".format(self.names[i], arg1.name, i))
                    else:
                        # DEF op: target_name arg1_name arg2_name op
                        # DEF op: target_name 'None' 'None' 'noop'
                        Code.append("op {0} {1} {3} {2}".format(self.names[i], arg1.names[i], op, arg2.names[i]))
                else:
                    Code.append("op {0} None None noop".format(self.names[i]))
    def __str__(self):
        # return "[" + (",".join(str(v) for v in self.names)) + "]"
        return " ".join(str(v) for v in self.names)

    # Binary

    # Simple
    def __xor__(self, b):
        return Var(self, "^", b)
    def __and__(self, b):
        return Var(self, "&", b)
    def __or__(self, b):
        return Var(self, "|", b)
    # Unary
    def __invert__(self):
        return Var(self, "~", Dummy())

    def __rshift__(self, b):
        # часть сдвигаем, а часть забиваем нулями (константами)
        # %% работает только с константами, иначе надо сделать
        # операцию на другом уровне с возможным вычислением там
        # (скажем, переменная цикла при развороте становится
        # константой)

        # у нас структура как Var, но без новых переменных в байткоде
        v = Var(init = False)
        # слева (вначале списка имён) идут старшие биты
        # %% не уверен насчёт порядка битов
        v.names = self.names[0:(Var.bits - b)]
        for i in range(b):
            v.names.insert(0, BitConst.zero)
        return v

    def __add__(self, b):
        # уникальный префикс
        # %% вынести op?
        op = lambda *args: Code.append('op {0} {1} {3} {2}'.format(*args))
        a = self.names
        b = b.names
        # создаём все имена впрок
        # (возможно, есть лишние, это не страшно)
        r, n, x, q, w = [[Var.new_name() for j in range(i)]
                         for i in [Var.bits] * 5]
        # r - result bit
        # n - carry bit
        for i in reversed(range(Var.bits)):
            if i == Var.bits - 1:
                op(r[i], a[i], '^', b[i])
                op(n[i], a[i], '&', b[i])
            else:
                op(x[i], a[i], '^', b[i])
                op(r[i], x[i], '^', n[i + 1])
                # %% Better circuit here.
                # n[i] = b[i] ^ (x[i] & (b[i] ^ n[i + 1]))
                op(w[i], b[i], '^', n[i + 1])
                op(q[i], x[i], '&', w[i])
                op(n[i], b[i], '^', q[i])
        v = Var(init = False)
        v.names = r
        return v

    # def __sub__(self, b):
    #     return Var(self, "-", b)

    # def __mul__(self, b):
    #     return Var(self, "*", b)

    def __floordiv__(self, b):
        # Means assignment, a // b is equal to a = b; in C
        # %% Bad priority: a // (b + c) is for a = b + c, not nice
        # %% raise error on assignment to const
        # %% user has to create a variable before assignment
        for i in range(Var.bits):
            # DEF assign: target_name source_name
            Code.append("assign {0} {1}".format(self.names[i], b.names[i]))
        return self

    # With assignment, like +=
    def __iadd__(self, b):
        # %% а присваивать тут не надо?!
        # без присваивания тут a += b работает, как a = a + b, а не
        # a // (a + b), это разные вещи, надо об этом помнить; то есть
        # += не подходит для использования в циклах
        # %% если делать как a = a + b, то надо ли это вообще определять?
        return self + b

class Dummy(Var):
    def __init__(self):
        self.names = ["None"] * Var.bits

class BitConst(Var):
    count = 0
    def __init__(self, c):
        if c == None:
            self.name = "None"
        else:
            self.name = "const" + str(BitConst.count)
            # DEF %%
            Code.append("const {0} {1} {2} {3}".format(self.name, c, Var.endianness, Var.size))
            self.value = c
            BitConst.count += 1
    def __str__(self):
        return self.name
all_zero = 0
all_one = ~all_zero
BitConst.zero = BitConst(all_zero)
BitConst.one = BitConst(all_one)

# print >> sys.stderr, ">>", all_one, all_zero

class Const(Var):
    # %% надо реализовать через BitConst
    def __init__(self, c):
        # собственно, констант у нас две: 0 и 1, так что все остальные
        # просто собираются из них
        self.names = []
        for i in range(Var.bits):
            self.names.insert(0, BitConst.one if c & (1 << i) else BitConst.zero)

def to_const_maybe(a):
    if not isinstance(a, Var):
        a = Const(a)
    return a

# rotate right
def ror(a, b):
    v = Var(init = False)
    v.names = a.names[(Var.bits - b):Var.bits] + a.names[0:(Var.bits - b)]
    return v

# rotate left
def rol(a, b):
    v = Var(init = False)
    v.names = a.names[b:Var.bits] + a.names[0:b]
    return v

# to big endian
def to_be(v):
    # %% проверка, что у нас литтл эндиан
    n = Var(init = False)
    n.names = list(reversed(v.names))
    return n

class input(Var):
    count = 0
    def __init__(self):
        self.names = []
        for i in range(Var.bits):
            n = "input" + str(input.count)
            # DEF %%
            Code.append("declare {0} {1} {2}".format(n, Var.endianness, Var.size))
            input.count += 1
            self.names.append(n)

# byte string, no endianness, no size
class input_string(Var):
    count = 0
    def __init__(self):
        self.name = "input_string" + str(input_string.count)
        # # %% это может скрывать ошибки и усложнять отладку
        # self.names = [self.name] * Var.bits
        # DEF %%
        Code.append("declare_string {0}".format(self.name))
        input_string.count += 1
    # def get_ints(self, number):
    #     vs = [Var() for i in range(number)]
    #     # ** string_get_ints implies endianness conversion.
    #     # %% тут надо подумать, если читаем мы не в инты, а сразу на
    #     # биты режем
    #     Code.append("string_get_ints {0} {1} {2} {3} {4}".format(self.name, Var.endianness, Var.size, number, " ".join(str(v) for v in vs)))
    #     return vs
    def get_ints_with_bit_on_the_end(self, number):
        vs = [Var() for i in range(number)]
        # ** string_get_ints implies endianness conversion.
        # %% тут надо подумать, если читаем мы не в инты, а сразу на
        # биты режем
        # DEF %%
        Code.append("string_get_ints_with_bit_on_the_end {0} {1} {2} {3} {4}".format(self.name, Var.endianness, Var.size, number, " ".join(str(v) for v in vs)))
        return vs
    def get_bit_length(self):
        return Var(self, 'bit_length')

class state(Var):
    count = 0
    def __init__(self, default):
        self.names = []
        for i in range(Var.bits):
            n = "state" + str(state.count)
            # DEF %%
            # %% надо бы сделать функции для каждой инструкции
            Code.append("declare {0} {1} {2} {3}".format(n, all_one if default & (1 << i) else all_zero, Var.endianness, Var.size))
            state.count += 1
            self.names.insert(0, n)

def output(a):
    for i in range(Var.bits):
        # DEF %%
        Code.append("output " + str(a.names[i]))

def my_const_array(name, arr):
    return MyArray(name, [Const(v) for v in arr])

class MyArray(object):
    # %% make arrays writable
    def __init__(self, name, arr):
        self.name = "array_" + name
        # DEF %%
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
        # DEF %%
        Code.append("cycle_const_range {0} {1} {2} {3} {4}".format(self.name, cycle_name, min, max, step))
        CycleVar.count += 1

def cycle_const_range(name, min, max, step):
    # min and max are inclusive (unlike in python's range)
    return CycleVar(name, min, max, step)

def cycle_end(name):
    # %% check parity
    # DEF %%
    Code.append("cycle_end " + name)

def comment(text, *args):
    # %% check for new lines
    # DEF %%
    Code.append("comment " + text.format(*args))

code = sys.stdin.read()
exec(code)
for i in Code:
    print i
