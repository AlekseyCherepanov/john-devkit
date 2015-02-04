# -*- coding: utf-8 -*-
# библиотека для работы с "байткодом"

# %% clean imports
import sys
import os
import re
import pickle

# http://stackoverflow.com/questions/967443/python-module-to-shellquote-unshellquote
try:
    from shlex import quote
except ImportError:
    from pipes import quote

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
    pipe = os.popen('python {1} ../john-devkit-dirty/lang{2}_main.py < ../john-devkit-dirty/algo_{0}.py {3} > {0}.bytecode && cat {0}.bytecode'.format(name, tracer_options if use_tracer else '', '_bs' if use_bitslice else '', args_str))
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
    # input_string\d+
    # const\d+
    # input\d+
    # state\d+
    # однако, если мы добавляем префикс, то сначала может быть
    # префикс
    #
    # мне нужна замена на месте
    for l in c:
        for i in range(len(l)):
            if re.match('(var|input_string|const|input|state)\d+$', l[i]):
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
        if l[0] == 'declare' and len(l) == 4:
            names[l[1]] = names_a.pop(0)
            l[0] = drop
        for i in range(len(l)):
            if l[i] in names:
                l[i] = names[l[i]]
        a.append(l)
    # %% проверка, что все имена использованы
    return clean(a)

