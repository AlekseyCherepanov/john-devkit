# -*- coding: utf-8 -*-
# библиотека для вывода кода в скалярный си
# в отдельный файл или в формат для джона

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

# аргументы сгенерированного бинарника: key salt rounds

import sys

import re

from string import Template
from bytecode_main import drop, clean

import bytecode_main as B
# import output_c as O

size_type = {
    # %% generate asserts to enforce assumptions, or use uint64_t and similar
    8: 'unsigned long long',
    # 8: 'int',
    4: 'unsigned int'
}
size_format_x = {
    8: '%016llx',
    4: '%08x'
}
size_format_u = {
    8: '%016llu',
    4: '%08u'
}
size_suffix = {
    8: 'ULL',
    4: 'U'
}

# %% __m128i and other types
bs_size_type = {
    64: 'unsigned long long'
}


def not_implemented():
    raise Exception('not implemented')

def bad_instruction():
    raise Exception('bad instruction (see backtrace)')

class Global:
    c_output = None
    def __init__(self):
        self.reset()
        # bs_size должен 0 по умолчанию, чтобы в код можно было делать
        # проверки, типа #if $bssize, указывали на использование
        # битслайса; к тому же без инициализации должно быть
        # исключение о неизвестном поле, если не был вызван
        # apply_bs_size, который отнюдь не всегда нужен
        # ** размеры не сбрасываются при .reset()
        self.bs_size = 0
        self.bs_o_type = None
        # ** обычные размеры должны быть установлены вручную всегда
    def reset(self):
        self.code = ''
        self.const_code = ''
        self.funcs_code = ''
        self.output_names = []
        self.quick_output_names = []
        self.input_bs_names = []
        self.output_bs_names = []
        self.bit_lengths = {}
        self.bit_length_bits = []
        self.cycles = {}
        self.use_define = [False]
        # %% надо переименовать inputs в input_names
        self.inputs = []
        # словарь определений переменных: тип => { имя => 1, имя => 1 }
        self.var_definitions = {}
        # словарь для трекания состояния инструкции get_from_padded_string
        # имя строки -> массив имён
        self.padded_strings = {}
        # self.lengths = { '_count': 0 }
        self.types = {}

g = Global()

Global.c_output = g

# %% мы можем перенаправить вывод из c(), однако размеры и всё такое
# будет в g
funcs = Global()

# функция добавления кода в глобальную строку
def c(code, *args):
    Global.c_output.code += code.format(*args) + "\n"

def c_prepend(code, *args):
    Global.c_output.code = code.format(*args) + "\n" + Global.c_output.code

# функция вывода один раз
written_once = {}
def c_once(code, *args):
    o = code.format(*args)
    if o not in written_once:
        written_once[o] = 1
        c(o)

# функция вывода кода практически в начало файла
def c_const(code, *args):
    Global.c_output.const_code += code.format(*args) + "\n"

# враппер для присваиваний, которые можно выразить define'ом
def a(code, *args):
    # %% проверить, что есть точка с запятой в конце
    left, right = code[:-1].split(' = ')
    # Ещё и тип выделяем.
    p = left.rindex(' ')
    t = left[:p]
    name = left[p + 1:]
    # print >>sys.stderr, code, '---', [name, t, right]
    if Global.c_output.use_define[0]:
        c('#define {0} ({1})'.format(name, right), *args)
    else:
        # %% ммм, name == '{0}', так что берём первый args, проверки?
        def_var(t, args[0])
        c('{0} = {1};'.format(name, right), *args)

# %% вообще, у нас есть разные размеры: размер в алгоритме, это влияет
# на ввод, вывод и арифметику, размер чисел в операциях, размер чисел
# при выводе, у нас может 8 байтовый ввод, который режется на биты и
# укладывается в 128-битные вектора для вычислений; это надо
# различать; размер констант для сдвига может быть другим, это может
# быть удобно для некоторых векторных инструкций, да и вообще,
# алгоритм может использовать несколько типов (как sunmd5)

def apply_size(size):
    g.size = size
    g.o_type = size_type[size]
    g.o_format_x = size_format_x[size]
    g.o_format_u = size_format_u[size]
    g.o_suffix = size_suffix[size]
    g.bits = size * 8
    g.vsize = 16 / size

# Endianness / endianity setup
def apply_endianity(endianity):
    assert endianity in ['le', 'be']
    g.endianity = endianity
    if endianity == 'be':
        g.need_input_swap = 1
    else:
        g.need_input_swap = 0

# %% bs_size - в битах, size - в байтах, не очень хорошо
def apply_bs_size(bs_size):
    g.bs_size = bs_size
    g.bs_o_type = bs_size_type[bs_size]

def partition(l, n):
    if len(l) % n != 0 or n < 1:
        raise Exception('bad array for partition')
    return zip(*[iter(l)] * n)

def print_bs(args):
    # c('printf("out:");')
    for i in range(len(args) / g.bits):
        # собираем биты от bits чисел
        c('printf(" $formatx", {0});', " | ".join("(({0} & 1) << ($bits - 1 - {1}))".format(args[i * g.bits + j], j) for j in range(g.bits)))
    c('printf("\\n");')

# init / update / final interface

def load_iuf(algo):
    # %% sha512 only so far
    code = B.get_code_full('sha512', **args)
    padding = B.get_code_full('padding', **args)
    code = B.join_parts(padding, code)
    # We already applied size.
    # %% то есть мы не можем иметь вызов sha256 и sha512 разом?
    # O.apply_size(size)


# %% хм, может быть сокращено до форматной строки на имя, кроме
#  % new_array, где join используется

# %% стоит делать проверку аргументов на тип

# одна переменная может быть описана несколько раз, реально она будет
# описана только один раз
def def_var(t, var):
    # # No definition if we use define to express assignment
    # if Global.c_output.use_define[0]:
    #     return
    if True:
        # Declaration go before the code
        if t not in g.var_definitions:
            g.var_definitions[t] = {}
        g.var_definitions[t][var] = 1
    else:
        # In-place declarations
        c('{0} {1} $align;', t, var)

def def_var_default(var):
    def_var('$type', var)
def def_var_vector(var):
    def_var('__m128i', var)

def gen_var_defs():
    for i in g.var_definitions:
        vs = g.var_definitions[i]
        # c_prepend('{0} {1} $align;', i, " $align, ".join(vs.keys()))
        c_prepend('{0} {1};', i, ", ".join("{0} $align".format(v) for v in vs.keys()))



# ######################################################################
# b_* - definitions of functions to handle each bytecode instruction.
# b_v_* - vectorized, has its own section

def b_print_verbatim(hexed):
    c('printf("pv: %s\\n", "{0}");', ''.join('\\x' + hexed[i * 2 : i * 2 + 2] for i in range(len(hexed) / 2)))

def b_use_define(label):
    # %% parity?
    if label == 'yes':
        Global.c_output.use_define.insert(0, True)
    else:
        Global.c_output.use_define.pop(0)

def b_new_const(name, value):
    # %% handle $suffix according to output type, not algo's type
    c('#define {0} {1}$suffix', name, value)
    # c_const('#define {0} {1}$suffix', name, value)

def b_new_var(name):
    # c('$type {0};', name)
    def_var_default(name)

def b_new_state_var(name, value):
    # Если состояние добралось до раскрытия, то это значит, что мы не
    # использовали его в качестве входа, так это просто константа. Но
    # аргумент для функции уже был обработан, как константа. Так что
    # просто даём новое имя.
    c('#define {0} {1}', name, value)

def b_new_array(name, label, *values):
    # c('$type {0}[{1}] = {{ {2} }};', name, len(values), ", ".join(values))
    c('$type {0}[] = {{ {1} }};', name, ", ".join(values))

def b_make_array(name, label, size):
    c('$type {0}[{1}];', name, size)

def b_input_rounds(name):
    # %% is atoi good?
    a('$type {0} = atoi(argv[3]);', name)

# def b_input_key(name):
#     types[name] = 'string'
#     if Global.c_output is g:
#         c('#define {0} (argv[1])', name)
#         # c('#define {0} ((const char *)saved_key[index/MMX_COEF_SHA512 + myindex])', name)
#     elif Global.c_output is funcs:
#         c('#define {0} (state->buf)', name)
#     else:
#         not_implemented()

def b_input_key(name):
    g.types[name] = 'string'
    # c('#define {0} (($type *)(saved_key[index]))', name)
    c('#define {0} (saved_key[index])', name)

def get_from_padded_string(name, string):
    # Выводим код для копирования из буфера в переменную
    # c('#define {0} (JOHNSWAP64((($type*)saved_key[index])[{1}]))',
    c('#define {0} (JOHNSWAP$bits(p[{1}]))',
      name, len(g.padded_strings[string]))
    g.padded_strings[string].append(name)

# совмещённая функция для добавления 0x80, паддинга и записи
# длины в конец, для sha2;
# одна инструкция - один выходной инт, так что можно собрать всё и
# потом вывести; или вначале разобрать в буфер, а потом уже раздавать
def b_get_from_key_0x80_padding_length(name, string):
    # Проверяем, что ещё не разложили строку
    if string in g.padded_strings:
        # Если строка имеет паддинг, то просто возвращаем значение.
        get_from_padded_string(name, string)
    else:
        # Если строка не имеет паддинга, делаем его, а потом
        # возвращаем первое значение.
        # %% делать имя на ходу
        c('''
        $type p[(PLAINTEXT_LENGTH + 1)/$size + 2];
        memset(p, 0, sizeof(p));
        size_t l = strlen({0});
        printf("padding: l = %d\\n", l);
        memcpy(p, saved_key[index], l);
        ((unsigned char *)p)[l] = 0x80;
        p[(PLAINTEXT_LENGTH + 1)/$size] = 0;
        p[(PLAINTEXT_LENGTH + 1)/$size + 1] = JOHNSWAP$bits(l << 3);
        ''', string)
        g.padded_strings[string] = []
        get_from_padded_string(name, string)

def b_input_salt(name):
    g.types[name] = 'string'
    # %% checks?
    if Global.c_output is g:
        c('#define {0} (argv[2])', name)
    else:
        not_implemented()

def b_set_item(name, idx, value):
    c('{0}[{1}] = {2};', name, idx, value)

def b_output(var):
    if Global.c_output is g:
        # %% вариант для джона
            # ((unsigned char*)&((($type*)crypt_out[index/MMX_COEF_SHA512])[myindex + {1} * MMX_COEF_SHA512]))[$size * {1} + i] = ((unsigned char *)&{0})[$size - i - 1];
        # c('''
        # for (i = 0; i < $size; i++) {{
        #     ((unsigned char*)&( (crypt_out[index/MMX_COEF_SHA512 + {1} * MMX_COEF_SHA512][myindex]) ))[$size * {1} + i] = ((unsigned char *)&{0})[$size - i - 1];
        # }}''', var, len(g.output_names))
        # c('''
        # for (i = 0; i < $size; i++) {{
        #     ((unsigned char*)&( (($type*)(crypt_out[index/MMX_COEF_SHA512]))[myindex + {1} * MMX_COEF_SHA512] ))[i] = ((unsigned char*)&{0})[$size - i - 1];
        # }}''', var, len(g.output_names))
#         c('''
# (($type*)(crypt_out[index/MMX_COEF_SHA512]))[myindex + {1} * MMX_COEF_SHA512] = {0};
#         ''', var, len(g.output_names))
        # c('''
        # (($type*)(crypt_out[0]))[{1}] = {0};
        # ''', var, len(g.output_names))
        # c(''' /* no op: output {0} */  ''', var, len(g.output_names))
        # c(''' crypt_out[0][{1} + 1] = {0}; ''', var, len(g.output_names))
        c('dk_put_output({0}, {1});', var, len(g.output_names))
        g.output_names.append(var)
    elif Global.c_output is funcs:
        c('result->H[{0}] = {1};', len(funcs.output_names), var)
        funcs.output_names.append(var)
    else:
        not_implemented()

def b_check_output(var):
    # c('crypt_out[0][0] = {0};', var)
    c('dk_quick_output({0});', var)

def b_input(name):
    # В момент вывода отметки о входах должны быть убраны.
    # bad_instruction()
    # c('#define {0} ((($type*)saved_key[index/MMX_COEF_SHA512])[myindex + {1} * MMX_COEF_SHA512])',
    # c('#define {0} (JOHNSWAP64((($type*)saved_key[0])[{1}]))mw',
    c('#define {0} (dk_read_input({1}))',
    name, len(g.inputs))
    g.inputs.append(name)

bin_ops = {
'__add__': '+',
'__sub__': '-',
'__xor__': '^',
'__mul__': '*',
'__rshift__': '>>',
'__lshift__': '<<',
'__and__': '&',
'__or__': '|',
'__mod__': '%',
'__le__': '<=',
'__lt__': '<',
'__ge__': '>=',
'__gt__': '>',
'__eq__': '==',
'__ne__': '!='
}

# %% All ops except assignment may be expressed using either '#define'
#  % or assignment. It may affect performance, try different.

for i in bin_ops:
    v = bin_ops[i]
    def gen_func(c_op):
        def func(name, arg1, arg2):
            a('$type {0} = {1} {2} {3};', name, arg1, c_op, arg2)
        return func
    exec('b_{0} = gen_func(v)'.format(i))

# assignment
def b___floordiv__(lvalue, rvalue):
    # %% типы, кроме num, должны быть раскрыты до этого?
    c('{0} = {1};', lvalue, rvalue)

# def get_length(name):
#     if name not in lengths:
#         lengths['_count'] += 1
#         n = 'len{0}'.format(lengths['_count'])
#         c('size_t {0} = strlen({1});', n, name)
#         lengths[name] = n
#     return lengths[name]

# temp = []

def b_get_int_raw(name, string, idx):
    # It's like get_int but without length check.
    # %% быстрее?
    # %% опять тип
    # %% обработка того же эндианнесса
    # %% проверка, что типы совпадают заявленному
    # %% optimize strlen with already used op-strlen
    # %% optimize
    # temp.append(name)
    c('''
    $type {0};
    for (i = 0; i < $size; i++) {{
        ((unsigned char *)&{0})[$size - i - 1] = {1}[$size * {2} + i];
    }}''', name, string, idx)

def b_get_int(name, string, idx, length):
    # %% быстрее?
    # %% опять тип
    # %% обработка того же эндианнесса
    # %% проверка, что типы совпадают заявленному
    # %% optimize strlen with already used op-strlen
    # %% optimize
    # temp.append(name)
    # c('$type {0};', name)
    def_var_default(name)
    c('''
    for (i = 0; i < $size; i++) {{
        ((unsigned char *)&{0})[$size - i - 1] = ($size * {2} + i < {3} ? {1}[$size * {2} + i] : 0);
    }}''', name, string, idx, length)

def b_put0x80(string, length):
    # %% We override '\0'.
    c('{0}[{1}] = 0x80;', string, length)

def b___getitem__(name, arr, idx):
    if arr in g.types and g.types[arr] == 'string':
        print >> sys.stderr, name, arr, idx
        # Если мы индексируем строку, то это означает взять инт из
        # неё, а не байт.
    elif arr in g.types and g.types[arr] == 'digest':
        # c('$type {0} = ({1}->H[{2}]);', name, arr, idx)
        a('$type {0} = ({1}->H[{2}]);', name, arr, idx)
    else:
        # %% use '#define' to allow assignments
        # c('$type {0} = ({1}[{2}]);', name, arr, idx)
        a('$type {0} = ({1}[{2}]);', name, arr, idx)

def b___invert__(name, arg):
    # c('$type {0} = ~{1};', name, arg)
    a('$type {0} = ~{1};', name, arg)

def b_swap_to_be(name, arg):
    a('$type {0} = JOHNSWAP$bits({1});', name, arg)

b_swap_to_le = b_swap_to_be

def b_ror(name, arg1, arg2):
    a('$type {0} = ror({1}, {2});', name, arg1, arg2)

def b_rol(name, arg1, arg2):
    a('$type {0} = rol({1}, {2});', name, arg1, arg2)

def b_get_length(name, string):
    if Global.c_output is g:
        c('size_t {0} = strlen({1});', name, string)
        # c('size_t {0} = saved_key_length[index/MMX_COEF_SHA512 + myindex];', name, string)
    elif Global.c_output is funcs:
        # c('size_t {0} = strlen({1});', name, string)
        c('size_t {0} = state->len;', name)
    else:
        not_implemented()

def b_cycle_const_range(name, label, init, last, step):
    c('size_t {0};\n for ({0} = {1}; {0} <= {2}; {0} += {3}) {{',
      name, init, last, step)

def b_cycle_range(name, label, init, last, step):
    # на данный момент нет разницы; разница может проявляться раньше
    b_cycle_const_range(name, label, init, last, step)

def b_cycle_end(label):
    # %% use cycle name
    c('}}')
    if label in Global.c_output.cycles and Global.c_output.cycles[label] == 'while':
        Global.c_output.use_define.pop(0)

def b_cycle_while_begin(label):
    Global.c_output.cycles[label] = 'while'
    Global.c_output.use_define.insert(0, True)

def b_cycle_while(label, condition):
    # %% условие может быть так вставлено, только если оно было
    # выведено дефайнами
    c('while ({0}) {{', condition)

def b_if_condition(label, condition):
    # %% use label
    c('if ({0}) {{', condition)

def b_if_else(label):
    # %% use label
    c('}} else {{')

def b_if_end(label):
    # %% use label
    c('}}')

def b_init(state_name, algo):
    g.types[state_name] = 'digest_state'
    # load_iuf(algo)
    c('struct digest_state* {0} = init();', state_name)

def b_update(state_name, string, length):
    c('update({0}, {1}, {2});', state_name, string, length)

def b_final(digest_name, state_name):
    g.types[digest_name] = 'digest'
    c('struct digest* {0} = final({1});', digest_name, state_name)

def b_free(string):
    # c('free({0});', string)
    # %%
    pass

def b_string_copy_and_extend(name, string, length1, length2):
    # %% malloc check
    # 'string' may or may not be a null-terminated string.d
    c('''
    unsigned char* {0} = malloc({3});
    memset({0}, 0, {3});
    memcpy({0}, {1}, {2});
    ''', name, string, length1, length2)
    # for (i = 0; i < 128; i++) printf("%02x", {0}[i]); printf("\\n");


def b_put_int(string, idx, value):
    # It's a reverse to get_int_raw.
    # %% быстрее?
    # %% опять тип
    # %% обработка того же эндианнесса
    # %% проверка, что типы совпадают заявленному
    # %% optimize strlen with already used op-strlen
    # %% optimize
    # temp.append(name)
    c('''
    for (i = 0; i < $size; i++) {{
        {1}[$size * {2} + i] = ((unsigned char *)&{0})[$size - i - 1];
    }}''', value, string, idx)
    # c('for (i = 0; i < 128; i++) printf("%02x", {0}[i]); printf("\\n");', string)

def b_print_buf(string, length):
    c('''
    printf(">> length is %d\\n", {1});
    for (i = 0; i < {1}; i++) {{
        if (i && i % $size == 0)
           printf(" ");
        printf("%02x", (unsigned char *){0}[i]);
    }}
    printf("\\n");''', string, length)

def b_print_var(name):
    c('printf("  {0} is 0x $formatx $formatu\\n", {0}, {0});', name)

def b_goto(label):
    # %% automatic names?
    c('goto {0};', label)

def b_label(label):
    # c('{0}: ;', label)
    # %% пока что выключено, так как не дружит с анролом
    pass

def b_digest_to_string(name, digest):
    # %% memory leak
    c("""
    unsigned char* {0} = malloc($size * 8);
    for (j = 0; j < 8; j++) {{
        for (i = 0; i < $size; i++) {{
            {0}[$size * j + i] = ((unsigned char *)&({1}->H[j]))[$size - i - 1];
        }}
    }}""", name, digest)

def b_fill_string(name, out_length, string, string_length):
    # %% memory leak
    c('''
    unsigned char* {0} = malloc({1});
    for (i = 0; i < {1}; i++)
        {0}[i] = {2}[i % {3}];
    ''', name, out_length, string, string_length)

def b_print_digest(name):
    c('''
    for (i = 0; i < 8; i++) {{
        if (i)
            printf(" ");
        printf("$formatx", {0}->H[i]);
    }}
    printf("\\n");
    ''', name)


# %% implement
"""
string digest_to_string(digest)
string fill_string(num, string)

digest_state init(label)
void update(!digest_state, string)
digest final(digest_state)
"""

# ######################################################################
# bitslice versions b_bs_*

# ** __floordiv__ -> bs_assign
#  * __getitem__ -> bs_getitem
#  * __xor__ -> bs_xor
#  * __or__ -> bs_or
#  * __and__ -> bs_and
#  * __invert__ -> bs_invert


# ** ops are without underscore: op instead of __op__
bs_bin_ops = {
# '__xor__': '^',
# '__and__': '&',
# '__or__': '|'
'xor': '^',
'and': '&',
'or': '|'
}

# %% All ops except assignment may be expressed using either '#define'
#  % or assignment. It may affect performance, try different.

for i in bs_bin_ops:
    v = bs_bin_ops[i]
    def gen_func(c_op):
        def func(name, arg1, arg2):
            # %% должно зависеть от типа
            a('$bstype {0} = {1} {2} {3};', name, arg1, c_op, arg2)
        return func
    exec('b_bs_{0} = gen_func(v)'.format(i))

def b_bs_invert(name, arg1):
    a('$bstype {0} = ~{1};', name, arg1)

b_bs_assign = b___floordiv__

# Функция создания констант
# Создаёт только 2 константы: 0 и 1
def b_bs_new_const(name, value):
    assert(value == "0" or value == "1")
    if value == "0":
        # %% correct suffix
        c("#define {0} 0ULL", name)
    else:
        c("#define {0} 0xFFFFFFFFFFFFFFFFULL", name)

def b_bs_make_array(name, label, size):
    c("$bstype {0} [{1}][$bssize];", name, size)

def b_bs_getitem(name, array, idx, bit):
    a('$bstype {0} = ({1}[{2}][{3}]);', name, array, idx, bit)

def b_bs_set_item(array, idx, value, bit):
    c('{0}[{1}][{3}] = {2};', array, idx, value, bit)

def b_bs_new_var(name):
    # %% support declarations before code
    c('$bstype {0};', name)

# ** We expect that all print_var() for 1 var go in 1 pack starting
#  * from bit 0 and ending with bit N-1.
# %% Make checks for that; можно было бы избавиться от этого: надо
#  % просто трекать, сколько битов мы вывели, а если сохранить в
#  % инструкции начальное имя, то можно даже по переменным трекать.
#  % Правда, вывод может стать непредсказуемым, так что надо просто
#  % ломаться, если не по порядку идут.
def b_bs_print_var(name, bit):
    # name - имя переменной, несущей вектор битов с номером bit
    bit = int(bit)
    # Мы выводим только первый и последний кандидаты из пачки
    # Временные переменные для сбора битов
    c_once('$type bs_first;')
    c_once('$type bs_last;')
    if bit == 0:
        # В самом начале обнуляем временные переменные
        c('bs_first = bs_last = 0;')
    # Для каждого бита выводим код, кладущий бит во временные
    # переменные
    # c('bs_last |= (({0} & (1ULL << ($bssize - 1))) >> ($bssize - 1)) << ($bits - {0} - 1);', bit)
    # c('bs_first |= (({0} & (1ULL << 0)) >> 0) << ($bits - {0} - 1);', bit)
    c('bs_last |= (({0} >> ($bssize - 1)) & 1ULL) << ($bits - {1} - 1);', name, bit)
    c('bs_first |= ({0} & 1ULL) << ($bits - {1} - 1);', name, bit)
    if bit == g.bits - 1:
        # Мы накопили всё, выводим переменные.
        c('printf("first = $formatx  last = $formatx\\n", bs_first, bs_last);')

def b_bs_output(name, bit):
    # bit игнорируется на данный момент
    i = len(g.output_bs_names)
    g.output_bs_names.append(name)
    c('crypt_out[{1}] = {0};', name, i)

def b_bs_input(name, bit):
    # bit игнорируется на данный момент
    i = len(g.input_bs_names)
    g.input_bs_names.append(name)
    c('#define {0} (bits[{1}])', name, i)

# ######################################################################
# vectorized versions b_v_*

# совмещённая функция для добавления 0x80, паддинга и записи
# длины в конец, для sha2;
# одна инструкция - один выходной инт, так что можно собрать всё и
# потом вывести; или вначале разобрать в буфер, а потом уже раздавать
def b_v_get_from_key_0x80_padding_length(name, string):
    # Проверяем, что ещё не разложили строку
    if string in g.padded_strings:
        # Если строка имеет паддинг, то просто возвращаем значение.
        v_get_from_padded_string(name, string)
    else:
        # Если строка не имеет паддинга, делаем его, а потом
        # возвращаем первое значение.
        v_put_0x80_padding_length(string)
        g.padded_strings[string] = []
        v_get_from_padded_string(name, string)

def b_v_input(name):
    # bad_instruction()
    a('__m128i {0} = dk_v_read_input({1});',
    name, len(g.inputs))
    g.inputs.append(name)

def b_v_check_output(var):
    # c('crypt_out[0][0] = {0};', var)
    c('dk_v_quick_output({0}, {1});', var, len(g.quick_output_names))
    g.quick_output_names.append(var)

def b_v_output(var):
    if Global.c_output is g:
        # _mm_store_si128((__m128i *) &(crypt_out[index/MMX_COEF_SHA512][{1}]), {0});
#         c('''
# _mm_store_si128(&(((__m128i*)(crypt_out[index/MMX_COEF_SHA512]))[{1}]), {0});
#         ''', var, len(g.output_names))
        c('dk_v_put_output({0}, {1});', var, len(g.output_names))
        g.output_names.append(var)
    # elif Global.c_output is funcs:
    #     c('result->H[{0}] = {1};', len(funcs.output_names), var)
    #     funcs.output_names.append(var)
    else:
        not_implemented()

def b_v_new_const(name, value):
    # %% handle $suffix according to output type, not algo's type
    # %% make an option to choose between set1 and load
    suf = '32' if g.bits == 32 else '64x'
    c('#define {0} _mm_set1_epi{2}({1}$suffix)', name, value, suf)
    # c('#define {0} _mm_set_epi64x({1}$suffix, {1}$suffix)', name, value)
    # # %% correct $type here
    # c_prepend('static unsigned long long {0}_stored[4] __attribute__((aligned(16))) = {{ {1}$suffix, {1}$suffix, {1}$suffix, {1}$suffix }};', name, value)
    # c('#define {0} _mm_load_si128((__m128i *){0}_stored)', name)

def b_v_swap_to_be(name, arg):
    a('__m128i {0} = vshuffle_epi8({1}, swap_endian${{bits}}_mask);', name, arg)

b_v_new_state_var = b_new_state_var

def b_v_new_array(name, label, *values):
    # c('$type {0}[{1}] = {{ {2} }};', name, len(values), ", ".join(values))
    c('__m128i {0}[] $align = {{ {1} }};', name, ", ".join(values))

def b_v_make_array(name, label, size):
    # %% sometimes volatile for setupW in raw-sha512 works better
    #  % Full unroll (and some other whistles) with/without volatile:
    #  % Raw:	1608K c/s real, 1608K c/s virtual; 7070 instructions
    #  % Raw:	1488K c/s real, 1488K c/s virtual; 7467 instructions
    # c('__m128i volatile {0}[{1}] $align;', name, size)
    c('__m128i {0}[{1}] $align;', name, size)

def b_v_ror(name, arg1, arg2):
    # %% use shuffle for rotates of 8
    # %% subst ror at bytecode level when not XOP
    a('__m128i {0} = _mm_roti_epi$bits({1}, {2});', name, arg1, arg2)

def b_v_rol(name, arg1, arg2):
    # %% use shuffle for rotates of 8
    # %% subst ror at bytecode level when not XOP
    # a('__m128i {0} = my_rol_epi$bits({1}, {2});', name, arg1, arg2)
    a('__m128i {0} = vroti_epi$bits({1}, {2});', name, arg1, arg2)

v_bin_ops = {
'__add__': '_mm_add_epi$bits',
'__sub__': '_mm_sub_epi$bits',
'__xor__': '_mm_xor_si128',
'__mul__': '_mm_mullo_epi$bits',
'__rshift__': '_mm_srli_epi$bits',
'__lshift__': '_mm_slli_epi$bits',
'__and__': '_mm_and_si128',
'__or__': '_mm_or_si128',
# '__mod__': '%',
# '__le__': '<=',
'__lt__': '_mm_cmplt_epi16',
# '__ge__': '>=',
'__gt__': '_mm_cmpgt_epi16',
'__eq__': '_mm_cmpeq_epi16',
'__ne__': '!='
}

# type: short
#define EQ _mm_cmpeq_epi16
#define GT _mm_cmpgt_epi16
#define LT _mm_cmplt_epi16
#define OR _mm_or_si128
#define XOR _mm_xor_si128
#define AND _mm_and_si128
#define MUL _mm_mullo_epi16
#define SR _mm_srli_epi16
#define SL _mm_slli_epi16
#define SUB _mm_sub_epi16
#define ADD _mm_add_epi16
#define ANDNOT _mm_andnot_si128
#define SHUFFLE8 _mm_shuffle_epi8
#define BLEND8 _mm_blendv_epi8

# %% copy-pasted
for i in v_bin_ops:
    v = v_bin_ops[i]
    def gen_func(c_op):
        def func(name, arg1, arg2):
            a('__m128i {0} = {2}({1}, {3});', name, arg1, c_op, arg2)
        return func
    exec('b_v_{0} = gen_func(v)'.format(i))

def b_v_new_var(name):
    c('__m128i {0};', name)

b_v___floordiv__ = b___floordiv__

def b_v_andnot(name, arg1, arg2):
    a('__m128i {0} = _mm_andnot_si128({1}, {2});', name, arg1, arg2)

def b_v___invert__(name, arg):
    # %% just warn if used
    # it is needed for md5
    a('__m128i {0} = _mm_xor_si128({1}, _mm_set1_epi32(0xFFFFFFFFU));', name, arg)
    # a('__m128i {0} = _mm_andnot_si128({1}, _mm_set1_epi32(0xFFFFFFFFU));', name, arg)
    # bad_instruction()

def b_v___getitem__(name, arr, idx):
    # %% use '#define' to allow assignments
    a('__m128i {0} = ({1}[{2}]);', name, arr, idx)

b_v_set_item = b_set_item

def b_v_print_var(name):
    c('''
    _mm_store_si128(&tmp, {0});
#if $vsize == 2
    printf(" 0x $formatx 0x $formatx\\n", *($type *)&tmp, *(($type *)&tmp + 1));
#else
#if $vsize == 4
    printf(" 0x $formatx 0x $formatx 0x $formatx 0x $formatx\\n", *($type *)&tmp, (($type *)&tmp)[1], (($type *)&tmp)[2], (($type *)&tmp)[3]);
#else
#error "unsupported vsize ($vsize) for v_print_var"
#endif
#endif
    ''', name)


# ######################################################################
# other code

# aggregate functions into a dictionary: bytecode instruction -> function
bytecode_functions = {}
for i in dir():
    if i.startswith('b_'):
        b = i[2:]
        bytecode_functions[b] = eval(i)

def out_all(code):
    bits = g.bits
    # c('size_t i, j;')
    c('size_t i;')
    c('__m128i tmp;')
    # %% это нужно только в векторных сборках
    # c('__m128i tmp;')
    for l in code:
        if l[0] in bytecode_functions:
            bytecode_functions[l[0]](*l[1:])
        else:
            raise Exception("unknown instruction [{0}]".format(", ".join(l)))
    gen_var_defs()

def gen_to_str(code, template, args, additional_replacements = {}):
    g.reset()
    # %% стоит вынести ror/rol, можно раскрывать в другие операции
    # sha512 = B.get_code_full('iuf', False, False, { 'size': 8 })
    # Global.c_output = funcs
    c('#define ror(a, b) (((a) << ($bits - (b))) | ((a) >> (b)))')
    c('#define rol(a, b) (((a) >> ($bits - (b))) | ((a) << (b)))')
    # out_all(sha512)
    # Global.c_output = g
    out_all(code)
    # print >> sys.stderr, temp
    # c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(temp)), ', '.join(temp))
    if len(g.output_names) > 0:
        # c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(g.output_names)), ', '.join(g.output_names))
        if args['use_bitslice']:
            print_bs(g.output_names)
    # replace various global vars like size and type
    def subst_vars(code):
        # %% align only arrays?
        # ** During debugging, __attribute__ slows down coloring of .c
        #  * file in emacs.
        align = '__attribute__((aligned(16)))'
        align = ''
        return Template(code).safe_substitute(type = g.o_type, formatx = g.o_format_x, formatu = g.o_format_u, bits = g.bits, size = g.size, suffix = g.o_suffix, align = align, bstype = g.bs_o_type, bssize = g.bs_size, input_swap = g.need_input_swap, vsize = g.vsize, **additional_replacements)
    # g.code = subst_vars(g.code)
    # g.funcs_code = subst_vars(g.funcs_code)
    # print code_template.safe_substitute(code = g.code, funcs = g.funcs_code)
    g.code = subst_vars(g.code)
    # %% наверное, так делать плохо, костылями попахивает...
    # Делаем undef всего, что было определено макросами внутри куска кода
    defines = re.compile('^#\s*define\s*(\w+)', re.M).findall(g.code)
    # %% определения могут быть не уникальными
    g.code += ''.join(['#undef {0}\n'.format(i) for i in defines])
    result = subst_vars(Template(template).safe_substitute(code = g.code, constants = g.const_code))
    return result

def gen(code, *args):
    # g.reset()
    print gen_to_str(code, *args)
    return code

# def main(code, args):
#     # %% copy-pasted, see gen()
#     # %% стоит вынести ror/rol, можно раскрывать в другие операции
#     sha512 = B.get_code_full('iuf', False, False, { 'size': 8 })
#     Global.c_output = funcs
#     c('#define ror(a, b) (((a) << ($bits - (b))) | ((a) >> (b)))')
#     c('#define rol(a, b) (((a) >> ($bits - (b))) | ((a) << (b)))')
#     out_all(sha512)
#     Global.c_output = g
#     out_all(code)
#     # print >> sys.stderr, temp
#     # c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(temp)), ', '.join(temp))
#     if len(g.output_names) > 0:
#         c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(g.output_names)), ', '.join(g.output_names))
#         if args['use_bitslice']:
#             print_bs(g.output_names)
#     # replace various global vars like size and type
#     def subst_vars(code):
#         return Template(code).safe_substitute(type = g.o_type, formatx = g.o_format_x, bits = g.bits, size = g.size, suffix = g.o_suffix, bstype = g.bs_o_type, bssize = g.bs_size)
#     # g.code = subst_vars(g.code)
#     # g.funcs_code = subst_vars(g.funcs_code)
#     # print code_template.safe_substitute(code = g.code, funcs = g.funcs_code)
#     print subst_vars(Template(template).safe_substitute(code = g.code, funcs = funcs.code))
#     # gen(code, code_template, args)


code_template = """
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

struct digest {
    $type H[8];
};

#define SIZE 20000
struct digest_state {
    size_t len;
    unsigned char buf[SIZE];
};

struct digest_state* init() {
    struct digest_state* t = malloc(sizeof(struct digest_state));
    /* size_t i; */
    t->len = 0;
    memset(t->buf, 0, SIZE);
    return t;
}

void update(struct digest_state* state, unsigned char* string, $type len) {
    /*printf("Update %p with %d: ", state, len);
    size_t myi;
    for (myi = 0; myi < (len); myi++)
        printf("%02x", (string)[myi]);
    printf("\\n");*/
    memcpy(state->buf + state->len, string, len);
    state->len += len;
}

struct digest* final(struct digest_state* state) {
    /*size_t ti;
    printf("Final: length is %d\\n", state->len);
    for (ti = 0; ti < 200; ti++)
        printf("%02x", state->buf[ti]);
    printf("\\n");*/
    struct digest* result = malloc(sizeof(struct digest));
$funcs
    /* free(state); */
    /* %% memory leak */
    return result;
}


int main(int argc, unsigned char ** argv)
{
    if (argc < 1)
        return 1;

    $code

    return 0;
}
"""
# %% вывод со вставкой имён
# %% эндианнес при выводе?


