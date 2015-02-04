# -*- coding: utf-8 -*-
# временный скрипт для начала работы с sha512
# bit-slice версия

import sys
import os
from string import Template

import re

def warn(args):
    print >> sys.stderr, args

def get_code(name):
    # %% needs a patched trace.py that outputs to stderr, may bypass
    # it prefixing bytecode lines to distinguish them from tracer's
    # output
    # %% capture output of tracer
    decor = ("#" * 15) + " {0} " + ("#" * 15)
    # use_tracer = False
    # use_tracer = True
    use_tracer = sys.argv[1] == "t"
    tracer_options = '-m trace --ignore-dir=/usr -t'
    print >> sys.stderr, decor.format('BEGIN OF {0}'.format(name))
    # %% remove temporary file and `cat`, or make as an option for debug
    # pipe = os.popen('python {1} lang_bs_main.py < algo_{0}.py'.format(name, tracer_options if use_tracer else ''))
    pipe = os.popen('python {1} lang_bs_main.py < algo_{0}.py > {0}.bytecode && cat {0}.bytecode'.format(name, tracer_options if use_tracer else ''))
    output = pipe.read()
    print >> sys.stderr, decor.format('END OF {0}'.format(name))
    c = pipe.close()
    if c and c > 0:
        # print >> sys.stderr, "hi there << {0}".format(c)
        # ** c may be 256
        exit(1)
    return output

sha512 = get_code('sha512')
padding = get_code('padding')

# # вывод "байткода"
# print sha512
# print padding

# режем код на части
def split_bytecode(c):
    return [l.split(' ') for l in c.split('\n') if l != '']
sha512 = split_bytecode(sha512)
padding = split_bytecode(padding)

def print_bytecode(c):
    print "\n".join(" ".join(l) for l in c)

# сливаем вместе куски: выходы padding'а становятся входами sha512
#
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
add_prefix(padding, 'padding')
add_prefix(sha512, 'sha512')
# %% предполагаем, что нет конфликтов имён
# может менять параметры
# %% drop line - неплохо имя, так как разбивка по пробелам
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
code = join_parts(padding, sha512)

class Global:
    pass
g = Global()

g.code = ''

# функция добавления кода в глобальную строку
def c(code, *args):
    g.code += code.format(*args) + "\n"

# все константы и переменные состояния можно сделать дефайнами
def out_const(code):
    for l in code:
        if l[0] == 'const' or (l[0] == 'declare' and len(l) == 5):
            c('#define {0} {1}ULL', l[1], l[2])
            l[0] = drop
    return clean(code)

g.out_names = []
g.bit_lengths = {}
g.bit_length_bits = []

def partition(l, n):
    if len(l) % n != 0 or n < 1:
        raise Exception('bad array for partition')
    return zip(*[iter(l)] * n)

def print_bs(args):
    # c('printf("out:");')
    # %% compute 64
    for i in range(len(args) / 64):
        # собираем биты от 64 чисел
        c('printf(" %016llx", {0});', " | ".join("(({0} & 1) << (64 - 1 - {1}))".format(args[i * 64 + j], j) for j in range(64)))
    c('printf("\\n");')

def out_all(code):
    c('size_t i, len;')
    for l in code:
        if l[0] == 'op':
            # op sha512_var634 sha512_var632 sha512_var633 ^
            # if l[4] == 'bit_length':
            #     c('size_t {0} = strlen({1}) * 8;', l[1], l[2])
            #     c('printf(">> %016llx\\n", {0});', l[1])
            # el
            if l[4] == 'to_be':
                # to big endian
                # %% быстрее
                # %% использовать переменную?
                # %% почему это не нужно?
                #c('#define {0} ({1})', l[1], " | ".join('((({1} & (0xff << ({0} * 8))) >> ({0} * 8)) << ((8 - {0} - 1) * 8))'.format(i, l[2]) for i in range(8)))
                c('#define {0} {1}', l[1], l[2])
                c('printf(">>> %016llx\\n", {0});', l[1])
            elif l[4] == 'noop':
                # %% другие типы, параметризация этого
                # %% описание типов у операций
                c('unsigned long long {0};', l[1])
            elif l[4] == '~':
                c('unsigned long long {0} = {3}{1};', *l[1:])
            # elif l[4] == 'getitem':
            #     c('unsigned long long {0} = {1}[{2}];', *l[1:])
            elif l[4] == 'ror' or l[4] == 'rol':
                c('unsigned long long {0} = {3}({1}, {2});', *l[1:])
            else:
                c('unsigned long long {0} = {1} {3} {2};', *l[1:])
        elif l[0] == 'declare_string':
            # declare_string padding_input_string0
            # %% это заглушка для связи, нужна параметризация
            c('#define {0} (argv[1])', l[1])
        elif l[0] == 'string_get_ints_with_bit_on_the_end':
            # # string_get_ints padding_input_string0 be 8 14 padding_var2 ...
            # # %% быстрее?
            # # %% опять тип
            # # %% обработка того же эндианнесса
            # # %% проверка, что типы совпадают заявленному
            # names = l[5:]
            # s = l[1]
            # c('len = strlen({0});', s)
            # for i, n in enumerate(names):
            #     # %% optimize strlen with already used op-strlen
            #     # %% optimize
            #     c('''
            #     for (i = 0; i < 8; i++) {{
            #         ((char *)&{0})[8 - i - 1] = (8 * {2} + i < len ? {1}[8 * {2} + i] : 0);
            #     }}''', n, s, i)
            #     # c('printf(">> %016llx\\n", {0});', n)
            # # в конец цепляем бит
            # # %% реализовать
            # # c('((char *)&{0})[0] = 0x80;', names[0])
            # c('((char *)&{0})[0] = 0x80;', names[13])
            # c('printf("{0}\\n", {1});', ' '.join(('%016llx',) *
            # len(names)), ', '.join(names))
            # раскладываем на биты
            string = l[1]
            number = l[4]
            # двумерный массив: [число1:[бит1,бит2...], ...]
            # %% compute 64
            c('len = strlen({0});', string)
            names = partition(l[5:], 64)
            for i, ns in enumerate(names):
                for j, n in enumerate(ns):
                    # для каждого бита в каждом числе берём бит из
                    # строки
                    # %% несколько строк
                    # %% длина
                    # %% compute 64
                    # %% optimize
                    c('''
                    if ({2} * 64 + {3} < len * 8) {{
                        {0} = (((unsigned long long *){1})[{2}] & (1ULL << (64 - ((7 - {3} / 8) * 8 + {3} % 8) - 1))) >> (64 - ((7 - {3} / 8) * 8 + {3} % 8) - 1);
                    }} else {{
                        {0} = ({2} * 64 + {3} == len * 8);
                    }}
                    ''', n, string, i, j)
            print_bs(l[5:])
        elif l[0] == 'comment':
            # %% does name substitution on merging work for comments?
            c('/* {0} */', " ".join(l[1:]))
            if l[1] == 'input:':
                c('printf("input: {0}\\n", {1});', ' '.join(('%016llx',) * len(l[2:])), ', '.join(l[2:]))
        elif l[0] == 'array':
            # array array_w padding_var2 padding_var3 ...
            # %% type again, derive it from variables
            # %% compute 64
            c('unsigned long long {0} [][64] = {{ {{ {1} }} }};', l[1], "}, {".join(', '.join(v) for v in partition(l[2:], 64)))
        elif l[0] == 'assign':
            # assign sha512_var624 sha512_state0
            c('{0} = {1};', l[1], l[2])
        elif l[0] == 'cycle_const_range':
            # cycle_const_range cyclevar0 main 0 79 1
            c('size_t {0};\n for ({0} = {1}; {0} <= {2}; {0} += {3}) {{',
              l[1], l[3], l[4], l[5])
        elif l[0] == 'cycle_end':
            # cycle_end main
            # %% use cycle name
            c('}}')
        elif l[0] == 'output':
            # output sha512_var661
            g.out_names.append(l[1])
        elif l[0] == 'bit_length':
            # bit_length padding_var0 padding_input_string0 0
            # для взятия длины у нас много операций идёт, каждая даёт
            # 1 бит, номер бита задан в конце
            # %% compute 64
            # однако размер надо вычислять один раз только, для этого
            # нам нужен хеш, кого мы уже определили
            if l[2] not in g.bit_lengths:
                # Мы будем использовать <имя_строки>_bit_length для
                # именования переменной с её длиной в битах.
                g.bit_lengths[l[2]] = l[2] + '_bit_length';
                c('size_t {0}_bit_length = strlen({0}) * 8;', l[2])
            # %% вот тут у нас в одну переменную должны собираться от
            # нескольких строк биты, сейчас только первый; строки
            # имеют одно имя
            # Здесь обработка не такая же, как для ввода.
            c('unsigned long long {0} = ({1}_bit_length & (1ULL << {2})) >> {2};', *l[1:])
            g.bit_length_bits.append(l[1])
            if len(g.bit_length_bits) % 64 == 0:
                print_bs(g.bit_length_bits)
                g.bit_length_bits = []
        elif l[0] == 'debug_print_var':
            v = l[1:65]
            comment = " ".join(l[65:])
            # %% quoting
            c('printf("%s:", "{0}");', comment)
            print_bs(v)
        elif l[0] == 'getitem':
            c('unsigned long long {0} = {1}[{2}][{3}];', *l[1:])
        else:
            raise Exception("unknown instruction [{0}]".format(", ".join(l)))

code = out_const(code)

# print_bytecode(code)

out_all(code)

# %% стоит вынести ror/rol, стоит раскрывать в другие операции
code_template = Template("""
#include <stdio.h>
#include <string.h>

int main(int argc, const char ** argv)
{
    if (argc < 1)
        return 1;

#define ror(a, b) (((a) << (sizeof(a)*8 - (b))) | ((a) >> (b)))
#define rol(a, b) (((a) >> (sizeof(a)*8 - (b))) | ((a) << (b)))

    $code

    return 0;
}
""")
# %% вывод со вставкой имён
# %% эндианнес при выводе?


c('printf("{0}\\n", {1});', ' '.join(('%016llx',) * len(g.out_names)), ', '.join(g.out_names))

print_bs(g.out_names)

# c('printf(">> %d\\n", sizeof(unsigned long long));')
# c('printf(">> %llx\\n", 0x428a2f98d728ae22);')
# c('printf(">> %llx\\n", 0x428a2f98d728ae22ULL);')

print code_template.safe_substitute(code = g.code)
