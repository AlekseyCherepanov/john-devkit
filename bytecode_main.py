# -*- coding: utf-8 -*-
# библиотека для работы с "байткодом"

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

# %% clean imports
import sys
import os
import re
import pickle

import random
# RNG = random.SystemRandom()

from lang_spec import instructions

# http://stackoverflow.com/questions/967443/python-module-to-shellquote-unshellquote
try:
    from shlex import quote
except ImportError:
    from pipes import quote

global_vars = {}

def get_code(name, use_tracer, use_bitslice, args={}):
    # %% needs a patched trace.py that outputs to stderr, may bypass
    # it prefixing bytecode lines to distinguish them from tracer's
    # output
    # %% capture output of tracer
    args_str = quote(pickle.dumps(args))
    decor = ("#" * 15) + " {0} " + ("#" * 15)
    tracer_options = '-m trace --ignore-dir=/usr -t'
    print >> sys.stderr, decor.format('BEGIN OF {0}'.format(name))
    # %% remove temporary file and `cat`, or make as an option for debug
    pipe = os.popen('python {1} ../john-devkit-dirty/lang_main.py < ../john-devkit-dirty/algo_{0}.py {3} > {0}.bytecode && cat {0}.bytecode'.format(name, tracer_options if use_tracer else '', '_bs' if use_bitslice else '', args_str))
    output = pipe.read()
    print >> sys.stderr, decor.format('END OF {0}'.format(name))
    c = pipe.close()
    if c and c > 0:
        # print >> sys.stderr, "hi there << {0}".format(c)
        # ** c may be 256
        exit(1)
    return output

def get_code_full(name, use_tracer, use_bitslice, args={}):
    temp = get_code(name, use_tracer, use_bitslice, args)
    temp = split_bytecode(temp)
    add_prefix(temp, name)
    return temp

# режем код на части
def split_bytecode(c):
    return [l.split(' ') for l in c.split('\n') if l != '']

def print_bytecode(c):
    print "\n".join(" ".join(l) for l in c)

# мы можем сливать, заменяя или давая новые определения;
# при слиянии у нас будут конфликты имён, хорошо бы к именам добавлять
# префиксы
# %% автоматом давать префиксы при загрузке байткода?
def add_prefix(c, prefix):
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

def dump(code, filename):
    with file(filename, 'w') as f:
        for i in code:
            # Мы всё приводим к строкам
            # %% хорошо бы проверять, что мы получили строку или число
            f.write(" ".join(i))
            f.write("\n")
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
get_from_key_0x80_padding_length

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

# get_length

# cycle_const_range
# cycle_range
# cycle_while_begin
# cycle_while
# cycle_end

# label
# goto

# digest_to_string
# fill_string

# if_condition
# if_else
# if_end

# init
# update
# final

# put0x80
# get_int
# get_int_raw
# put_int

# string_copy_and_extend
# free

set_item
make_array

print_buf
print_var
print_digest

swap_to_be

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
def compute_const_expressions(code):
    consts = {}
    for l in code:
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
    # %% вообще, это можно было бы делать в один проход
    new_code = []
    for l in code:
        if l[0] == '__sub__' and l[2] in consts and l[3] in consts:
            l[0] = 'new_const'
            l[2] = str(int(consts[l[2]]) - int(consts[l[3]]))
            del l[3]
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
            if n:
                n[0] = drop
    code = clean(code)
    return code

class BGlobal():
    pass
g = BGlobal()
g.const_count = 0

def new_const(value):
    g.const_count += 1
    n = 'bconst_var' + str(g.const_count)
    return ['new_const', n, str(value)]

def new_name():
    g.const_count += 1
    n = 'b_var' + str(g.const_count)
    return n

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

def deep_copy(code):
    return list(list(l) for l in code)

# функция замены всех частей на строки
def alltostr(code):
    r = code
    packs = [code]
    if type(code) == dict:
        packs = code.values()
    # Заменяем на месте
    for p in packs:
        # deep copy each pack (code object)
        p = deep_copy(p)
        for l in p:
            # print >> sys.stderr, l
            for i in range(len(l)):
                # %% нужна проверка, что там только числа и строки
                l[i] = str(l[i])
            # print >> sys.stderr, l
    return r

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
    for f in forms:
        # Если не список и не кортеж, то это bare function,
        # оборачиваем в список.
        if type(f) != list and type(f) != tuple:
            f = [f,]
        print >> sys.stderr, f[0]
        # После каждого прохода заменяем всё на строки
        # %% Это такой глобальный костыль, чтобы можно сохранять числа
        #  % в массив
        # %% Это должно быть медленно
        res = deep_copy(res)
        res = f[0](res, *f[1:])
        res = alltostr(res)
        # Если получили словарь и наш словарь - словарь по
        # умолчанию, то мы замещаем словарь на новый.
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

def bitslice(code, bs_bits, size):
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
            for i in reversed(range(bs_bits)):
                if i == bs_bits - 1:
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
    for l in code:
        if l[0] == 'output':
            outputs_array.append(l[1])
    code.append(['check_output', outputs_array[output_number]])
    return { 'code': code, 'reverse': reverse_code }

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
