#! /usr/bin/python
# -*- coding: utf-8 -*-

import sys
import subprocess

import bytecode_main as B
from lang_spec import instructions

from lang_common import args

# %% проверки повторения меток

class Var():
    count = 0
    def __init__(self):
        Var.count += 1
        self.name = 'var' + str(Var.count)
    @staticmethod
    def setup(e, s):
        # %% implement, or avoid the whole approach
        pass

class Label():
    def __init__(self, name):
        self.name = name

# операции идут в

class Code:
    code = ''
    consts = {}
    @staticmethod
    def append(string):
        Code.code += string + '\n'
    @staticmethod
    def append_code(code):
        Code.code += "".join(" ".join(l) + "\n" for l in code)

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
                # print >> sys.stderr, args
                a = [new_const1(v) for v in args]
                # print >> sys.stderr, a
                a = [v.name for v in a]
                third = " ".join(a)
            else:
                # Константы проваливаются, как есть. Для всего остального
                # есть имена.
                third = args[0]
            third = str(third)
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
        if c not in Code.consts:
            # Если константа ещё не встречалась, именуем её и
            # запоминаем.
            Code.consts[c] = new_const2(c)
        c = Code.consts[c]
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

# Algo manipulations

def algo_load(name, args = {}):
    return B.get_code_full(name, False, False, args)

def algo_get_block_int_count(code):
    k = 0
    for l in code:
        if l[0] == 'input':
            k += 1
    return k

# %% cache results?
def algo_get_initial_state(code):
    state = []
    for l in code:
        if l[0] == 'new_state_var':
            state.append(l[2])
    # Определения констант вынесены в отдельные инструкции
    for l in code:
        # %% use hash
        if l[0] == 'new_const' and l[1] in state:
            Code.append_code([l])
    return state

def algo_insert(code, *args):
    block_count = algo_get_block_int_count(code)
    block = args[0:block_count]
    state = args[block_count:]
    # %% тут надо будет не вставлять инициализацию состояния
    # итак, вставка кода: у нас есть инструкции кода, список
    # переменных блока, список переменных состояния, а вернуть мы
    # должны список переменных-выходов
    #
    # составляем таблицы замен входов и состояний, а так же список выходов
    outputs = []
    substs = {}
    b = list(block)
    s = list(state)
    for l in code:
        if l[0] == 'new_state_var':
            substs[l[1]] = s.pop(0)
            l[0] = B.drop
        if l[0] == 'input':
            substs[l[1]] = b.pop(0)
            l[0] = B.drop
        if l[0] == 'output':
            outputs.append(l[1])
            l[0] = B.drop
    code = B.clean(code)
    # заменяем имена в коде
    # %% надо бы делать глубокую копию
    for l in code:
        for i in range(1, len(l)):
            if l[i] in substs:
                # %% We don't accept bear constants here.
                l[i] = substs[l[i]].name
    # добавляем код в общий
    Code.append_code(code)
    return outputs

if __name__ == "__main__":
    code = sys.stdin.read()
    # print >> sys.stderr, ">>>>", code, "<<<<"
    exec(code)
    print Code.code
