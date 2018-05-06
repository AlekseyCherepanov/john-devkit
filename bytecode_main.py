# -*- coding: utf-8 -*-
# библиотека для работы с "байткодом"

# Copyright © 2015,2016 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

# %% clean imports
import pickle
import glob
from copy import deepcopy
import hashlib

import lang_main as L

# import random
# # RNG = random.SystemRandom()

from util_main import *

from bytecode_util import *

global_vars = {}

output_delimiter = "END OF DEBUG OUTPUT"

def get_code(name, args={}, temp_file=None):
    # %% needs a patched trace.py that outputs to stderr, may bypass
    # it prefixing bytecode lines to distinguish them from tracer's
    # output
    # %% capture output of tracer
    args_str = shell_quote(pickle.dumps(args))
    decor = ("#" * 15) + " {0} " + ("#" * 15)
    # %% tracer is not exposed as option.
    use_tracer = False
    if use_tracer:
        tracer_options = '-m trace --ignore-dir=/usr -t'
    else:
        tracer_options = ''
    print >> sys.stderr, decor.format('BEGIN OF {0}'.format(name))
    # %% remove temporary file and `cat`, or make as an option for debug
    file_name = get_dk_path("algo_{0}.py".format(name))
    if temp_file != None:
        file_name = temp_file
    lang_main = get_dk_path('lang_main.py')
    # %% quoting?
    # %% option to choose between pypy and regular python
    # pipe = os.popen('pypy {1} {4} < {3} {2} > {0}.bytecode && cat {0}.bytecode'.format(name, tracer_options, args_str, file_name, lang_main))
    pipe = os.popen('pypy {1} {4} < {3} {2}'.format(name, tracer_options, args_str, file_name, lang_main))
    debug = True
    output = ''
    for l in pipe:
        l = l.rstrip('\n')
        # print '--', debug, l
        if l == output_delimiter:
            debug = False
        elif debug:
            print '>', l
        else:
            output += l + '\n'
    # output = pipe.read()
    print >> sys.stderr, decor.format('  END OF {0}'.format(name))
    c = pipe.close()
    if c and c > 0:
        # print >> sys.stderr, "hi there << {0}".format(c)
        # ** c may be 256
        exit(1)
    return output

def evaluate(code_str):
    with open('temp.dkpy', 'w') as f:
        f.write(code_str)
    r_str = get_code('temp', {}, 'temp.dkpy')
    code = split_bytecode(r_str)
    return code

# %% rename it into get_code() ?
def get_code_full(name, args={}):
    temp = get_code(name, args)
    temp = split_bytecode(temp)
    add_prefix(temp, name)
    return temp

def get_hfun_code(name, args={}):
    temp = get_code_full('hfun_' + name, args)
    return temp

# режем код на части
def split_bytecode(c):
    # %% use c.splitlines() instead of c.split('\n') ?
    return [l.split(' ') for l in c.split('\n') if l != '']

def print_bytecode(c):
    print "\n".join(" ".join(l) for l in c)

# def slurp_bytecode(fname):
#     return split_bytecode(slurp_file(fname))

# def slurp_bytecode(fname):
#     r = []
#     with open(fname, 'r') as f:
#         for line in f:
#             r.append(line.rstrip('\n').split(' '))
#     return r

# import fileinput
# def slurp_bytecode(fname):
#     r = []
#     for line in fileinput.input([fname]):
#         r.append(line.rstrip('\n').split(' '))
#     return r

def slurp_bytecode(fname):
    with open(fname, 'r') as f:
        return [l.rstrip('\n').split(' ') for l in f if l != '']

# мы можем сливать, заменяя или давая новые определения;
# при слиянии у нас будут конфликты имён, хорошо бы к именам добавлять
# префиксы
# %% автоматом давать префиксы при загрузке байткода?
def add_prefix(c, prefix):
    # Заменяем "-" на "_" в префиксе, чтобы не было проблем с си
    prefix = prefix.replace('-', "_")
    # %% сделать так: заносить в хеш имена от операций, описывающих переменные
    # положимся на то, что все имена имеют форму
    # var\d+
    # однако, если мы добавляем префикс, то сначала может быть
    # префикс
    #
    # мне нужна замена на месте
    for l in c:
        for i in range(len(l)):
            if re.match('(var)\d+$', l[i]):
                l[i] = prefix + "_" + l[i]

# %% предполагаем, что нет конфликтов имён
# может менять параметры
# %% drop line - неплохое имя, так как разбивка по пробелам
# делает такое имя не доступным в обычных условиях
# %% хорошо бы найти более приличный способ удалять строки удобно
drop = '>>>>>   drop line <<<<<<<<           '
def clean(code):
    return [l for l in code if l[0] != drop]

def join_parts(a, b):
    # заменяем именами выходов входы во втором коде
    names = {}
    names_a = []
    for l in a:
        if l[0] == 'output':
            names_a.append(l[1])
            l[0] = drop
    for l in b:
        # %% таким образом мы не склеиваем, когда во втором принимает
        # строку
        # %% таким образом мы не прицепляем выходы к состояниям,
        # требуется конфигурация этого
        if l[0] == 'input':
            names[l[1]] = names_a.pop(0)
            l[0] = drop
        for i in range(len(l)):
            if l[i] in names:
                l[i] = names[l[i]]
        a.append(l)
    # %% проверка, что все имена использованы
    return clean(a)

def dump_with_file_object(code, f):
    for l in code:
        # Мы всё приводим к строкам
        # %% хорошо бы проверять, что мы получили строку или число
        f.write(" ".join(l))
        f.write("\n")

def dump(code, filename = None):
    if filename == None:
        print '  Dump to stdout:'
        print
        dump_with_file_object(code, sys.stdout)
        print
        print '  End of dump'
        return code
    with file(filename, 'w') as f:
        dump_with_file_object(code, f)
    return code


vectorizable = '''
new_const
new_var
new_state_var
new_array
#input_rounds
#input_key
#input_salt
output
input
check_output

__add__
__sub__
__xor__
__mul__
__rshift__
__lshift__
__and__
__or__
__floordiv__
__invert__
__getitem__
__mod__

# __le__
# __lt__
# __ge__
# __gt__
# __eq__
# __ne__

ror
rol

# cycle_const_range
# cycle_range
# cycle_while_begin
# cycle_while
# cycle_end

# label
# goto

# if_condition
# if_else
# if_end

set_item
make_array

print_var

swap_to_be

permute
new_array
sbox

load
store

'''

to_vector = {}

v = vectorizable.split('\n')
v = [i for i in v if not i.startswith('#') and i != '']
for i in v:
    n = 'v_' + i
    to_vector[i] = n
    # %% move that to lang_spec.py?
    instructions[n] = instructions[i]

def collect_tree(code):
    # функция для сбора дерева определений: словарь имя переменной ->
    # строка определения; переменная может оказаться в левом положении
    # несколько раз, если мы в неё присваивали
    r = {}
    for l in code:
        if l[1] in r:
            r[l[1]].append(l)
        else:
            r[l[1]] = [l]
    return r

# функция, вычисляющая константные выражения
def compute_const_expressions(code, size):
    bits = size * 8
    consts = {}
    for l in code:
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
    # %% вообще, это можно было бы делать в один проход
    new_code = []
    def run_op_on_consts(op_fun, *args):
        return str(op_fun(*[int(consts[a]) for a in args]))
    max_int = 2 ** bits
    mask_int = max_int - 1
    def d_rol(a, b):
        print >> sys.stderr, 'rol:', a, b
        return (a >> b) | ((a << (bits - b)) & mask_int)
    ops = {
        # %% wrap negative?
        '__sub__': lambda a, b: a - b,
        '__and__': lambda a, b: a & b,
        '__xor__': lambda a, b: a ^ b,
        '__invert__': lambda a: mask_int ^ a,
        'ror': lambda a, b: (a >> b) | ((a << (bits - b)) & mask_int),
        'rol': lambda a, b: ((a << b) & mask_int) | (a >> (bits - b)),
        # 'rol': d_rol,
        '__add__': lambda a, b: (a + b) & mask_int,
        '__rshift__': lambda a, b: (a >> b)
    }
    for l in code:
        if instructions[l[0]].return_type != 'void' and ((len(instructions[l[0]].args) == 2 and l[2] in consts and l[3] in consts) or (len(instructions[l[0]].args) == 1 and l[2] in consts)):
            if l[0] in ops:
                # print >> sys.stderr, l
                # print >> sys.stderr, [consts[a] for a in l[2:]]
                # print >> sys.stderr, size
                l[2] = run_op_on_consts(ops[l[0]], *l[2:])
                if len(instructions[l[0]].args) == 2:
                    del l[3]
                l[0] = 'new_const'
                new_code.append(l)
                consts[l[1]] = l[2]
            else:
                print >> sys.stderr, "Warning: consts with op: ", l[0]
                new_code.append(l)
        else:
            new_code.append(l)
    return new_code

def vectorize(code):
    # не все константы надо векторизовывать, размеры битовых
    # сдвигов/ротейтов не надо
    # %% надо бы проверять, что константы не используются в разных
    #  % местах и разделять на векторную и скалярную
    no_vec = {}
    array_vars = {}
    for l in code:
        if l[0] == 'cycle_const_range':
            array_vars[l[1]] = 1
        if l[0] in ['ror', 'rol', '__rshift__', '__lshift__', '__getitem__', 'make_array']:# or (l[0].startswith('cycle_') and l[0] != 'cycle_end'):
            no_vec[l[3]] = 1
        if l[0] in ['set_item']:
            no_vec[l[2]] = 1
        if l[0] == '__sub__' and l[2] in array_vars:
            # %% очередной костыль...
            # %% эта проверка копируется для самой операции вычитания
            # %% любой аргумент, а не только левый
            # Проверяем, что левый аргумент является переменной цикла.
            # Тогда не векторизуем константу, которая вычитается.
            no_vec[l[3]] = 1
        if l[0] not in to_vector:
            for i in l[1:]:
                no_vec[i] = 1
    # print >>sys.stderr, no_vec
    for l in code:
        if l[0] in to_vector and not (
                l[0] == 'new_const' and l[1] in no_vec) and not (
                    l[0] == '__sub__' and l[2] in array_vars):
            l[0] = to_vector[l[0]]
    # заменяем ~a & b на andnot(a, b)
    t = collect_tree(code)
    for l in code:
        # если текущая операция and, то проверяем аргументы, если один
        # из них not, то заменяем на andnot; мы уже векторизовали
        # операции, так что смотрим на векторные
        if l[0] == 'v___and__':
            # %% handle multi op case; вероятно надо брать
            #  % последнюю операцию перед текущей
            a = t[l[2]][0]
            b = t[l[3]][0]
            n = None
            if a[0] == 'v___invert__':
                l[0] = 'v_andnot'
                l[2] = a[2]
                n = a
            elif b[0] == 'v___invert__':
                # если левый аргумент не имеет not, то мы ставим
                # второй аргумент на левое место
                l[0] = 'v_andnot'
                l[3] = l[2]
                l[2] = b[2]
                n = b
            # %% у нас подвисла операция not
            # если операция not больше никем не используется, то её
            # можно удалить; собственно, могу сделать обрезание
            # неиспользуемых переменных
            # %% надо сделать такую проверку
            # if n:
            #     n[0] = drop
    code = clean(code)
    return code

def unroll_cycle_const_range_partly(code, label, unroll_size):
    # %% copy-pasted... extract common part with unroll_cycle_const_range
    # %% можно исключить присваивание; пока что это делается отдельным проходом
    # %% частичный анрол
    # Размножаем тело, подставляя переменную цикла.
    # %% вычислять константные выражения
    # находим тело
    begin = None
    end = None
    for i in range(len(code)):
        if code[i][0] == 'cycle_const_range' and code[i][2] == label:
            # %% check that there is only 1 such cycle.
            begin = i
        if code[i][0] == 'cycle_end' and code[i][1] == label:
            end = i
    pre = code[: begin]
    body = code[begin : end]
    post = code[end :]
    # We use cycle's label as label for begin of the cycle and as a
    # base for label on the end of the cycle.
    pre.append(['label', body[0][2]])
    post.insert(0, ['label', body[0][2] + '_end'])
    new_body = []
    # %% вычисление выражений для нахождения границ цикла
    # Собираем константы
    consts = {}
    for l in code:
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
    # Имя переменной цикла
    name = body[0][1]
    # %% проверка, что количество итераций кратно новому шагу
    # Изменяем шаг цикла
    # %% тут вообще-то надо константу делать, а не записывать её
    #  % напрямую в инструкцию
    nn = new_name()
    new_body.append(['new_const', nn, str(int(consts[body[0][5]]) * unroll_size)])
    body[0][5] = nn
    new_body.append(body[0])
    # Конструируем новое тело.
    # Выполняем проходим по циклу заданное количество раз
    for i in range(unroll_size):
        # Вставляем код для константы
        const_def = new_const(i)
        n_name = const_def[1]
        new_body.append(const_def)
        # Добавляем константу к переменной цикла
        t = new_name()
        new_body.append(['__add__', t, name, n_name])
        # Суммой будем заменять переменную цикла
        n_name = t
        rs = {}
        for l in body[1:]:
            # print >>sys.stderr, '>>', l
            n = list(l)
            # Заменяем все целевые имена, кроме левой стороны
            # присваивания, на новые. Так же заменяем их
            # использования.
            if not n[0].endswith('__floordiv__') and instructions[n[0]].return_type != 'void':
                t = new_name()
                rs[n[1]] = t
                # n[1] = t
            for j in range(len(n)):
                # Заменяем имя переменной цикла на имя константы с
                # текущим значением.
                if n[j] == name:
                    n[j] = n_name
                # Заменяем использования переменных, определённых в теле.
                if n[j] in rs:
                    n[j] = rs[n[j]]
            new_body.append(n)
            # print >>sys.stderr, ' <', new_body[-1]
    # собираем результат
    # %% хорошо бы отметить функции, которые возвращают новый code
    return pre + new_body + post

def unroll_cycle_const_range(code, label):
    # %% можно исключить присваивание; пока что это делается отдельным проходом
    # %% частичный анрол
    # Размножаем тело, подставляя переменную цикла.
    # %% вычислять константные выражения
    # находим тело
    begin = None
    end = None
    for i in range(len(code)):
        if code[i][0] == 'cycle_const_range' and code[i][2] == label:
            # %% check that there is only 1 such cycle.
            begin = i
        if code[i][0] == 'cycle_end' and code[i][1] == label:
            end = i
    pre = code[: begin]
    # we don't include cycle_end into the body
    body = code[begin : end]
    post = code[end + 1 :]
    # We use cycle's label as label for begin of the cycle and as a
    # base for label on the end of the cycle.
    pre.append(['label', body[0][2]])
    post.insert(0, ['label', body[0][2] + '_end'])
    new_body = []
    # %% вычисление выражений для нахождения границ цикла
    # Собираем константы
    consts = {}
    for l in code:
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
    # Имя переменной цикла
    name = body[0][1]
    # Конструируем новое тело.
    # Выполняем проход цикла.
    for i in range(int(consts[body[0][3]]),
                   int(consts[body[0][4]]) + 1,
                   int(consts[body[0][5]])):
        const_def = new_const(i)
        n_name = const_def[1]
        new_body.append(const_def)
        rs = {}
        for l in body[1:]:
            # print >>sys.stderr, '>>', l
            n = list(l)
            # Заменяем все целевые имена, кроме левой стороны
            # присваивания, на новые. Так же заменяем их
            # использования.
            if not n[0].endswith('__floordiv__') and instructions[n[0]].return_type != 'void':
                t = new_name()
                rs[n[1]] = t
                # n[1] = t
            for j in range(len(n)):
                # Заменяем имя переменной цикла на имя константы с
                # текущим значением.
                if n[j] == name:
                    n[j] = n_name
                # Заменяем использования переменных, определённых в теле.
                if n[j] in rs:
                    n[j] = rs[n[j]]
            new_body.append(n)
            # print >>sys.stderr, ' <', new_body[-1]
    # собираем результат
    # %% хорошо бы отметить функции, которые возвращают новый code
    return pre + new_body + post

def replace_in_line(line, dictionary):
    for j in range(len(line)):
        if line[j] in dictionary:
            line[j] = dictionary[line[j]]

def replace_in_code(code, dictionary):
    for l in code:
        replace_in_line(l, dictionary)

def unpack_const_subscripts(code, arrays = None):
    # %% track set_item instructions
    if type(arrays) == str:
        arrays = [arrays]
    const_defs = {}
    array_defs = {}
    for l in code:
        if l[0] == 'new_const':
            const_defs[l[1]] = l[2]
        if l[0] in ['v_new_array', 'new_array']:
            array_defs[l[1]] = l
        if l[0] in ['v_make_array', 'make_array']:
            array_defs[l[1]] = l
    rs = {}
    for l in code:
        # Заменяем имена по таблице
        replace_in_line(l, rs)
        # Добавляем новые замены по операции взятия индекса
        # if l[0] == 'v___getitem__' and l[2] == 'sha512_var1':
        #     print >> sys.stderr, l, arrays, array_defs
        if l[0] in ['v___getitem__', '__getitem__'] and l[3] in const_defs and (not arrays or array_defs[l[2]][2] in arrays):
            old = l[1]
            # Берём элемент из массива
            # %% надо бы проверять, что индекс не отрицательный
            # Skipping op, array name, label
            new = array_defs[l[2]][3 + int(const_defs[l[3]])]
            # Операцию удаляем
            l[0] = drop
            # Добавляем имена в таблицу замен
            rs[old] = new
    # Удаляем указанные массивы.
    # %% Проверка, что не используются
    for a in array_defs:
        if not arrays or array_defs[a][2] in arrays:
            array_defs[a][0] = drop
    return clean(code)

def remove_assignments(code):
    # %% проверки, что это можно сделать?
    rs = {}
    for l in code:
        # print >>sys.stderr, '>>', l
        # Запоминаем соответствие от присваиваний.
        if l[0] in ('v___floordiv__', '__floordiv__'):
            # Для левой части запоминаем правую, её будем подставлять
            # вместо левой дальше.
            rs[l[1]] = l[2]
            # Пока подстановка может быть раскрыта, раскрываем её.
            while rs[l[1]] in rs:
                rs[l[1]] = rs[rs[l[1]]]
            # Само присваивание выкидываем.
            l[0] = drop
            # print >>sys.stderr, rs
        else:
            # Заменяем, согласно присваиваниям.
            for j in range(len(l)):
                # Для каждого элемента в строке: если имя в таблице замен,
                # то раскрываем его.
                if l[j] in rs:
                    l[j] = rs[l[j]]
        # print >>sys.stderr, ' <', l
    # Убираем инструкции new_var, так как без присваиваний они не
    # нужны.
    for l in code:
        if l[0] in ('new_var', 'v_new_var'):
            l[0] = drop
    return clean(code)

# def deep_copy(code, to_str = False):
#     t = type(code)
#     if t == dict:
#         r = {}
#         for k in code:
#             r[k] = deep_copy(code[k], to_str)
#     elif t == list:
#         r = []
#         for k in code:
#             r.append(deep_copy(k, to_str))
#     else:
#         r = code
#         # %% нужна проверка, что там только числа и строки
#         if to_str:
#             r = str(r)
#     return r

# def deep_copy(code, to_str = False):
#     return code

def deep_copy_str(code):
    t = type(code)
    if t == dict:
        r = {}
        for k, v in code.iteritems():
            r[k] = deep_copy_str(v)
    elif t == list:
        r = map(deep_copy_str, code)
    else:
        # %% нужна проверка, что там только числа и строки
        r = str(code)
    return r

def deep_copy_nostr(code):
    t = type(code)
    if t == dict:
        r = {}
        for k, v in code.iteritems():
            r[k] = deep_copy_nostr(v)
    elif t == list:
        r = map(deep_copy_nostr, code)
    else:
        r = code
        # return code
    return r

def deep_copy(code, to_str = False):
    r = None
    if to_str:
        r = deep_copy_str(code)
    else:
        r = deep_copy_nostr(code)
    return r

# # функция замены всех частей на строки
# def alltostr(code):
#     r = code
#     packs = [code]
#     if type(code) == dict:
#         packs = code.values()
#     # Заменяем на месте
#     for p in packs:
#         # deep copy each pack (code object)
#         p = deep_copy(p)
#         for l in p:
#             # print >> sys.stderr, l
#             for i in range(len(l)):
#                 # %% нужна проверка, что там только числа и строки
#                 l[i] = str(l[i])
#             # print >> sys.stderr, l
#     return r

# функция замены всех частей на строки
def alltostr(code):
    return deep_copy(code, True)

# It's like -> in clojure and dash.el. It is not as elegant as macro
# in lisp but is fine too. Example of usage:
# B.thread_first(
#     B.get_code_full('sha512', **args),
#     B.vectorize,
#     [ B.unroll_cycle_const_range, 'main' ],
#     B.remove_assignments,
#     [ B.dump, 'all.bytecode' ],
#     [ O.gen, c_code, args ]
# )
# Though there is thread_code for code passes. This function is for
# simpler usages.
def thread_first(what, *forms):
    for f in forms:
        if type(f) != list and type(f) != tuple:
            f = (f,)
        print >> sys.stderr, f[0]
        what = f[0](what, *f[1:])
        # После каждого прохода заменяем всё на строки
        # %% Это такой глобальный костыль, чтобы можно сохранять числа
        #  % в массив
        # %% Это должно быть медленно
        what = alltostr(what)
    return what

# Like thread_first but handles parallel branches
# If a function returns a list then the list is passed to next
# function.
# If a function returns a dictionary then
#   If next "function" is a list or a bare function then
#     we pass all values through it and collect the dictionary again
#   If next "function" is tuple then the first element is a key to
#       select the value to process through that function
# %% а что если мы пропускаем словарь, а функция вернула новый
#  % словарь, мы можем совмещать, а можем вкладывать
def thread_code(what, *forms):
    res = what
    res = deep_copy(res)
    for f in forms:
        # Если не список и не кортеж, то это bare function,
        # оборачиваем в список.
        if type(f) != list and type(f) != tuple:
            f = [f,]
        print >> sys.stderr, f[0]
        # if f[0] == dump:
        #     for r in res:
        #         print >> sys.stderr, r
        res = f[0](res, *f[1:])
        # После каждого прохода заменяем всё на строки
        # %% Это такой глобальный костыль, чтобы можно сохранять числа
        #  % в массив
        # %% Это должно быть медленно
        res = alltostr(res)
    return res

def use_define_for_some(code):
    # Все инструкции, результат которых используется один раз,
    # оборачиваются в инструкции, включающие использование #define
    # вместо присваивания.
    new_code = []
    # Находим инструкции, результат которых используется один раз.
    counts = {}
    for l in code:
        # Перебираем все имена, включая результаты, так что
        # интересующие нас встречаются дважды: при присваивании и при
        # 1 использовании.
        # Метки мы не пропускаем, потому что они не будут в качестве
        # целевого имени. То есть мы их посчитаем, но не будем проверять.
        for n in l[1:]:
            if n not in counts:
                counts[n] = 0
            counts[n] += 1
    for l in code:
        if instructions[l[0]].return_type != 'void' and counts[l[1]] == 2:
            new_code.append(['use_define', 'yes'])
            new_code.append(l)
            new_code.append(['use_define', 'no'])
        else:
            new_code.append(l)
    return new_code

def reduce_assignments(code, begin, end):
    # %% based on use_define_for_some, extract common part
    # Все инструкции, результат которых используется один раз,
    # оборачиваются в инструкции, включающие использование #define
    # вместо присваивания.
    new_code = []
    # Находим инструкции, результат которых используется один раз.
    counts = {}
    for l in code:
        # Перебираем все имена, включая результаты, так что
        # интересующие нас встречаются дважды: при присваивании и при
        # 1 использовании.
        # Метки мы не пропускаем, потому что они не будут в качестве
        # целевого имени. То есть мы их посчитаем, но не будем проверять.
        for n in l[1:]:
            if n not in counts:
                counts[n] = 0
            counts[n] += 1
    # Учитывая, что код для генерации использования define'ов убран,
    # это надо вызывать после use_define_for_some.
    for l in code:
        # %% надо бы сделать отдельное свойство у инструкций, чтобы
        #  % различать операции с присваиванием и без
        if instructions[l[0]].return_type != 'void' and counts[l[1]] > 2 and l[0] not in ['new_const', 'new_state_var']:
            # Те инструкции, что возвращают результат и имеют больше 1
            # использования - присваивания.
            new_code.append((True, l))
        else:
            new_code.append((False, l))
    # new_code - инструкции помечены, какие используют присваивание,
    # какие нет; (True, [...]) - использует, (False, [...]) - нет.
    # Находим метки
    b, e = None, None
    for i in range(len(code)):
        if code[i] == ['label', begin]:
            b = i
        if code[i] == ['label', end]:
            e = i
    pre = code[:b + 1]
    body_marked = new_code[b + 1:e]
    body = code[b + 1:e]
    post = code[e:]
    tail = body + post
    # Перебираем все инструкции в заданной области
    new_body = []
    # Словарь: имя новой переменной => { last_pos => N, имя заменяемой
    # переменной => ... }
    # %% сделать словарь, где ключ - имя заменяемой переменной?
    var_pool = {}
    for i in range(len(body_marked)):
        use_assignment, l = body_marked[i]
        # Заменяем имена согласно таблице замен.
        for j in range(len(l)):
            n = [k for k in var_pool if var_pool[k]['name'] == l[j]]
            assert len(n) <= 1
            if n:
                l[j] = n[0]
        # Если инструкция использует присваивание
        if use_assignment:
            # Проверяем, что у нас нет свободных переменных для этого
            # присваивания: выбираем те, что освободились, согласно
            # позиции последнего использования относительно нашего
            # положения.
            # %% могут быть разные паттерны использования переменных:
            #  % все поровну, некоторые чаще-реже; они могут влиять на
            #  % скорость, стоит попробовать
            ns = [k for k in var_pool if var_pool[k]['last_pos'] < i]
            if ns:
                # Если мы нашли свободные переменные, используем одну
                # из них.
                n = ns[0]
            else:
                # Если мы не нашли свободную переменную, то создаём
                # новую.
                n = new_name()
                var_pool[n] = {}
            # Теперь для выбранной переменной надо задать имя, которое
            # она заменяет и найти позицию последнего использования.
            var_pool[n]['name'] = l[1]
            # Оборачиваем присваивание в использование define'ов и
            # добавляем присваивание в переменную.
            new_body.append(['use_define', 'yes'])
            new_body.append(list(l))
            new_body.append(['use_define', 'no'])
            # # %% надо бы это делать до векторизации, а то как-то коряво
            # new_op = 'v___floordiv__' if l[0].startswith('v_') else '__floordiv__'
            new_op = '__floordiv__'
            new_body.append([new_op, n, l[1]])
            # Перебираем хвост в поисках последнего использования.
            for ti in range(i + 1, len(tail)):
                for p in tail[ti]:
                    if p == l[1]:
                        var_pool[n]['last_pos'] = ti
        else:
            new_body.append(list(l))
    # %% тут тоже нужна другая операция до/после векторизации; в целом,
    #  % надо запоминать, какой тип нужен, в пуле должно быть
    #  % разделение, потому что нельзя одни и те же переменные
    #  % использовать для разных типов.
    var_defs = [['v_new_var', k] for k in var_pool]
    # Делаем обратный словарь
    reverse_pool = {}
    for k in var_pool:
        n = var_pool[k]['name']
        assert n not in reverse_pool
        reverse_pool[n] = k
    # Заменяем имена в post
    replace_in_code(post, reverse_pool)
    return pre + var_defs + new_body + post

# def rotate_associativity(code):
#     # Крутим порядок ассоциативных операций: + ^
#     # %% не векторный вариант
#     return code

def replace_state_with_const(code):
    rs = {}
    for l in code:
        # Так не сработает, потому что константу надо подставить в инструкцию
        # if l[0] == 'new_state_var':
        #     l[0] = 'new_const'
        # Заменяем переменную состояния на константу.
        if l[0] == 'new_state_var':
            rs[l[1]] = l[2]
            l[0] = drop
        replace_in_line(l, rs)
    return clean(code)

def replace_state_with_vars(code, new_vars):
    rs = {}
    for l in code:
        if l[0] == 'new_state_var':
            rs[l[1]] = new_vars.pop(0)
            l[0] = drop
        replace_in_line(l, rs)
    return clean(code)

def replace_inputs_with_consts(code, new_consts):
    # %% rs тут не нужен
    rs = {}
    for l in code:
        if l[0] == 'input':
            c = new_consts.pop(0)
            n = new_name()
            rs[l[1]] = n
            # мы заменяем операцию на создание константы
            l[0] = 'new_const'
            l[1] = n
            assert len(l) == 2
            l.append(c)
        replace_in_line(l, rs)
    return code

def replace_length_with_const(code, new_value):
    for l in code:
        if l[0] == 'input_length':
            c = new_value
            # мы заменяем операцию на создание константы
            l[0] = 'new_const'
            assert len(l) == 2
            l.append(c)
    return code

def apply_replacements(code, rs):
    for l in code:
        for i in range(len(l)):
            if l[i] in rs:
                l[i] = rs[l[i]]
    return code

def drop_outputs(code):
    for l in code:
        if l[0] == 'output':
            l[0] = drop
    return clean(code)

def connect_inputs_outputs(*code_blocks):
    nc = []
    for code in code_blocks:
        code = deep_copy(code)
        rename_uniquely(code)
        nc.append(code)
    def collect_lines(code, what):
        return filter(lambda l: l[0] == what, code)
    main_code = nc.pop(0)
    main_outputs = collect_lines(main_code, 'output')
    for code in nc:
        inputs = collect_lines(code, 'input')
        rs = {}
        # print >> sys.stderr, len(main_outputs), len(inputs)
        assert len(main_outputs) == len(inputs)
        for l_out, l_in in zip(main_outputs, inputs):
            rs[l_in[1]] = l_out[1]
            l_in[0] = drop
            l_out[0] = drop
        apply_replacements(code, rs)
        # for l in main_outputs + inputs:
        #     l[0] = drop
        main_outputs = collect_lines(code, 'output')
        main_code += code
    return clean(main_code)

def interleave(code, number):
    assert type(number) == int
    # assert number > 1
    assert number >= 1
    if number == 1:
        return code
    # Мы размножаем все инструкции, кроме циклов (ну и управления
    # использованием define'ов). При этом содержимое циклов может
    # перемешиваться, а может и не перемешиваться. Операции вне циклов
    # должны чередоваться.
    # %% Если я использую define'ы, то будет тяжело чередовать
    #  % операции.
    # %% не перемешивание циклов
    rss = [{} for i in range(number)]
    new_code = []
    saved_code = []
    # Собираем код, используемый циклом
    # %% в общем случае это не будет работать
    to_save = {}
    mix_arrays = True
    # mix_arrays = False
    for l in reversed(code):
        if l[0] == 'cycle_const_range':
            for i in range(number):
                rss[i][l[1]] = l[1]
            for n in l[3:]:
                to_save[n] = 1
                for i in range(number):
                    rss[i][n] = n
        if mix_arrays and l[0] in ['v_make_array']:
            # %% support new_array too (everywhere when (v_)make_array
            #  % used)
            for n in l[2:]:
                to_save[n] = 1
        if l[0] == 'var_setup':
            saved_code.append(l)
        if instructions[l[0]].return_type != 'void' and l[1] in to_save or l[0] in ['v_new_array', 'print_verbatim']:
            if l[0] in ['v_new_array', 'print_verbatim']:
                to_save[l[1]] = 1
            # %% v_new_array пока что только для констант, поэтому его
            #  % мы не размножаем
            saved_code.append(l)
            for i in range(number):
                rss[i][l[1]] = l[1]
            for n in l[2:]:
                to_save[n] = 1
    saved_code = list(reversed(saved_code))
    # Добавляем константу 1
    one = new_const(1)
    new_code.append(one)
    one = one[1]
    # Добавляем код определения констант для сдвигов и размера интерлива
    offsets = [new_const(i) for i in range(number)]
    Nl = new_const(number)
    N = Nl[1]
    new_code += [Nl] + offsets
    offsets = [l[1] for l in offsets]
    for l in code:
        # print >> sys.stderr, '>>', l
        if l in saved_code:
            new_code.append(l)
            # print >> sys.stderr, l
            # print >> sys.stderr, ' <-  same'
        elif l[0] in ['cycle_const_range', 'use_define', 'label', 'cycle_end']:
            new_code.append(l)
            # print >> sys.stderr, ' <-  same'
        elif mix_arrays and l[0] in ['v_make_array']:
            # %% v_new_array, scalar variants
            # Если мы создаём массив, надо делать его больше в N раз.
            # Умножаем размер массива на N.
            # %% Это можно сделать прямо тут, без операции.
            n = new_name()
            new_code.append(['__mul__', n, N, l[3]])
            l[3] = n
            # print >> sys.stderr, l
            for rs in rss:
                rs[l[1]] = l[1]
            new_code.append(l)
        else:
            for i in range(number):
                # Добавляем инструкцию в новый код нужное количество раз
                new_line = [l[0]]
                # %% new_state_var пока что должен быть заменён на
                #  % new_const
                if l[0] in ['new_const', 'v_new_const']:
                    # %% copy-pasted
                    if l[1] not in rss[i]:
                        rss[i][l[1]] = new_name()
                    new_line.append(rss[i][l[1]])
                    new_line.append(l[2])
                elif mix_arrays and l[0] in ['v___getitem__', 'v_set_item']:
                    # %% scalar variant
                    # %% а что если есть несколько массивов?
                    # Если у нас берётся элемент, то индекс должен
                    # быть не idx, а  idx * N + i  .
                    # Индексы не меняют для вектора констант.
                    array_name = l[2] if l[0] == 'v___getitem__' else l[1]
                    idx = l[3] if l[0] == 'v___getitem__' else l[2]
                    m = new_name()
                    s = new_name()
                    # %% можно не копировать описание индекса
                    # new_code.append(['__mul__', m, rss[i][idx], N])
                    # Если массив констант, то индексы умножаются на 1
                    # и не сдвигаются
                    # %% сие корявенько
                    new_code.append(['__mul__', m, rss[i][idx], one if array_name in to_save else N])
                    # new_code.append(['__add__', s, m, offsets[i]])
                    if i > 0 and array_name not in to_save:
                        new_code.append(['__add__', s, m, offsets[i]])
                    else:
                        # Для нулевого "треда" итоговый результат - сумма.
                        s = m
                    if l[0] == 'v___getitem__':
                        # Elements: result array index
                        # %% copy-pasted
                        if l[1] not in rss[i]:
                            rss[i][l[1]] = new_name()
                        # Добавляем целевое имя
                        new_line.append(rss[i][l[1]])
                        # Добавляем имя массива
                        new_line.append(l[2])
                        # Добавляем новый индекс
                        new_line.append(s)
                    else:
                        # Elements: array index value
                        # Добавляем имя массива
                        new_line.append(l[1])
                        # Добавляем новый индекс
                        new_line.append(s)
                        # Добавляем значение
                        new_line.append(rss[i][l[3]])
                else:
                    for n in l[1:]:
                        # Если имя есть в соответствующей таблице замен,
                        # то заменяем, если нет, то создаём новое имя.
                        if n not in rss[i]:
                            rss[i][n] = new_name()
                        new_line.append(rss[i][n])
                new_code.append(new_line)
                # print >> sys.stderr, ' <', new_line
    return new_code

# http://www.agner.org/optimize/instruction_tables.pdf
# core i7 920, Nehalem
latencies = {
    # instruction: ?-? - latency, reciprocal throughput; ...
    # %% not sure xmm-m128 means memory -> register or register ->
    #  % memory; I choose memory -> register; tune it by practice.
    # movdqa: xmm-xmm - 1, 0.33; xmm-m128 - 2, 1; m128-xmm - 3, 1
    'to_mem': 3,
    'from_mem': 2,
    'move': 1,
    # paddq: xmm-xmm - 1, 0.5
    'add': 1,
    # psrlq psllq: xmm-i - 1, 1; xmm-xmm - 2, 2
    'shift_right': 1,
    'shift_left': 1,
    # pand(n) por pxor: xmm-xmm - 1, 0.33; xmm,m - ?, 1
    # %% these and 'move' may be pipelined, right? how much? use it
    'and': 1,
    'andnot': 1,
    'or': 1,
    'xor': 1
}
# %% The model lacks ability to save to scalar (general purpose)
#  % registers. It is possible with
#  %   MOV RAX, <first_half>
#  %   MOVQ XMM0, RAX
#  %   MOV RAX, <second_half>
#  %   MOVQ XMM1, RAX
#  %   MOVLHPS XMM0,XMM1
#  % http://stackoverflow.com/questions/6654099/how-to-move-128-bit-immediates-to-xmm-registers
#  % Moving back may be performed with movehl, movelh (really?)
#  % http://www-db.in.tum.de/~finis/x86-intrin-cheatsheet-v2.1.pdf
registers = 16

# %% it depends on target platform, so the right place for it is not here.
def make_asm(code, begin = None, end = None):
    # %% implement
    b, e = 0, len(code)
    for i in range(len(code)):
        if code[i] == ['label', begin]:
            b = i
        if code[i] == ['label', end]:
            e = i
    pre = code[:b + 1]
    body = code[b + 1:e]
    post = code[e:]
    return code

def short_circuit_getitem_after_set_item(code):
    # Если мы берём элемент из массива и в области видимости есть
    # присваивание в этот элемент массива, то берём напрямую значение.
    # %% мы не переступаем через границу цикла, хотя иногда через
    #  % начало можно было бы
    # %% implement
    return code

def replace_new_array(code):
    # Заменяем new_array на make_array и присваивания.
    new_code = []
    for l in code:
        if l[0] == 'new_array':
            # new_array(array_name, label, element1, element2, ...)
            name = l[1]
            label = l[2]
            elements = l[3:]
            # Записываем длину массива
            len_name = new_name()
            new_code.append(['new_const', len_name, len(elements)])
            # Создаём массив
            new_code.append(['make_array', name, label, len_name])
            # Присваиваем элементы
            for i, j in enumerate(elements):
                # Создаём константу индекса
                n = new_name()
                new_code.append(['new_const', n, i])
                # Присваиваем элемент
                new_code.append(['set_item', name, n, j])
        else:
            new_code.append(l)
    return new_code

# %% это надо слить с новым так, чтобы было управление тем, какие
#  % массивы раскрывать, а какие нет
# %% bs_bits тут не нужен
def bitslice_old(code, bs_bits, size):
    # %% надо бы сделать поддержку new_array, чтобы не раскрывать
    code = replace_new_array(code)
    # for l in code
    #     if l[0] == 'new_array':
    #         raise Exception('new_array should be expanded')
    # проходим по коду и заменяем часть операций на новые; ведём
    # таблицу имён: имя -> вектор битов
    bits = 8 * size
    new_code = []
    names = {}
    consts = {}
    # Создаём константы для 0 и 1
    bs_zero = new_name()
    new_code.append(["bs_new_const", bs_zero, 0])
    bs_one = new_name()
    new_code.append(["bs_new_const", bs_one, 1])
    # Проходим код, чтобы записать константы, которые не надо
    # битслайсить. В этом плане, битслайс очень похож на векторизацию.
    # не все константы надо векторизовывать, размеры битовых
    # сдвигов/ротейтов не надо
    # %% надо бы проверять, что константы не используются в разных
    #  % местах и разделять на векторную и скалярную
    # %% Copy-pasting is evil! Copied from vectorize()
    no_vec = {}
    array_vars = {}
    for l in code:
        if l[0] == 'cycle_const_range':
            array_vars[l[1]] = 1
            # %% это наверное надо и в vectorize добавить
            no_vec[l[3]] = 1
            no_vec[l[4]] = 1
            no_vec[l[5]] = 1
        if l[0] in ['ror', 'rol', '__rshift__', '__lshift__', '__getitem__', 'make_array']:# or (l[0].startswith('cycle_') and l[0] != 'cycle_end'):
            no_vec[l[3]] = 1
        if l[0] in ['set_item']:
            no_vec[l[2]] = 1
        if l[0] == '__sub__' and l[2] in array_vars:
            # %% очередной костыль...
            # %% эта проверка копируется для самой операции вычитания
            # %% любой аргумент, а не только левый
            # Проверяем, что левый аргумент является переменной цикла.
            # Тогда не векторизуем константу, которая вычитается.
            no_vec[l[3]] = 1
        # if l[0] not in to_vector:
        #     for i in l[1:]:
        #         no_vec[i] = 1
        if l[0] == 'make_array':
            # Размер массива
            no_vec[l[2]] = 1
    # Собираем константы
    for l in code:
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
    # Обрабатываем код
    for l in code:
        # %% надо сделать различную генерации в зависимости от размера
        #  % выходных векторов
        if l[1] in no_vec:
            # Пропускаем не векторизуемые вещи
            new_code.append(l)
            continue
        if l[0] == 'make_array':
            new_code.append(["bs_" + l[0]] + l[1:])
        elif l[0] == '__getitem__':
            v = []
            for i in range(bits):
                n = new_name()
                v.append(n)
                # Взятие элемента из массива теперь ещё несёт бит
                new_code.append(["bs_getitem", n, l[2], l[3], i])
            names[l[1]] = v
        elif l[0] == 'set_item':
            # set_item(array, idx, value)
            # bs_set_item(array, idx, value, bit)
            for i, j in zip(range(bits), names[l[3]]):
                new_code.append(['bs_set_item', l[1], l[2], j, i])
        elif l[0] == 'new_var':
            v = []
            for i in range(bits):
                n = new_name()
                v.append(n)
                new_code.append(['bs_new_var', n])
            names[l[1]] = v
        elif l[0] in ['print_var', 'output']:
            for i, j in enumerate(names[l[1]]):
                new_code.append(['bs_' + l[0], j, i])
        elif l[0] == 'input':
            v = []
            for i in range(bits):
                n = new_name()
                v.append(n)
                new_code.append(['bs_input', n, i])
            names[l[1]] = v
        elif l[0] in ['__xor__', '__or__', '__and__']:
            op = 'bs_' + l[0].replace('_', '')
            # для аргументов берём пары из векторов, для каждой пары
            # делаем новую операцию, вектор новых имён запоминаем
            v = []
            for i, j in zip(names[l[2]], names[l[3]]):
                n = new_name()
                v.append(n)
                new_code.append([op, n, i, j])
            names[l[1]] = v
        elif l[0] == '__invert__':
            # %% copy-pasting is evil! тут можно было подсократить,
            #  % потому что скопирован код
            op = 'bs_' + l[0].replace('_', '')
            v = []
            for i in names[l[2]]:
                n = new_name()
                v.append(n)
                new_code.append([op, n, i])
            names[l[1]] = v
        elif l[0] == '__getitem__':
            # __getitem__(name, array, idx)
            # bs_getitem(name, array, idx, bit)
            # Подобно другим операциям, но при взятии элемента, ещё
            # номер бита указывается.
            # %% В некоторых хешах всё-таки нужно делать битовые
            #  % индексы (например, в sunmd5 на этапе coin flip). Там
            #  % они не константы, операция при этом должна быть другой.
            op = 'bs_' + l[0].replace('_', '')
            v = []
            for i in range(bits):
                n = new_name()
                v.append(t)
                new_code.append([op, n, l[2], l[3], i])
            names[l[1]] = v
        elif l[0] == '__add__':
            # op = lambda *args: new_code.append('bs_{2} {0} {1} {3}'.format(*args))
            op = lambda r, a, op, b: new_code.append(['bs_' + op, r, a, b])
            a = names[l[2]]
            b = names[l[3]]
            # создаём все имена впрок
            # (возможно, есть лишние, это не страшно)
            r, n, x, q, w = [[new_name() for j in range(i)]
                            for i in [bits] * 5]
            # r - result bit
            # n - carry bit
            for i in reversed(range(bits)):
                if i == bits - 1:
                    op(r[i], a[i], 'xor', b[i])
                    op(n[i], a[i], 'and', b[i])
                else:
                    op(x[i], a[i], 'xor', b[i])
                    op(r[i], x[i], 'xor', n[i + 1])
                    # %% Better circuit here.
                    # n[i] = b[i] ^ (x[i] & (b[i] ^ n[i + 1]))
                    op(w[i], b[i], 'xor', n[i + 1])
                    op(q[i], x[i], 'and', w[i])
                    op(n[i], b[i], 'xor', q[i])
            names[l[1]] = r
        elif l[0] == '__floordiv__':
            # assignment
            # %% rotate has problems overriding values: a = rol(a, 1)
            #  % is broken; maybe temp vars can solve that
            #  % (предположительно, компилятор уберёт ненужные)
            # Для всех пар битов, присваиваем правый в левый.
            for i, j in zip(names[l[1]], names[l[2]]):
                new_code.append(['bs_assign', i, j])
        elif l[0] == 'new_const':
            # Режем константу на биты и запоминаем в виде вектора
            # битов.
            c = int(l[2])
            # ** Биты идут со старших: старшие биты - в начале вектора,
            #  * младшие - в конце. Начало вектора - слева, конец -
            #  * справа. Соответствует битовым сдвигам.
            names[l[1]] = [bs_one if c & (1 << i) else bs_zero for i in range(bs_bits - 1, -1, -1)]
        elif l[0] == '__rshift__':
            # We just manipulated names.
            # У нас 3 аргумента: результат, переменная, сдвиг.
            # В таблицу имён мы присваиваем сдвинутый вектор,
            # дополненный нулями, нужны нули. Операции при этом не
            # получается.
            s = int(consts[l[3]])
            names[l[1]] = [bs_zero] * s + names[l[2]][: bits - s]
        elif l[0] == 'ror':
            # Как сдвиг, только мы не дополняем нулями, а берём другой
            # кусок.
            s = int(consts[l[3]])
            names[l[1]] = names[l[2]][bits - s :] + names[l[2]][: bits - s]
        else:
            # operation that should not be bitsliced, pass as is
            new_code.append(l)
    return new_code

def sbox_table_hash_hex(table):
    table_string = '_'.join(str(i) for i in table)
    h = hashlib.new('sha256')
    h.update(table_string)
    table_hash = h.hexdigest()
    return table_hash

def bs_pick_sbox(table):
    # По таблице возвращаем схему для интеграции в общий circuit,
    # количество входных битов, количество выходных битов.
    name = "_".join(str(i) for i in table)
    # We pick the first one
    # %% allow user to chose sbox
    files = glob.glob("sboxes/" + name + ".*")
    if len(files) != 0:
        fname = files[0]
    else:
        h = sbox_table_hash_hex(table)
        fname = glob.glob("sboxes/" + h + ".*")[0]
    code = slurp_bytecode(fname)
    counts = count_instructions(code)
    # %% get number either from code or from file name
    return code, counts['input'], counts['output']

def bs_swap_bytes(a, size):
    # return a
    bits = []
    for i in reversed(range(size)):
        bits += a[i * 8 : i * 8 + 8]
    return bits

def expand_bs_andnot(code):
    # r = a `andnot` b  =>  r = a & ~b
    new_code = []
    for l in code:
        if l[0] == 'bs_andnot':
            n = new_name()
            new_code.append(['bs_invert', n, l[3]])
            l[3] = n
            l[0] = 'bs_and'
        new_code.append(l)
    return new_code

# Функция для исследования возможности реверса
# Показывает номер лучшего выхода для первичной проверки и выходит.
# %% случай одного выхода не сработает для битслайса, было бы
#  % интересно посмотреть, нельзя реверсить битслайс не до 1 инта, к
#  % тому же нам не все биты нужны, проверки в crypt_all можно
#  % растянуть и делать постепенно
# %% need to unroll all loops, B.remove_assignments,
#  % B.unpack_const_subscripts before the research
def research_reverse(code):
    new_code = []
    reverse_code = []
    # Идём с конца от выходов по операциям для реверса: swap_to_be
    # выпадает в swap_to_le, а + и ^ реверсятся, только если у нас
    # один из аргументов - константа, но ассоциативность играет роль:
    # r = (a ^ b) ^ C - константа сверху, мы реверсим
    # r = a ^ (b ^ C) - константа не сверху, мы не видим возможность
    # реверса; надо привести к первому случаю, либо заглядывать
    # глубже.
    # %% обрабатывать ассоциативность
    # %% обрабатывать реверс
    # %% изменение порядка операций может бить по производительности
    # %% для outputs можно было бы использовать множество, а не словарь
    outputs = {}
    reverse_inputs = []
    reverse_outputs = []
    # Записываем константы
    consts = {}
    for l in code:
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
    # Для каждого выхода находим инструкцию, дальше которой не
    # реверсится
    # %% тут можно сразу собрать инструкции для реверса в отдельные
    #  % массивы по выходам
    connections = {}
    for l in reversed(code):
        if l[0] == 'output':
            outputs[l[1]] = 1
            # print >> sys.stderr, 'same', l[1]
            connections[l[1]] = l[1]
        if l[0] == 'swap_to_be' and l[1] in outputs:
            # Если операция - swap_to_be и её результат - выход
            # алгоритма, то мы обращаем операцию, а её аргумент
            # считаем новым выходом алгоритма
            old_output = l[1]
            new_output = l[2]
            # print >> sys.stderr, new_output, old_output
            connections[new_output] = connections[old_output]
            del connections[old_output]
            del outputs[old_output]
            outputs[new_output] = 1
        if l[0] in ['__xor__', '__add__'] and l[1] in outputs and (l[2] in consts or l[3] in consts):
            # Если операция - сложение (битовое ^ или численное +),
            # один из аргументов - константа, а результат - выход, то
            # мы обращаем операцию. Не константный аргумент становится
            # новым выходом.
            old_output = l[1]
            # %% если оба константы, мы не оптимизировали
            #  % константные подвыражения, это надо было сделать
            #  % раньше; пока что просто ломаемся
            if l[2] in consts and l[3] in consts:
                raise Exception('+/^ with 2 consts')
            if l[2] in consts:
                const = l[2]
                new_output = l[3]
            else:
                const = l[3]
                new_output = l[2]
            # print >> sys.stderr, new_output, old_output
            connections[new_output] = connections[old_output]
            del connections[old_output]
            del outputs[old_output]
            outputs[new_output] = 1
        # %% сделать проверку, что выход - результат, а операция не
        #  % реверсится, тогда удалять выход из множества выходов
        if l[0] == 'cycle_end':
            # %% мы всегда должны разворачивать; операции в цикле не
            #  % могут быть реверсены
            raise Exception('cycle_end reversing ops')
    # Считаем размеры зависимостей для каждого из выходов
    sizes = {}
    for o in outputs:
        count = 0
        is_needed = { o: 1 }
        for l in reversed(code):
            # %% тут не считают операции с побочными эффектами, так
            #  % что результат - лишь оценка
            if instructions[l[0]].return_type != 'void' and l[1] in is_needed:
                # Записываем аргументы в множество нужных нам
                for i in l[2:]:
                    is_needed[i] = 1
            # Все инструкции проверяем на использование нужных
            # элементов; такие инструкции не могут быть отброшены.
            for i in l[1:]:
                if i in is_needed:
                    # Считаем инструкцию в количество нужных
                    count += 1
                    break
        sizes[o] = count
        # print >> sys.stderr, is_needed
    # Находим ближайший выход
    m = len(code)
    mo = None
    for o in sizes:
        # Exactly <= (not <) because there may be full length: no
        # reverse at all and only 1 output, we pick that output
        if sizes[o] <= m:
            m = sizes[o]
            mo = o
    assert mo != None
    # Находим номер выхода по оригинальному коду
    output = connections[mo]
    # Собираем выходы
    onums = []
    for l in code:
        if l[0] == 'output':
            onums.append(l[1])
    back_connections = {}
    for i in connections:
        if i != connections[i]:
            back_connections[connections[i]] = i
    # %% при равном размере мы хотели бы выбирать выход с меньшим
    #  % размеров реверса
    # print >> sys.stderr, connections
    # print >> sys.stderr, back_connections
    # print >> sys.stderr, sizes
    # print >> sys.stderr, onums
    for i, o in enumerate(onums):
        print >> sys.stderr, "#{0} output {1} has size {2}".format(i, o, sizes[back_connections[o]])
    print >> sys.stderr, "Result: use output #{0} ({1} connected to {2}) size = {3}".format(onums.index(output), output, mo, m)
    # выводим все выходы по порядку
    print >> sys.stderr, "All size:", sizes
    raise Exception('exited; end of execution, use the result above')

# Функция для возврата пустого кода для реверса операций
# Возвращает: словарь {
#   'code': основной код,
#   'reverse': обратный код для обработки хеша.
# }
def no_reverse(code, output_number):
    reverse_code = [
        ['input', 'r1'],
        ['output', 'r1']]
    # Записываем выходы
    outputs_array = []
    last_vs = None
    for l in code:
        if l[0] == 'var_setup':
            last_vs = l
        if l[0] == 'output':
            outputs_array.append(l[1])
    code.append(['check_output', outputs_array[output_number]])
    assert last_vs != None
    return { 'code': code, 'reverse': [last_vs] + reverse_code }

# Функция для реверса операций (+, ^, swap_to_be)
# Реверсит только 1 инт, на него ставит check_output инструкцию,
# все выходы сохраняются, для binary() возвращается код для реверса
# одного инта
# Получает: код, номер выхода для реверса.
# Возвращает: словарь {
#   'code': основной код,
#   'reverse': обратный код для обработки хеша.
# }
# %% по структуре полностью копируем research_reverse
# %% ещё ротейты должны реверситься
def reverse_ops(code, output_number):
    reverse_code = []
    # Записываем константы
    consts = {}
    for l in code:
        if l[0] == 'new_const':
            consts[l[1]] = l
    # Записываем выходы
    outputs_array = []
    for l in code:
        if l[0] == 'output':
            outputs_array.append(l[1])
    output_to_reverse = outputs_array[output_number]
    # Мы нашли название выхода для реверса, теперь откатываем операции
    outputs = { output_to_reverse: 1 }
    # Вставляем операцию входа в алгоритм реверса
    reverse_code.append(['input', output_to_reverse])
    last_idx = None
    last_output = None
    for op_idx, l in reversed(list(enumerate(code))):
        if l[0] == 'swap_to_be' and l[1] in outputs:
            # Если операция swap_to_be и её результат - выход
            # алгоритма, то мы обращаем операцию, а её аргумент
            # считаем новым выходом алгоритма
            old_output = l[1]
            new_output = l[2]
            del outputs[old_output]
            outputs[new_output] = 1
            # Запоминаем обратную операцию
            reverse_code.append(['swap_to_le', l[2], l[1]])
            last_idx = op_idx
            last_output = new_output
        if l[0] in ['__xor__', '__add__'] and l[1] in outputs and (l[2] in consts or l[3] in consts):
            # Если операция - сложение (битовое ^ или численное +),
            # один из аргументов - константа, а результат - выход, то
            # мы обращаем операцию. Не константный аргумент становится
            # новым выходом.
            old_output = l[1]
            # %% если оба константы, мы не оптимизировали
            #  % константные подвыражения, это надо было сделать
            #  % раньше; пока что просто ломаемся
            if l[2] in consts and l[3] in consts:
                raise Exception('+/^ with 2 consts')
            if l[2] in consts:
                const = l[2]
                new_output = l[3]
            else:
                const = l[3]
                new_output = l[2]
            del outputs[old_output]
            outputs[new_output] = 1
            # Запоминаем обратную операцию
            # %% хорошо бы операцию определения константы тоже взять,
            #  % правда, имя надо заменить; если выводить в один файл,
            #  % то надо все константы выносить в начало файла
            reverse_code.append([
                '__sub__' if l[0] == '__add__' else '__xor__',
                new_output,
                old_output,
                const
                ])
            last_idx = op_idx
            last_output = new_output
        # %% сделать проверку, что выход - результат, а операция не
        #  % реверсится, тогда удалять выход из множества выходов
        if l[0] == 'cycle_end':
            # %% мы всегда должны разворачивать; операции в цикле не
            #  % могут быть реверсены
            # %% пока что не крашимся, но надо вручную проверять, что
            #  % в нужном месте реверсимся
            pass
            # raise Exception('cycle_end reversing ops')
    assert last_idx != None
    assert last_output != None
    # Копируем инструкции описания констант в код обращения
    const_code = []
    for l in reverse_code:
        for i in l:
            if i in consts:
                const_code.append(consts[i])
    reverse_code = const_code + reverse_code
    # В основной код вставляем инструкцию check_output - она будет
    # отмечать реверсенный выход.
    # %% убрать старый выход?
    code.insert(last_idx + 1, ['check_output', last_output])
    # Вставляем операцию выхода из алгоритма реверса: выход - это
    # результат последней операции
    reverse_code.append(['output', reverse_code[-1][1]])
    return { 'code': code, 'reverse': reverse_code }

# Функция для откладывания операций, которые не нужны для быстро
# проверки результатов
# Возвращает: словарь {
#   'code': основной код,
#   'postponed': отложенный код
# }
# %% а этого достаточно? или нам надо больше код возвращать, чтобы
#  % иметь управление над порядком данных в binary? думаю, нам нужен
#  % код для binary, а может, и других методов...
def postpone_part(code):
    new_code = []
    postponed_code = []
    # %%%
    return { 'code': new_code, 'postponed': postponed_code }

# Реверс операций и откладывание того, что не нужно для минимальной
# проверки
# Возвращает: словарь {
#   'code': основной код,
#   'postponed': код доведения до минимальной проверки,
#   'reverse': обратный код для обработки хеша.
# }
def reverse_ops_and_postpone(code):
    # Обращаем операции
    t = reverse_ops(code)
    # Отделяем часть, которая не нужна для сравнения
    t2 = postpone_part(t['code'])
    t2['reverse'] = t['reverse']
    return t2

# Функция для введение повторного использования переменных, чтобы не
# использовать кучу временных переменных: добавляем вначале несколько
# свободных переменных, в них присваиваем результаты, всё остальное
# оборачиваем, как use_define_for_some; по сути мы вообще всё
# оборачиваем так, но у нас появятся присваивания
def reuse_variables(code):
    new_code = []
    # Проходим по коду и записываем положения использования переменных
    used_at = {}
    for i, l in enumerate(code):
        for n in l[1:]:
            used_at[n] = i
    # Считаем количество обращений для имён
    counts = {}
    for l in code:
        # Перебираем все имена, включая результаты, так что
        # интересующие нас встречаются дважды: при присваивании и при
        # 1 использовании.
        # Метки мы не пропускаем, потому что они не будут в качестве
        # целевого имени. То есть мы их посчитаем, но не будем проверять.
        for n in l[1:]:
            if n not in counts:
                counts[n] = 0
            counts[n] += 1
    # Проходим по коду и составляем список переменных
    # variables = [0] * 20
    variables = []
    substs = {}
    #  and counts[l[1]] != 2
    check = lambda l: instructions[l[0]].return_type != 'void' and l[0] not in ['new_const', 'input']
    check2 = lambda l, i: check(l) # and (counts[l[1]] != 2)
    for i, l in enumerate(code):
        # Если операция имеет результат и используется несколько раз,
        # то она записывается в переменную
        # if check(l):
        if check2(l, i):
            # Мы хотим записать результат в переменную: если у нас
            # есть свободная переменная, то в неё, иначе создаём новую
            # переменную.
            vv = list(enumerate(variables))
            # random.shuffle(vv)
            # vv = reversed(vv)
            # Ищем свободную переменную:
            for j, v in vv:
                # Если оригинальная переменная, связанная с этой
                # позицией уже не используется, то мы запоминаем в эту
                # позицию новую переменную. Иначе создаём новую
                # позицию.
                if v == 0 or used_at[v] <= i:
                    variables[j] = l[1]
                    substs[l[1]] = j
                    break
            else:
                substs[l[1]] = len(variables)
                variables.append(l[1])
    # print >> sys.stderr, variables, substs
    # У нас есть массив variables, по его длине нам нужно сделать
    # переменные; после этого мы заменим старые имена на новые по
    # словарю substs.
    for i in range(len(variables)):
        v = new_name()
        new_code.append(['new_var', v])
        variables[i] = v
    new_code.append(['use_define', 'yes'])
    for j, l in enumerate(code):
        l2 = list(l)
        used = check2(l, j)
        for i in range(2 if used else 1, len(l2)):
            # заменяем чтения оригинальных переменных на обращения к
            # новым переменным
            if l[i] in substs:
                l2[i] = variables[substs[l[i]]]
        new_code.append(l2)
        if used:
            # вставляем присваивание
            new_code.append(['__floordiv__', variables[substs[l[1]]], l[1]])
    new_code.append(['use_define', 'no'])
    return new_code

# Remove all print instructions
def drop_print(code):
    # %% more instructions
    return [l for l in code if l[0] not in
            ['print_var', 'v_print_var', 'bs_print_var', 'print_verbatim']]

def override_state(code, state):
    consts = {}
    for l in code:
        # We collect lists with constants and then override constants
        # when we meet state variables.
        # ** It assumes that merging of constants is disabled.
        if l[0] == 'new_const':
            consts[l[1]] = l
        if l[0] == 'new_state_var':
            consts[l[2]][2] = str(state.pop(0))
    return code

def drop_last_output(code):
    outputs = 0
    for l in code:
        if l[0] == 'output':
            outputs += 1
    k = 0
    for l in code:
        if l[0] == 'output':
            k += 1
            if outputs == k:
                l[0] = drop
    return clean(code)

# %% it is reused for regular code, not sure if bitslice is needed yet
def split_bitslice(code, size, regular = False):
    # Мы разбиваем код на части
    # %% assignment, cycles are prohibited
    part1 = []
    part2 = []
    p1names = {}
    k = 0
    # %% если мы в половине встретили выход, то нам его надо
    #  % пробросить дальше, либо мне нужна инструкция для
    #  % промежуточных выходов, либо не надо добавлять в первую часть,
    #  % вторая часть подхватит это
    last_var_setup = None
    for l in code:
        if k < size:
            # До заданного размера мы всё сохраняем
            part1.append(l)
            # Запоминаем имена, описанные в первой части
            if instructions[l[0]].return_type != 'void':
                p1names[l[1]] = 1
            if l[0] == 'var_setup':
                last_var_setup = l
        else:
            if k == size:
                part2.append(last_var_setup)
            # Если аргумент встречался, то на этой точке мы добавляем
            # выход из первой части и вход во второй.
            for n in l[1:]:
                if n in p1names:
                    # "ignored" is a number of bit, we don't care here
                    if regular:
                        part1.append(["output", n])
                        part2.append(["input", n])
                    else:
                        part1.append(["bs_output", n, "ignored"])
                        part2.append(["bs_input", n, "ignored"])
                    del p1names[n]
            part2.append(l)
        k += 1
    return part1, part2

def split_at(code, where):
    places = filter(lambda l: l[0] == 'may_split_here' and l[1] == where, code)
    assert len(places) == 1
    # print >> sys.stderr, code.index(places[0])
    pos = code.index(places[0])
    return split_bitslice(code, pos, True)

def drop_arrays(code):
    # %% работает после compute_const_expressions
    # %% надо проверять, где можно убрать операции, а где нет
    new_code = []
    consts = {}
    arrays = {}
    substs = {}
    for l in code:
        for i in range(len(l)):
            if l[i] in substs:
                l[i] = substs[l[i]]
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
        if l[0] == 'set_item':
            # We fail on non-const subscripts.
            # %% It needs constant subexpression computations.
            assert l[2] in consts
            arrays[l[1]][consts[l[2]]] = l[3]
        elif l[0] == '__getitem__':
            substs[l[1]] = arrays[l[2]][consts[l[3]]]
        elif l[0] == 'make_array':
            arrays[l[1]] = {}
        else:
            new_code.append(l)
    return new_code

# def drop_unused(code):
#     used = {}
#     new_code = []
#     for l in code:
#         try:
#             instructions[l[0]]
#         except Exception:
#             print >> sys.stderr, l
#         ii = instructions[l[0]]
#         # Если void, то все аргументы надо отметить
#         for e in l[2 - (ii.return_type == 'void'):]:
#             # if e not in used:
#             #     used[e] = 0
#             # used[e] += 1
#             used[e] = 1
#     print >> sys.stderr, ">>>", 'b_var7331' in used
#     for l in code:
#         ii = instructions[l[0]]
#         # if ii.return_type == 'void' or (ii.return_type != 'void' and used[l[1]] > 1):
#         if ii.return_type == 'void' or (ii.return_type != 'void' and l[1] in used):
#         # if ii.return_type == 'void' or l[1] in used:
#             new_code.append(l)
#     return new_code

def drop_unused(code):
    used = {}
    r_new_code = []
    for l in reversed(code):
        try:
            ii = instructions[l[0]]
        except Exception:
            print >> sys.stderr, l
            raise
        # %% надо бы проверять, что цикл не пустой
        if ii.return_type == 'void' or (ii.return_type != 'void' and l[1] in used) or l[0].startswith('cycle_'):
            # Если инструкции не возвращает ничего, то это побочный
            # эффект, она нам нужна.
            # %% Присваивания в массив не возвращают, но могут быть не
            #  % нужны.
            # Или инструкция нужна, если она возвращает значение,
            # которое используется.
            r_new_code.append(l)
            # Если void, то все аргументы надо отметить, как используемые
            for e in l[2 - (ii.return_type == 'void'):]:
                used[e] = 1
    return list(reversed(r_new_code))

def gen_asm(code):
    # количество регистров
    rk = 32
    # индексы регистров
    ris = list(range(rk))
    # состояние регистров
    registers = ([None] * rk)
    consts = {}
    asm = []
    for li in range(len(code)):
        l = code[li]
        # Очищаем регистры: если значение больше не будет
        # использоваться, то выкидываем регистр.
        for ri in ris:
            r = registers[ri]
            f = True
            for l2 in code[li:]:
                for e in l2[1:]:
                    if e == r:
                        f = False
            if f:
                registers[ri] = None
        if l[0] == 'label':
            asm.append(l)
            continue
        # %% у нас, вроде, не должно быть побочных эффектов, на всяких
        #  % случай; кроме, label
        assert l[0] == 'output' or instructions[l[0]].return_type != 'void'
        # обрабатываем новый код
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
        elif l[0] == 'input':
            # Размещение входов в регистрах - за пределами
            # генерируемого кода.
            # Кладём в первый свободный регистр.
            if None in registers:
                i = registers.index(None)
                registers[i] = l[1]
            else:
                die("can't find free register for input")
        else:
            # Если на регистр среди аргументов текущей операции 1
            # ссылка, то можно использовать этот регистр в качестве
            # целевого, иначе надо копировать значение.
            i = None
            for e in l[2:]:
                # есть элемент, есть регистр; аргументы могут быть
                # константами, тогда их не будет в регистре
                if e not in consts:
                    ti = registers.index(e)
                    # ti - индекс регистра с возможным аргументом,
                    # теперь надо убедиться, что на него больше нет
                    # ссылок
                    for l2 in code[li + 1 :]:
                        if e in l2:
                            break
                    else:
                        # Если мы не нашли других ссылок на значение,
                        # то мы его заменим.
                        i = ti
                        break
            if i == None:
                # Если мы не нашли регистр, который можем использовать, как
                # целевой, то мы копируем в неиспользуемый регистр.
                i = registers.index(None)
                # Мы копируем не константу. Для этого надо найти
                # регистр.
                for e in l[2:]:
                    if e not in consts:
                        arg_i = registers.index(e)
                        break
                asm.append(['copy', 'r' + str(i), 'r' + str(arg_i)])
                registers[i] = registers[arg_i]
            # i - номер целевого регистра для инструкции;
            # registers[i] - имя переменной одного из аргументов,
            # остальные аргументы должны добавлены в инструкцию
            args = []
            for e in l[2:]:
                # %% всё это не учитывает порядок аргументов.
                if e != registers[i]:
                    if e in consts:
                        # Мы добавляем константы явно
                        args.append(consts[e])
                    else:
                        # Если аргумент - не константа, то мы
                        # добавляем регистр по номеру.
                        args.append('r' + str(registers.index(e)))
            asm.append([l[0], 'r' + str(i)] + args)
            registers[i] = l[1]
    return asm

# пока по-простому: операция+присвоение -> инструкция
def to_asm(code):
    last_op = None
    last_op2 = None
    vars = {}
    new_code = []
    v_consts = {}
    consts = {}
    for l in code:
        # заменяем на in-place операции:
        #   v_invert t a
        #   v___floordiv__ a t
        # становится
        #   a_v_invert a
        # так как переменные используются только временно, то их мы
        # просто устраняем, ничего переименовывать не надо

        # if last_op2 != last_op:
        #     print >> sys.stderr, "    remembered op changed ===============>"
        #     print >> sys.stderr, "    ", last_op
        #     last_op2 = last_op
        # print >> sys.stderr, l

        if instructions[l[0]].return_type != 'void':
            vars[l[1]] = 'temporary'

        if l[0] == 'v_new_const':
            v_consts[l[1]] = l[2]
            # %% надо проверять, что эта константа используется из ассемблера
            l[0] = 'a_' + l[0]
            new_code.append(l)
        elif l[0] == 'new_const':
            consts[l[1]] = l[2]
            # %% надо проверять, что эта константа используется из ассемблера
            l[0] = 'a_' + l[0]
            new_code.append(l)
        elif l[0] == 'use_define':
            new_code.append(l)
        elif l[0] == 'v_new_var':
            # Default is memory.
            vars[l[1]] = 'memory'
        elif l[0] == 'in_memory':
            assert vars[l[1]] != 'register'
            vars[l[1]] = 'memory'
        elif l[0] == 'in_register':
            # %% хм, мы по умолчанию memory записали... можно сделать
            #  % неизвестный типа памяти
            # assert l[1] not in vars
            assert vars[l[1]] != 'register'
            vars[l[1]] = 'register'
        elif l[0] == 'v_input':
            new_code.append(l)
        elif l[0] == 'v_output':
            # new_code.append(['a_v_output', l[1]])
            new_code.append(l)
        elif l[0] == 'v_store':
            new_code.append(['a_v_store', l[1], l[2]])
        elif l[0] == 'v_print_var':
            l[0] = 'a_' + l[0]
            new_code.append(l)
        elif l[0] == 'v_load':
            assert last_op == None
            last_op = l
            # new_code.append(['a_v_load', l[1], l[2]])
        else:

            # проверяем, с чем работает инструкция: с переменными или
            # с регистрами; смешанный случай - ошибка; бывают
            # константы
            rk = 0
            mk = 0
            tk = 0
            # if instructions[l[0]].return_type == 'void':
            #     args = l[1:]
            # else:
            #     args = l[2:]
            args = l[1:]
            for e in args:
                if e in vars:
                    if vars[e] == 'register':
                        rk += 1
                    elif vars[e] == 'memory':
                        mk += 1
                    elif vars[e] == 'temporary':
                        tk += 1
                    else:
                        die('unimplemented')
            assert mk == 0 or rk == 0
            assert not (l[0] == 'v___floordiv__' and vars[l[1]] == 'register' and vars[l[2]] == 'memory')
            assert not (l[0] == 'v___floordiv__' and vars[l[1]] == 'memory' and vars[l[2]] == 'register')

            if l[0] == 'v___floordiv__' and vars[l[1]] == 'register' and vars[l[2]] == 'temporary':
                # print >> sys.stderr, 1
                if l[2] not in v_consts and l[2] not in consts:
                    assert last_op != None
                    # %% мы рассчитываем на то, что у операций подряд будет
                    #  % одна переменная
                    assert last_op[1] == l[2]
                    if last_op[0] == 'v_load':
                        # v_load becomes the op, not assignment
                        l[0] = 'a_v_load'
                        args = [l[1], last_op[2]]
                    elif last_op[0] == 'v_invert':
                        # v_invert becomes the op
                        l[0] = 'a_v_invert'
                    elif last_op[2] == l[1]:
                        args = last_op[2:]
                    else:
                        # %% в теории, это не обязано быть таким;
                        #  % порядок может быть другим
                        die('wrong bytecode')
                    # заменяем: в качестве аргументов идут аргументы операции
                    new_code.append(['a_' + last_op[0]] + args)
                else:
                    new_code.append(['a_' + l[0]] + l[1:])
                last_op = None
            elif l[0] == 'v___floordiv__' and vars[l[1]] == 'register' and vars[l[2]] == 'register':
                # print >> sys.stderr, 2
                l[0] = 'a_' + l[0]
                new_code.append(l)
            elif mk == 0 and rk == 0 and tk == 0:
                # print >> sys.stderr, 3
                new_code.append(l)
            elif mk > 0:
                # print >> sys.stderr, 4
                # переменная в памяти
                # %% проверка типа результата, если есть результат
                new_code.append(l)
            else:
            # elif rk > 0:
                # print >> sys.stderr, 5
                # переменная в регистре
                assert last_op == None
                last_op = l

        # конец обработки
        if len(new_code) > 0:
            ll = new_code[-1]
            if ll[0] == 'a_v___floordiv__' and ll[1] == 'sha256_registers3_var25' and len(ll) == 2:
                print >> sys.stderr, ">>>>>", ll

    var_defs = []
    for k, v in vars.iteritems():
        if v == 'register':
            var_defs.append(['a_v_new_register', k])
        elif v == 'memory':
            # var_defs.append(['v_new_var', k])
            var_defs.append(['a_v_new_var', k])
    return var_defs + new_code

def put_asm_borders(code):
    # %% there are no checks
    new_code = []
    asm = False
    def is_asm(op):
        return op not in ['a_v_new_register'] and (op.startswith('a_') or op in ['v_new_const', 'new_const', 'use_define'])
    for l in code:
        if is_asm(l[0]) and not asm:
            asm = True
            new_code.append(['a_begin'])
        if not is_asm(l[0]) and asm:
            asm = False
            new_code.append(['a_end'])
        new_code.append(l)
    return new_code

def rename_uniquely(code):
    rs = {}
    # dump(code, 'before.bytecode')
    for l in code:
        for i in range(1, len(l), 1):
            # Если элемент не в таблице замен и это не метка, то
            # запоминаем замену.
            if l[i] not in rs and instructions[l[0]].all_types[i] != 'label':
                rs[l[i]] = new_name()
            # Если элемент в таблице замен, то заменяем его на указанный.
            if l[i] in rs:
                l[i] = rs[l[i]]
    # dump(code, 'after.bytecode')
    # if 'b_var16356' in rs.values():
    #     exit(1)
    return code

def collect_outputs(code):
    outputs = []
    for l in code:
        if l[0] == 'output':
            outputs.append(l[1])
    return outputs

def vectorize_maybe(code):
    if global_vars['vectorize']:
        return vectorize(code)
    return code

def my_exit(code):
    exit(1)

# построение обратного алгоритма (для шифров)
def reverse_full(code):
    # %% it is simplistic
    assert code[0][0] == 'var_setup'
    # new_code = [code[0]]
    var_setup = code[0]
    new_code = []
    known = set()
    inputs = []
    outputs = []
    for l in code:
        if l[0] == 'input':
            inputs.append(l)
        if l[0] == 'output':
            outputs.append(l)
    remains = list(reversed(code[1:]))
    while len(remains) != 0:
        for l in remains:
            if l[0] == 'output':
                # print 'o', l
                known.add(l[1])
                # new_code.append(['input', l[1]])
                l[0] = drop
            elif l[0] == 'new_const':
                # print 'c', l
                known.add(l[1])
                new_code.append(list(l))
                l[0] = drop
            elif l[0] == 'input' and l[1] in known:
                # print 'i', l
                # new_code.append(['output', l[1]])
                l[0] = drop
            elif l[0] == 'input' and l[1] not in known:
                pass
            elif instructions[l[0]].return_type == 'void':
                not_implemented()
            elif instructions[l[0]].return_type != 'void' and all(a in known for a in l[2:]):
                # print 'fk', l
                if l[1] in known:
                    # We skip instruction if the result is already known
                    # (redundancy)
                    # %% Это означает, что мы можем выбрать путь, как
                    #  % получить это значения. Это может влиять на
                    #  % скорость. (Если, конечно, чистили от дублей.)
                    print >> sys.stderr, 'warning: redundancy', l
                else:
                    # Add it as is
                    new_code.append(list(l))
                    known.add(l[1])
                l[0] = drop
            elif l[0] not in ['__rshift__', '__lshift__'] and instructions[l[0]].return_type != 'void' and l[1] in known and [a in known for a in l[2:]].count(False) == 1:
                # %% сдвиги теряют информацию, но не всю, результат
                #  % обратного сдвига вполне можно использовать
                #  % частично, но это удобней делать с bitslice
                #  % реализацией (там это "бесплатно")
                # print 'nk1', l
                # строим обратное
                nk_idx = [a in known for a in l[2:]].index(False)
                nk = l[nk_idx + 2]
                k = l[(1 - nk_idx) + 2]
                if l[0] == '__add__':
                    new_code.append(['__sub__', nk, l[1], k])
                elif l[0] == '__xor__':
                    new_code.append(['__xor__', nk, l[1], k])
                else:
                    not_implemented()
                known.add(nk)
                l[0] = drop
            else:
                # we just postpone because we can't move  forward
                pass
        # shrink remaining
        new_remains = filter(lambda x: x[0] != drop, remains)
        if len(new_remains) == len(remains):
            # print
            # print 'not reversed yet:'
            # for r in remains:
            #     print r
            die("can't reverse")
        remains = new_remains
    preamble = [var_setup]
    for l in outputs:
        preamble.append(['input'] + l[1:])
    for l in inputs:
        new_code.append(['output'] + l[1:])
    return preamble + new_code

def check_types(code):
    ms, mt = extract_modules(code)
    ts = {}
    for m in ms:
        # %% можно было бы запоминать тип функции и потом проверять
        ts[m] = 'function'
    def tsame(t1, t2):
        # it is not symmetric: t1 from real instruction, t2 from spec
        return t1 == t2 or (t1 == 'const_num' and t2 == 'num')
    for l in code:
        if l[0] not in instructions:
            die('not in spec: {0}', l)
        inst = instructions[l[0]]
        if inst.return_type == 'void':
            res = None
            res_type = None
            args = l[1:]
        else:
            res = l[1]
            res_type = inst.return_type
            args = l[2:]
        if len(args) < len(inst.args):
            die('op is too short: {0}', l)
        if len(args) > len(inst.args) and (len(inst.args) == 0 or inst.args[-1][0] != '*'):
            die('op is too long: {0}', l)
        i_args = list(inst.args)
        if len(i_args) > 0:
            if i_args[-1][0] == '*':
                t = i_args[-1][1:]
                i_args[-1] = t
                while len(args) > len(i_args):
                    i_args.append(t)
        for i, a in enumerate(args):
            if i_args[i] == 'label':
                continue
            # проверяем, что у всех аргументов есть типы
            if a not in ts:
                die('type was not inferred for {1} in {0}', l, a)
            # проверяем, что аргументы соответствуют спецификации
            if ts[a] != i_args[i].lstrip('!') and not tsame(ts[a], i_args[i]):
                die('type is not right for {1} in {0}, have {3}, expected {2}', l, a, i_args[i], ts[a])
        # запоминаем тип для результата
        # %% было бы неплохо запоминать const_num, если операция от const_num
        ts[res] = res_type
    return code

# def change_inputs_for_functions(code):
#     f = 0
#     for l in code:
#         if l[0] == 'module_begin':
#             f += 1
#         if l[0] == 'module_end':
#             f -= 1
#         if f > 0 and (l[0].startswith('input') or l[0].startswith('output')):
#             l[0] = 'function_' + l[0]
#     return code

def fix_run_merkle_damgard(code, ifs = None):
    ifs = collect_ifs(code)
    # if ifs == None:
    #     ifs = collect_ifs(code)
    # m, mt = extract_modules(code)
    # main_code = m['_main']
    # for n in m:
    #     if n == '_main':
    #         continue
    #     m[n] = fix_run_merkle_damgard(m[n], ifs)
    # %% dirty
    # state = []
    # consts = {}
    new_code = []
    sizes = [None]
    # const_sizes = {}
    for l in code:
        if l[0] == 'var_setup':
            # %% support var_setup_pop; each module has to have its
            #  % own stack
            sizes[-1] = l
        elif l[0] == 'module_begin':
            sizes.append(None)
        elif l[0] == 'module_end':
            sizes.pop()
        # elif l[0] == 'new_const':
        #     consts[l[1]] = l[2]
        # elif l[0] == 'new_state_var':
        #     l[0] = 'input_state'
        #     c = consts[l.pop()]
        #     state.append(c)
        #     const_sizes[c] = sizes[-1]
        elif l[0] == 'run_merkle_damgard':
            l[0] = 'run_merkle_damgard_with_state'
            # put zero as offset for MD
            zero = new_name()
            new_code.append(['new_const', zero, '0'])
            l.append(zero)
            # pops = 0
            state = map(lambda x: x[1], ifs[l[2]]['state_var_names_values'])
            for v in state:
                # if const_sizes[v] != sizes[-1]:
                #     new_code.append(const_sizes[v])
                #     pops += 1
                #     sizes.append(const_sizes[v])
                l.append(put_const(new_code, v))
            # for i in range(pops):
            #     new_code.append(['var_setup_pop'])
            #     sizes.pop()
        new_code.append(l)
    # return pack_modules(new_code, m, mt)
    return new_code

def compute_hfun_sizes(code):
    # modules, modules_types = extract_modules(code)
    # main_code = modules['_main']
    ifs = collect_ifs(code)
    new_code = []
    for l in code:
        if l[0] == 'hfun_block_size':
            if l[2] in ifs:
                l[0] = 'new_const'
                i = ifs[l[2]]
                # print i
                # l[2] = str(i['inputs'] * i['size'])
                l[2] = str(i['hfun_block_size'])
            else:
                die('unknown func {1} in {0}', l, m)
        if l[0] == 'hfun_digest_size':
            if l[2] in ifs:
                l[0] = 'new_const'
                i = ifs[l[2]]
                # l[2] = str(i['outputs'] * i['size'])
                l[2] = str(i['hfun_digest_size'])
            else:
                die('unknown func {1} in {0}', l, m)
        if l[0] == 'invoke_hfun':
            # ** к 'invoke_fun2' это не применимо (не всегда)
            l[0] += '_with_size'
            i = ifs[l[2]]
            v = new_name()
            # new_code.append(['new_const', v, str(i['outputs'] * i['size'])])
            new_code.append(['new_const', v, str(i['hfun_digest_size'])])
            l.append(v)
        new_code.append(l)
    return new_code

def test_modules_packing(code):
    modules, mt = extract_modules(code)
    return pack_modules(modules['_main'], modules, mt)

def pack_modules(code, modules, modules_types):
    new_code = []
    for k in modules:
        if k == '_main':
            continue
        new_code.append(['module_begin', k] + modules_types[k])
        new_code += modules[k]
        new_code.append(['module_end', k])
    new_code += code
    return new_code

def flatten_modules(code):
    # We lift all modules to the top renaming.
    all_modules, all_modules_types = {}, {}
    # Очередь объектов кода для вытаскивания модулей
    modules, modules_types = extract_modules(code)
    main_code = modules['_main']
    q = [('_main', code, None)]
    while len(q) > 0:
        name, c, t = q.pop()
        modules, modules_types = extract_modules(c)
        for m in modules:
            if m == '_main':
                continue
            q.append((m, modules[m], modules_types[m]))
        assert name not in all_modules
        all_modules[name] = modules['_main']
        all_modules_types[name] = t
    return pack_modules(main_code, all_modules, all_modules_types)

# ** compute_hfun_sizes should be called before
# ** flatten_modules should be called before
def inline_function(code, fun_type, name):
    modules, modules_types = extract_modules(code)
    main_code = modules['_main']
    v = None
    for m, (t, n) in modules_types.items():
        if t == fun_type and n == name:
            if v != None:
                die('multiple definitions for hfun {0}', n)
            v = m
    if v == None:
        die('{0} {1} not found', fun_type, name)
    m2, mt2 = extract_modules(modules[v])
    vcode = m2['_main']
    # lift submodules
    # del m2['_main']
    # for k in m2:
    #     if k in modules:
    #         die('name collision in submodules')
    #     modules[k] = m2[k]
    #     modules_types[k] = mt2[k]
    # del modules[v]
    # insert the body
    new_code = []
    callers = {
        'hfun' : [ 'invoke_hfun_with_size', 'invoke_hfun' ],
        'plain' : [ 'invoke_plain' ],
    }
    plain_arrays = {}
    if fun_type == 'plain':
        # Collect unpacking of results of 'plain' functions
        for l in main_code:
            if l[0] == 'invoke_plain' and v == l[2]:
                plain_arrays[l[1]] = []
            elif l[0] == '__getitem__' and l[2] in plain_arrays:
                # ** We assume indexing to go straight
                plain_arrays[l[2]].append(l[1])
    for l in main_code:
        if l[0] == '__getitem__' and l[2] in plain_arrays:
            pass
        elif l[0].startswith('invoke_') and l[2] == v and l[0] in callers[fun_type]:
            assert l[0] != 'invoke_hfun'
            output_names = []
            plain_result_name = None
            # hfun_result_name = None
            if l[0] == 'invoke_hfun_with_size':
                hfun_result_name = l[1]
                input_key_name = l[3]
                size_name = l[4]
            elif l[0] == 'invoke_plain':
                plain_result_name = l[1]
                # input and state
                state_names = l[3:]
            substs = {}
            # находим выход и записываем ему имя сразу
            out_bytes_name = None
            input_names = []
            for l2 in vcode:
                if l2[0] == 'output_bytes':
                    assert out_bytes_name == None
                    out_bytes_name = l2[1]
                    substs[out_bytes_name] = hfun_result_name
                elif l2[0] == 'output':
                    output_names.append(l2[1])
                elif l2[0] == 'input':
                    c = state_names.pop(0)
                    input_names.append(c)
                    substs[l2[1]] = c
            if fun_type == 'plain':
                for i, o in enumerate(output_names):
                    substs[o] = plain_arrays[plain_result_name][i]
            # вставляем код функции
            for l2 in vcode:
                if l2[0] == 'input_key':
                    # в новом коде, вход - та переменная
                    substs[l2[1]] = input_key_name
                elif l2[0] == 'new_state_var':
                    substs[l2[1]] = state_names.pop(0)
                elif l2[0] in ['set_hfun_block_size', 'set_hfun_digest_size']:
                    pass
                elif l2[0] == 'output_bytes':
                    # replace_in_code(new_code, { l2[1]: res })
                    pass
                elif l2[0] in ['output', 'input']:
                    pass
                else:
                    t = list(l2)
                    if instructions[l2[0]].return_type != 'void' and l2[1] not in substs:
                        substs[l2[1]] = new_name()
                    replace_in_line(t, substs)
                    new_code.append(t)
            # if plain_result_name != None:
            #     # new_code.append(['new_array', plain_result_name, 'plain_fun_res'] + output_names)
            #     c = put_const(new_code, len(output_names))
            #     new_code.append(['make_array', plain_result_name, 'plain_fun_res', c])
            #     for i, r in enumerate(output_names):
            #         new_code.append(['set_item', plain_result_name, put_const(new_code, i), r])
            #         replace_in_line(new_code[-1], substs)
            # if need_pop:
            #     new_code.append(['var_setup_pop'])
        else:
            new_code.append(l)
    return pack_modules(new_code, modules, modules_types)

# def unroll_block_from_merkle_damgard(code):
#     new_code = []
#     ifs = collect_ifs(code)
#     lengths = collect_bytes_lengths(code)
#     for l in code:
#         if l[0] == 'run_merkle_damgard_with_state':
#             # print l
#             # print lengths[l[3]]
#             if lengths[l[3]] == 'unknown':
#                 new_code.append(l)
#                 continue
#             # вызываем compression function 1 раз с текущим состоянием
#             res = l[1]
#             fun = l[2]
#             offset_inc = ifs[fun]['inputs'] * ifs[fun]['size']
#             if lengths[l[3]] < offset_inc:
#                 new_code.append(l)
#                 continue
#             inp = l[3]
#             offset = l[4]
#             state = l[5:]
#             # готовим входы для вызова
#             in_k = ifs[fun]['inputs']
#             n = put_const(new_code, in_k)
#             zero = put_const(new_code, 0)
#             inp2 = new_name()
#             oi = put_const(new_code, offset_inc)
#             new_code.append(['bytes_slice', inp2, inp, zero, oi])
#             split_res = new_name()
#             new_code.append(['bytes_split_to_nums', split_res, inp2, n])
#             inps = put_array_parts(new_code, split_res, in_k)
#             # вызов
#             fres = new_name()
#             new_code.append(['invoke_plain', fres, fun] + inps + state)
#             # новое состояние
#             out_k = ifs[fun]['outputs']
#             outs = put_array_parts(new_code, fres, out_k)
#             # новый оффсет
#             new_offset = new_name()
#             new_code.append(['__add__', new_offset, offset, oi])
#             # длина данных
#             ll = new_name()
#             new_code.append(['bytes_len', ll, inp])
#             # новые данные
#             data = new_name()
#             new_code.append(['bytes_slice', data, inp, oi, ll])
#             # мд
#             new_code.append(['run_merkle_damgard_with_state', res, fun, data, new_offset] + outs)
#         else:
#             new_code.append(l)
#     return new_code

def unroll_block_from_merkle_damgard(code):
    new_code = []
    ifs = collect_ifs(code)
    lengths = collect_bytes_lengths(code)
    with L.evaluate_to(new_code):
        for l in code:
            if l[0] == 'run_merkle_damgard_with_state':
                # print l
                # print lengths[l[3]]
                if lengths[l[3]] == 'unknown':
                    new_code.append(l)
                    continue
                fun = l[2]
                offset_inc = ifs[fun]['inputs'] * ifs[fun]['size']
                if lengths[l[3]] < offset_inc:
                    new_code.append(l)
                    continue
                # вызываем compression function 1 раз с текущим состоянием
                res = l[1]
                inp = l[3]
                offset = l[4]
                state = l[5:]
                # с переменными
                vs = map(L.Var, l)
                fun_var = vs[2]
                inp_var = vs[3]
                offset_var = vs[4]
                state_vars = vs[5:]
                inp2 = L.bytes_slice(inp_var, 0, offset_inc)
                in_k = ifs[fun]['inputs']
                split_res = L.bytes_split_to_nums(inp2, in_k)
                inps = [split_res[i] for i in range(in_k)]
                fres = L.invoke_plain(fun_var, *(inps + state_vars))
                out_k = ifs[fun]['outputs']
                outs = [fres[i] for i in range(out_k)]
                new_offset = offset_var + offset_inc
                ll = L.bytes_len(inp_var)
                data = L.bytes_slice(inp, offset_inc, ll)
                L.run_merkle_damgard_with_state(fun_var, data, new_offset, *outs)
                # fix result name
                new_code[-1][1] = res
            else:
                new_code.append(l)
    return new_code

def unroll_merkle_damgard(code):
    new_code = []
    ifs = collect_ifs(code)
    lengths = collect_bytes_lengths(code)
    with L.evaluate_to(new_code):
        for l in code:
            if l[0] == 'run_merkle_damgard' and lengths[l[3]] != 'unknown':
                res_name = l[1]
                fun = l[2]
                inp = l[3]
                ll = lengths[inp]
                # %% we don't support other lengths
                if ll != 192:
                    print >> sys.stderr, 'Warning: skipped unroll md for len', ll
                    new_code.append(l)
                    continue
                # %% надо бы проверять размер
                i = ifs[fun]
                size = i['size']
                in_k = i['inputs']
                out_k = i['outputs']
                endianity = i['endianity']
                state_values = i['state_var_names_values']
                # %% we don't support partial words
                assert ll % size == 0
                # инты на входе
                count = ll / size
                arr_var = L.bytes_split_to_nums(L.Var(inp), count)
                arr = [arr_var[i] for i in range(count)]
                state = [L.new_const(int(v)) for n, v in state_values]
                # полные блоки
                i = 0
                while i + in_k <= count:
                    # вызываем
                    args = arr[i : i + in_k] + state
                    # def pp(*a):
                    #     print 'pp:', a
                    # L.invoke_plain = pp
                    r = L.invoke_plain(L.Var(fun), *args)
                    state = [r[t] for t in range(out_k)]
                    # переходим к следующему блоку
                    i += in_k
                in_ints = arr[i :]
                if len(in_ints) <= 16 - 3:
                    b = 0x80 << ((size - 1) * 8)
                    in_ints.append(L.new_const(b))
                    while len(in_ints) < 16 - 2:
                        in_ints.append(L.new_const(0))
                    if endianity == 'be':
                        in_ints.append(L.new_const(0))
                        in_ints.append(L.new_const(ll << 3))
                    else:
                        die('not implemented')
                else:
                    die('not implemented')
                r = L.invoke_plain(L.Var(fun), *(in_ints + state))
                state = [r[i] for i in range(out_k)]
                res = L.bytes_join_nums(*state)
                new_code[-1][1] = res_name
            else:
                new_code.append(l)
    return new_code

def compute_const_lengths(code):
    lengths = collect_bytes_lengths(code)
    for l in code:
        if l[0] == 'bytes_len' and lengths[l[2]] != 'unknown':
            l[0] = 'new_const'
            l[2] = str(lengths[l[2]])
    return code

def opt_bytes_concat_slice(code):
    consts = collect_consts(code)
    lengths = collect_bytes_lengths(code)
    parts = {}
    substs = {}
    for l in code:
        replace_in_line(l, substs)
        if l[0] == 'bytes_concat':
            parts[(l[1], 0, lengths[l[2]])] = l[2]
            parts[(l[1], lengths[l[2]], lengths[l[1]])] = l[3]
        elif l[0] == 'bytes_slice':
            args = (l[2], int(consts[l[3]]), int(consts[l[4]]))
            # print args, parts
            if args in parts:
                substs[l[1]] = parts[args]
                l[0] = drop
    return clean(code)

def opt_bytes_concat_split(code):
    consts = collect_consts(code)
    lengths = collect_bytes_lengths(code)
    sizes = collect_sizes(code)
    parts = {}
    parts_arrays = {}
    new_code = []
    for l in code:
        if l[0] == 'bytes_concat':
            parts[l[1]] = (l[2], l[3])
        elif l[0] == 'bytes_split_to_nums' and l[2] in parts:
            # %% предположительно "размер" массива - размер элементов,
            #  % надо бы проверять, что между нет изменения размера
            size = sizes[l[1]][0]
            assert lengths[l[2]] != 'unknown' and lengths[l[2]] % size == 0
            a, b = parts[l[2]]
            assert lengths[a] % size == 0 and lengths[b] % size == 0
            count1 = lengths[a] / size
            count2 = lengths[b] / size
            count = int(consts[l[3]])
            assert count1 + count2 == count
            n1 = new_name()
            c1 = put_const(new_code, count1)
            new_code.append(['bytes_split_to_nums', n1, a, c1])
            n2 = new_name()
            c2 = put_const(new_code, count2)
            new_code.append(['bytes_split_to_nums', n2, b, c2])
            parts_arrays[l[1]] = (n1, count1, n2, count2, count)
        elif l[0] == '__getitem__' and l[2] in parts_arrays:
            p = parts_arrays[l[2]]
            idx = int(consts[l[3]])
            if idx >= p[1]:
                l[2] = p[2]
                l[3] = put_const(new_code, idx - p[1])
            else:
                l[2] = p[0]
        new_code.append(l)
    return new_code

def opt_bytes_join_split(code):
    consts = collect_consts(code)
    lengths = collect_bytes_lengths(code)
    joined = {}
    split = {}
    new_code = []
    substs = {}
    for l in code:
        if l[0] == 'bytes_join_nums':
            joined[l[1]] = l[2:]
        elif l[0] == 'bytes_split_to_nums' and l[2] in joined:
            split[l[1]] = joined[l[2]]
        elif l[0] == '__getitem__' and l[2] in split:
            substs[l[1]] = split[l[2]][int(consts[l[3]])]
            l[0] = drop
        new_code.append(l)
    replace_in_code(new_code, substs)
    return clean(new_code)

def lift_from_cycle(code, name):
    idx1, idx2 = find_cycle(code, name)
    new_code = code[ : idx1]
    body = code[idx1 + 1 : idx2]
    track = {}
    to_append = []
    for l in body:
        # %% set_item and __floordiv__
        if l[0] == 'bytes_assign':
            track[l[1]] = 1
    for l in body:
        if l[0] == 'new_bytes':
            del track[l[1]]
    new_body = []
    for l in body:
        if instructions[l[0]].return_type != 'void':
            for k in track.keys():
                if k in l:
                    track[l[1]] = 1
        if any(k in l for k in track):
            new_body.append(l)
            continue
        if instructions[l[0]].return_type != 'void' and l[1] not in track:
            new_code.append(l)
        elif l[0].startswith('print_'):
            new_body.append(l)
        elif l[0] == 'bytes_assign':
            new_code.append(l)
        elif instructions[l[0]].return_type != 'void' and l[1] in track:
            new_body.append(l)
        elif l[0].startswith('if_'):
            new_code.append(l)
        elif l[0] in ['var_setup', 'assume_length']:
            new_code.append(l)
        else:
            die('unhandled: {0}', l)
    new_code.append(code[idx1])
    new_code += new_body
    new_code += code[idx2 : ]
    return new_code

# pattern consists of matchers:
# list represents a line of
#   number: 1 - single variable, 0 - any number of variables,
#   string: explicit string,
#   dict: named placeholder for variable or many variables;
# string represents a line with such op and any args;
# dict: group or 'any of' matcher;
# See pattern_functions list.
#
# callback gets a dictionary with matched values and returns new list
# with ops
# %% return None to abort this match-replace
def replace_pattern(code, pattern, fun):
    # Жадный матчинг: если совпадает текущий кусок, то мы берём
    # максимум, пока совпадает.
    # Оптимистичный матчинг: если совпало начало, значит, весь паттерн
    # должен совпасть.
    # %% ролбеки?
    # Упрощаем паттерн: группы разбиваем на отдельные строки, числа
    # заменяем на словари без имени.
    np = []
    m = 'm'
    n = 'n'
    # Repack lines
    for l in pattern:
        if type(l) == dict and l['type'] == 'group':
            # %% можно тут ломаться, если имена повторяются
            for ll in l['matchers']:
                np.append({ n : l['name'], m : ll })
        elif type(l) == dict and l['type'] == 'many_any':
            np.append({ n : None, m : l })
        elif type(l) == list:
            np.append({ n : None, m : l })
    # Repack in lines
    for l in np:
        if type(l[m]) == list:
            for i, v in enumerate(l[m]):
                if type(v) == int:
                    assert v == 0 or v == 1
                    if v == 0:
                        l[m][i] = pattern_many_vars(None)
                    elif v == 1:
                        l[m][i] = pattern_var(None)
        elif type(l[m]) == str:
            l[m] = [ l[m], pattern_many_vars(None) ]
    # for l in np:
    #     print l
    d = {}
    def match(pattern_line, code_line):
        name = pattern_line[n]
        p = pattern_line[m]
        def handle_matched_line():
            if name != None:
                if name not in d:
                    d[name] = []
                d[name].append(code_line)
        if type(p) == dict:
            assert p['type'] == 'many_any'
            # %% only lines are supported now
            if code_line[0] in p['matchers']:
                handle_matched_line()
                return 0, 1
            else:
                # not matched, but it is ok, we did not handle line though
                return 1, 0
        else:
            assert type(p) == list
            for i, v in enumerate(p):
                # if v != 'cycle_range':
                #     print '>>', i, v
                if type(v) == str:
                    if v != code_line[i]:
                        return None
                elif type(v) == dict:
                    if v['type'] == 'var':
                        if v['name'] != None:
                            assert v['name'] not in d
                            d[v['name']] = code_line[i]
                    elif v['type'] == 'reference':
                        if d[v['name']] != code_line[i]:
                            return None
                    elif v['type'] == 'many_vars':
                        # %% we can't handle many vars in middle
                        assert i == len(p) - 1
                        if v['name'] != None:
                            d[v['name']] = code_line[i:]
            handle_matched_line()
            return 1, 1
    pi = 0
    ci = 0
    beginning = []
    while ci < len(code):
        r = match(np[pi], code[ci])
        if r == None:
            beginning.append(code[ci])
            ci += 1
        else:
            pi += r[0]
            ci += r[1]
            break
    if r == None:
        die('not matched 1')
        return code
    while pi < len(np) and ci < len(code):
        r = match(np[pi], code[ci])
        # print
        # for i, v in d.iteritems():
        #     if len(i) <= 3:
        #         print 'd:', i, v
        # print 'pattern:', np[pi]
        # print 'code:', code[ci]
        # print 'result:', r
        if r == None:
            die('not matched 2')
        pi += r[0]
        ci += r[1]
    r = beginning + fun(d) + code[ci :]
    return r

def split_bytes_pbkdf2(code):
    name = 'rounds'
    g, v, r, vs, lines = pattern_functions
    consts = collect_consts(code)
    pattern = [
        g('begin', [ 'cycle_range', 1, name, 0 ]),
        g('split', [ 'bytes_split_to_nums', v('arr'), v('b4'), v('count') ]),
        g('items', lines('__getitem__')),
        g('calls', lines('invoke_plain', '__getitem__')),
        [ 'bytes_join_nums', v('b1'), vs('ns1') ],
        [ 'bytes_xor', v('b2'), v('b3'), r('b1') ],
        [ 'bytes_assign', r('b4'), r('b1') ],
        [ 'bytes_assign', r('b3'), r('b2') ],
        g('end', [ 'cycle_end', name ])
    ]
    def replacement(m):
        new_code = []
        arr = L.Var(m['arr'])
        b4_vs = []
        # b4's count is same as of all byte strings in question.
        count = int(consts[m['count']])
        with L.evaluate_to(new_code):
            b3_vs = [L.new_var() for i in range(count)]
            b3_arr = L.bytes_split_to_nums(L.Var(m['b3']), count)
            for i in range(count):
                b3_vs[i] // b3_arr[i]
            b1_vs = map(L.Var, m['ns1'])
            new_code += m['split']
            for i in range(count):
                r = arr[i]
                v = m['items'][i][1]
                new_code.append(['new_var', v])
                v = L.Var(v)
                v // r
                b4_vs.append(v)
            new_code += m['begin']
            new_code += m['calls']
            # We replace b3^b1 with xor of each num in b3_vs and ns1
            # %% mix it in single cycle?
            b2_vs = [i ^ j for i, j in zip(b3_vs, b1_vs)]
            for i, j in zip(b2_vs, b3_vs):
                j // i
            for i, j in zip(b4_vs, b1_vs):
                i // j
            new_code += m['end']
            r = L.bytes_join_nums(*b3_vs)
            # new_code[-1][1] = m['b3']
            L.bytes_assign(L.Var(m['b3']), r)
        return new_code
    new_code = replace_pattern(code, pattern, replacement)
    return new_code

# Late imports, they use this file on their own, keep it in the end
from bytecode_bitslice import bitslice
from bytecode_interpreter import interpret
