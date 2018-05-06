#! /usr/bin/python
# -*- coding: utf-8 -*-

# Copyright © 2015,2016 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import subprocess
import pickle

import bytecode_main
from lang_spec import instructions
from util_main import *

def get_args():
    return pickle.loads(sys.argv[1])

# %% проверки повторения меток

class Var(object):
    count = 0
    prefix = 'var'
    def __init__(self, name = None):
        if name != None:
            self.name = name
        else:
            Var.count += 1
            self.name = self.prefix + str(Var.count)
    @staticmethod
    def setup(a, b):
        if a in ['le', 'be', '']:
            endiannes = a
            size = b
        elif b in ['le', 'be', '']:
            endiannes = b
            size = a
        else:
            die("can't find endiannes specification: {0} {1}", a, b)
        if endiannes == '' and size != 1:
            die('empty endiannes may be specified only with size 1, got {0}', size)
        # %% implement, or avoid the whole approach
        Code.append('var_setup {0} {1}'.format(size, endiannes))

class Label(object):
    def __init__(self, name):
        self.name = name

# операции идут в

class Code:
    code = []
    consts = {}
    limit = 10 ** 6
    @staticmethod
    def check():
        if len(Code.code) > Code.limit:
            # for l in Code.code[:10]:
            #     print ''.join(l)
            die('too many instructions, infinite loop in description? (or raise the limit in lang_main.py)')
    @staticmethod
    def append(string):
        # print string
        # Code.code += string + '\n'
        # Code.code.append(string)
        Code.code.append(string.split(' '))
        Code.check()
    @staticmethod
    def append_code(code):
        # Code.code += "".join(" ".join(l) + "\n" for l in code)
        # for l in code:
        #     print " ".join(l)
        # Code.code += map(" ".join, code)
        Code.code += code
        Code.check()

for name in instructions:
    return_type = instructions[name].return_type
    arguments = instructions[name].args
    def gen_func(return_type, name, arguments):
        # We need a closure. Python has closures to name tables. Hence
        # the additional level by 'gen_func'.
        def func(*args):
            # %% add checking of args
            # result var
            r = None
            if return_type != 'void':
                r = Var()
            third = None
            if name != 'new_const':
                # () may be used for the generators. But they make
                # tracebacks harder to read because evaluation is
                # postponed.
                # print >> sys.stderr, name, args
                a = [new_const1(v) for v in args]
                # print >> sys.stderr, a
                a = [v.name for v in a]
                third = " ".join(a)
            else:
                # Константы проваливаются, как есть. Для всего остального
                # есть имена.
                third = args[0]
            third = str(third)
            if name == 'print_verbatim' or name == 'new_bytes_const':
                # Для print_verbatim мы делаем всё в hex'е, ему можно
                # с пробелами передавать.
                third = third.encode('hex')
            if third != '':
                third = ' ' + third
            if return_type == 'void':
                Code.append('{0}{1}'.format(name, third))
            else:
                Code.append('{0} {1}{2}'.format(name, r.name, third))
            return r
        return func
    func = gen_func(return_type, name, arguments)
    if name.startswith('__'):
        exec('Var.{0} = func'.format(name))
    else:
        exec('{0} = func'.format(name))

new_const2 = new_const
def new_const1(c):
    if type(c) == int or type(c) == long:
        # if c not in Code.consts:
        #     # Если константа ещё не встречалась, именуем её и
        #     # запоминаем.
        #     Code.consts[c] = new_const2(c)
        # c = Code.consts[c]
        c = new_const2(c)
    elif isinstance(c, Var):
        # not 'type(c) == Var' because type(c) == <type 'instance'>
        # %% should not we break here?
        pass
    elif type(c) == str:
        # It is for 'labels'. They are wrapped into object with .name .
        c = Label(c)
    elif isinstance(c, Label):
        pass
    else:
        raise Exception('error 1: arg is not int or Var: {0} {1}'.format(type(c), c))
    return c
new_const = new_const1

# +=
# %% а присваивать тут не надо?!
Var.__iadd__ = lambda self, b: self + b

# The case: Python's const + our instance
Var.__radd__ = lambda self, b: self + b
Var.__rxor__ = lambda self, b: self ^ b
Var.__ror__ = lambda self, b: self ^ b

# Registers
# We emulate registers using variables.

# Decorator: wrap with use_define enabled
def wud(fun):
    def inner(self, *args, **kwargs):
        Code.append('use_define yes')
        # print >> sys.stderr, fun
        fun(self, *args, **kwargs)
        Code.append('use_define no')
        return self
    return inner

class Register(object):
    def __init__(self):
        self.var = new_var()
        in_register(self.var)
    @wud
    def input(self):
        i = input()
        self.var // i
    @wud
    def rol(self, num):
        self.var // rol(self.var, num)
    @wud
    def ror(self, num):
        self.var // ror(self.var, num)
    @wud
    def invert(self):
        self.var // ~self.var
    @wud
    def __ilshift__(self, num):
        self.var // (self.var << num)
    @wud
    def __irshift__(self, num):
        self.var // (self.var >> num)
    @wud
    def output(self):
        output(self.var)
    @wud
    def swap_to_be(self):
        self.var // swap_to_be(self.var)
    @wud
    def __floordiv__(self, a):
        if type(a) == int:
            self.var // a
        else:
            # %% надо проверять, что аргумент - регистр
            self.var // a.var
    # %% avoid copy-pasting
    @wud
    def __iadd__(self, a):
        if type(a) != int:
            a = a.var
        self.var // (self.var + a)
    @wud
    def __ixor__(self, a):
        if type(a) != int:
            a = a.var
        self.var // (self.var ^ a)
    @wud
    def __iand__(self, a):
        if type(a) != int:
            a = a.var
        self.var // (self.var & a)
    @wud
    def __ior__(self, a):
        if type(a) != int:
            a = a.var
        self.var // (self.var | a)
    @wud
    def load_from(self, var):
        self.var // load(var)
    @wud
    def store_to(self, var):
        store(var, self.var)

def new_register():
    return Register()

def new_memory():
    v = new_var()
    in_memory(v)
    return v

# # Algo manipulations

# def algo_load(name, args = {}):
#     return B.get_code_full(name, False, False, args)

# def algo_get_block_int_count(code):
#     k = 0
#     for l in code:
#         if l[0] == 'input':
#             k += 1
#     return k

# # %% cache results?
# def algo_get_initial_state(code):
#     state = []
#     for l in code:
#         if l[0] == 'new_state_var':
#             state.append(l[2])
#     # Определения констант вынесены в отдельные инструкции
#     for l in code:
#         # %% use hash
#         if l[0] == 'new_const' and l[1] in state:
#             Code.append_code([l])
#     return state

# def algo_insert(code, *args):
#     block_count = algo_get_block_int_count(code)
#     block = args[0:block_count]
#     state = args[block_count:]
#     # %% тут надо будет не вставлять инициализацию состояния
#     # итак, вставка кода: у нас есть инструкции кода, список
#     # переменных блока, список переменных состояния, а вернуть мы
#     # должны список переменных-выходов
#     #
#     # составляем таблицы замен входов и состояний, а так же список выходов
#     outputs = []
#     substs = {}
#     b = list(block)
#     s = list(state)
#     for l in code:
#         if l[0] == 'new_state_var':
#             substs[l[1]] = s.pop(0)
#             l[0] = B.drop
#         if l[0] == 'input':
#             substs[l[1]] = b.pop(0)
#             l[0] = B.drop
#         if l[0] == 'output':
#             outputs.append(l[1])
#             l[0] = B.drop
#     code = B.clean(code)
#     # заменяем имена в коде
#     # %% надо бы делать глубокую копию
#     for l in code:
#         for i in range(1, len(l)):
#             if l[i] in substs:
#                 # %% We don't accept bear constants here.
#                 l[i] = substs[l[i]].name
#     # добавляем код в общий
#     Code.append_code(code)
#     return outputs


# Modules/functions

class Module(Var):
    def __init__(self, code, fun_type, name):
        super(Module, self).__init__()
        self.code = code
        # self.interface = B.get_interface(code)
        # %% надо проверять, что name не содержит пробелы
        Code.append('module_begin {0} {1} {2}'.format(self.name, fun_type, name))
        Code.append_code(self.code)
        Code.append('module_end ' + self.name)
    # def __call__(self, *values):
    #     v = Var()
    #     Code.append('invoke_function {0} {1} {2}'.format(v.name, self.name, ' '.join(values)))

def load_plain(name, args = {}):
    # %% use get_code(), don't split bytecode
    return Module(bytecode_main.get_code_full(name, args), 'plain', name)

def load_hfun(name, args = {}):
    return Module(bytecode_main.get_hfun_code(name, args), 'hfun', name)

def load_fun2(name, args = {}):
    return Module(bytecode_main.get_code_full(name, args), 'fun2', name)


from lang_tools import *

def include(name):
    execfile(get_dk_path('algo_include_' + name + '.py'), globals())

# Import the library
exec(slurp_dk_file('algo_lib.py'))

def print_code():
    print bytecode_main.output_delimiter
    print >> sys.stderr, 'lang_main() code len:', len(Code.code)
    # %% enable the check
    # for l in Code.code:
    #     if len(l) < 2 or l[1] == ' ':
    #         if len(l) < 2:
    #             print >> sys.stderr, 'short line:', l
    #         die('single letter op, it means there is a bug somewhere')
    # Enable buffering back.
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 2**21)
    # print Code.code
    for l in Code.code:
        # We replace '-' with _, but we don't want to replace it
        # before constants.
        # # ** Arguments (including labels) should not start with _.
        # l = l.replace('-', '_').replace(' _', ' -')
        # print l
        print ' '.join(l)

# # context manager to collect code
# class evaluate_to(object):
#     # %% support for args var?
#     def __init__(self, list_for_output):
#         self.lst = list_for_output
#     def __enter__(self):
#         self.old_code = Code.code
#         self.old_consts = Code.consts
#         # %% тут можно было бы собрать константы по заданному коду
#         Code.consts = {}
#         Code.code = self.lst
#     def __exit__(self):
#         Code.code = self.old_code
#         Code.consts = self.old_consts

import contextlib
@contextlib.contextmanager
def evaluate_to(list_for_output):
    # %% надо что-то сделать и с нумерацией переменных; а может, и
    #  % нет, ведь нумерация не сбрасывается
    old_code = Code.code
    old_consts = Code.consts
    # old_var_prefix = Var.prefix
    Code.consts = {}
    Code.code = list_for_output
    # Var.prefix = prefix
    try:
        yield
    finally:
        Code.code = old_code
        Code.consts = old_consts
        # Var.prefix = old_var_prefix

if __name__ == "__main__":
    import atexit
    atexit.register(print_code)
    # to be used in algo_*.py
    args = get_args()
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    code = sys.stdin.read()
    # print >> sys.stderr, ">>>>", code, "<<<<"
    exec(code)
else:
    Var.prefix = 'lib'
