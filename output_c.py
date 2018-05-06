# -*- coding: utf-8 -*-
# библиотека для вывода кода на си

# Copyright © 2015,2016 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from bytecode_main import drop, clean

from util_main import *

import bytecode_main as B

# size definitions:
# type, format_x, format_u, suffix for constants

size_c = {
    # %% generate asserts to enforce assumptions, or use uint64_t and similar
    'type': { 8: 'unsigned long long', 4: 'unsigned int' },
    'x': { 8: '%016llx', 4: '%08x' },
    'u': { 8: '%016llu', 4: '%08u' },
    'suffix': { 8: 'ULL', 4: 'U' },
}

size_opencl = {
    'type': { 8: 'unsigned long', 4: 'unsigned int' },
    'x': { 8: '%016lx', 4: '%08x' },
    'u': { 8: '%016lu', 4: '%08u' },
    'suffix': { 8: 'UL', 4: 'U' },
}

# %% __m128i and other types
bs_size_type_c = {
    64: 'unsigned long long'
}

bs_size_type_opencl = {
    64: 'unsigned long',
    32: 'unsigned int'
    # 32: 'uint'
}

bs_all_zero = {
    64: '0ULL',
    32: '0U'
}

bs_all_one = {
    64: '0xFFFFFFFFFFFFFFFFULL',
    32: '0xFFFFFFFFU'
}


def bad_instruction():
    raise Exception('bad instruction (see backtrace)')

# %% try it from other file: is it in global namespace or in this module?
def include(name):
    execfile(get_dk_path('output_c_' + name + '.py'), globals())

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
        # self.write_opencl = True
        self.write_opencl = False
    def reset(self):
        self.code = ''
        self.code_arr = []
        self.const_code = ''
        self.funcs_code = ''
        self.output_names = []
        self.quick_output_names = []
        self.input_bs_names = []
        self.output_bs_names = []
        self.array_sizes = {}
        self.bit_lengths = {}
        self.bit_length_bits = []
        self.cycles = {}
        self.use_define = [False]
        # %% надо переименовать inputs в input_names
        self.inputs = []
        self.input_states = []
        self.input_lengths = []
        # словарь определений переменных: тип => { имя => 1, имя => 1 }
        self.var_definitions = {}
        self.types = {}
        self.registers = {}
        self.allocated_v_registers_count = 0
        self.v_consts = {}
        self.consts = {}
        self.asm_in = []
        self.asm_out = []
        self.asm_global_vars = ''
        self.asm_print_vars = []
        self.var_setup_stack = []
        # self.ifs = {}

g = Global()

Global.c_output = g

# %% мы можем перенаправить вывод из c(), однако размеры и всё такое
# будет в g
funcs = Global()

# функция добавления кода в глобальную строку
def c(code, *args, **kwargs):
    t = code.format(*args, **kwargs) + "\n"
    # That's a dirty trick to allow output of code before var_setup.
    if '$' in t:
        t = Template(t).safe_substitute(
            type = g.o_type,
            formatx = g.o_format_x,
            formatu = g.o_format_u,
            bits = g.bits,
            size = g.size,
            suffix = g.o_suffix,
            bstype = g.bs_o_type,
            bssize = g.bs_size,
            input_swap = g.need_input_swap,
            vsize = g.vsize,
            # %% additional_replacements were removed
            asm_global_vars = g.asm_global_vars)
    # Global.c_output.code += t
    Global.c_output.code_arr.append(t)

def c_prepend(code, *args):
    # Global.c_output.code = code.format(*args) + "\n" + Global.c_output.code
    Global.c_output.code_arr.insert(0, code.format(*args) + "\n")

# функция вывода один раз
written_once = {}
def c_once(code, *args):
    o = code.format(*args)
    if o not in written_once:
        written_once[o] = 1
        c(o)

def asm(code, *args):
    new = []
    for n in args:
        # if n == 'sha256_registers3_var49':
        #     print >> sys.stderr, n, g.registers
        if n in g.registers:
            new.append(g.registers[n])
        else:
            new.append(n)
    c('"' + code + '\\n\\t"', *new)

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
    defs = None
    if g.write_opencl:
        defs = size_opencl
        defs = size_opencl
    else:
        defs = size_c
    g.size = size
    g.o_type = defs['type'][size]
    g.o_format_x = defs['x'][size]
    g.o_format_u = defs['u'][size]
    g.o_suffix = defs['suffix'][size]
    g.bits = size * 8
    if g.vectorize:
        g.vsize = 16 / size
    else:
        g.vsize = 1

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
    g.bs_all_one = bs_all_one[bs_size]
    g.bs_all_zero = bs_all_zero[bs_size]
    if g.write_opencl:
        g.bs_o_type = bs_size_type_opencl[bs_size]
    else:
        g.bs_o_type = bs_size_type_c[bs_size]

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


# %% хм, может быть сокращено до форматной строки на имя, кроме
#  % new_array, где join используется

# %% стоит делать проверку аргументов на тип

# одна переменная может быть описана несколько раз, реально она будет
# описана только один раз
def def_var(t, var):
    # # No definition if we use define to express assignment
    # if Global.c_output.use_define[0]:
    #     return
    if False:
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
        # # This way makes emacs very slow:
        # c_prepend('{0} {1};', i, ",\n".join("{0} $align".format(v) for v in vs.keys()))
        # # This way is very slow:
        # for v in vs.keys():
        #     c_prepend('{0} {1} $align;', i, v)
        # This way is rather fast and does not slow down other tools:
        beginning = '{0} '.format(i)
        end = ' $align;\n'
        middle = end + beginning
        ss = beginning + middle.join(vs.keys()) + end
        c_prepend(ss)


# ######################################################################
# b_* - definitions of functions to handle each bytecode instruction.
# b_v_* - vectorized, has its own section

def b_debug_exit(label):
    # c('return;')
    c('fprintf(stderr, "debug_exit\\n");')
    c('exit(1);')

def real_var_setup(size, endianity):
    apply_size(int(size))
    apply_endianity(endianity)
    # for n in "dk_o_type", "dk_o_format_x", "dk_o_format_u", "dk_bits", "dk_size", "dk_vsize":
    #     c('#ifdef {0}', n)
    #     c('#undef {0}', n)
    #     c('#endif')
    #     c('#define {0} {1}', n, eval(n.replace('dk_', 'g.')))
    # c('#undef ror')
    # c('#define ror(a, b) (((a) << ($bits - (b))) | ((a) >> (b)))')
    # c('#undef rol')
    # c('#define rol(a, b) (((a) >> ($bits - (b))) | ((a) << (b)))')

def b_var_setup(size, endianity):
    g.var_setup_stack.append((size, endianity))
    real_var_setup(size, endianity)

def b_var_setup_pop():
    g.var_setup_stack.pop()
    if len(g.var_setup_stack) >= 1:
        real_var_setup(*g.var_setup_stack[-1])

def b_print_verbatim(hexed):
    # ** 'i * 2 + 2' and not 'i * 2 + 1' because that's upper border of slice
    c('printf("pv: %s\\n", "{0}");', ''.join('\\x' + hexed[i * 2 : i * 2 + 2] for i in range(len(hexed) / 2)))

def b_use_define(label):
    # %% parity?
    if label == 'yes':
        Global.c_output.use_define.insert(0, True)
    else:
        Global.c_output.use_define.pop(0)

def b_new_const(name, value):
    g.consts[name] = value
    # %% handle $suffix according to output type, not algo's type
    c('#define {0} {1}$suffix', name, value)
    # c_const('#define {0} {1}$suffix', name, value)

def b_new_var(name):
    # c('$type {0};', name)
    def_var_default(name)

# def b_new_state_var(name, value):
#     # Если состояние добралось до раскрытия, то это значит, что мы не
#     # использовали его в качестве входа, так это просто константа. Но
#     # аргумент для функции уже был обработан, как константа. Так что
#     # просто даём новое имя.
#     c('#define {0} {1}', name, value)

def b_new_array(name, label, *values):
    # c('$type {0}[{1}] = {{ {2} }};', name, len(values), ", ".join(values))
    g.array_sizes[name] = len(values)
    # We use new_array for arrays of constants, they can be made
    # static. 'static' keyword gives noticeable performance raise.
    # %% Lift them to global context?
    if g.write_opencl:
        c('$type {0}[] = {{ {1} }};', name, ", ".join(values))
    else:
        c('static $type {0}[] = {{ {1} }};', name, ", ".join(values))

def b_bs_new_array(name, label, *values):
    g.array_sizes[name] = len(values)
    if g.write_opencl:
        packs = [values[i : i + g.bits] for i in range(0, len(values), g.bits)]
        packs_str = ", ".join("{ " + (", ".join(p)) + " }\n" for p in packs)
        c_const('__constant $bstype {0}[][{2}] = {{ {1} }};', name, packs_str, g.bits)
    else:
        not_implemented()

def b_make_array(name, label, size):
    c('$type {0}[{1}];', name, size)

def b_low(name, var):
    a('$type {0} = ($type)({1});', name, var)

def b_high(name, var):
    # %% hard coded 32
    a('$type {0} = ($type)({1} >> 32);', name, var)

def b_combine_low_high(name, arg1, arg2):
    # %% hard coded 32
    a('$type {0} = (($type){1}) ^ ((($type){2}) << 32);', name, arg1, arg2)


def b_input_rounds(name):
    a('$type {0} = dk_input_rounds();', name)

# def b_input_key(name):
#     # a('$type {0} = dk_input_key();', name)
#     c('#define {0} dk_input_key()', name)
# def b_input_salt(name):
#     # a('$type {0} = dk_input_salt();', name)
#     c('#define {0} dk_input_salt()', name)
# def b_input_salt2(name):
#     # a('$type {0} = dk_input_salt2();', name)
#     c('#define {0} dk_input_salt2()', name)

include('modules')

def b_set_item(name, idx, value):
    c('{0}[{1}] = {2};', name, idx, value)

def b_may_split_here(label):
    # noop
    pass

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
        c('dk_output({0}, {1});', var, len(g.output_names))
        g.output_names.append(var)
    # elif Global.c_output is funcs:
    #     c('result->H[{0}] = {1};', len(funcs.output_names), var)
    #     funcs.output_names.append(var)
    else:
        not_implemented()

def b_check_output(var):
    # c('crypt_out[0][0] = {0};', var)
    # c('dk_quick_output({0});', var)
    c('dk_quick_output({0}, {1});', var, len(g.quick_output_names))
    g.quick_output_names.append(var)

# dummies
# %% raise error? show warning?
def b_in_memory(name):
    pass
def b_in_register(name):
    pass

def b_input(name):
    # В момент вывода отметки о входах должны быть убраны.
    # bad_instruction()
    # %% переименовать в dk_input
    c('#define {0} (dk_input({1}))',
      name, len(g.inputs))
    # a('$type {0} = (dk_input({1}));', name, len(g.inputs))
    g.inputs.append(name)

def b_new_state_var(name, value):
    # %% в таком случае мы можем испортить состояние до прочтения,
    #  % возможно, стоит принудительно(?) копировать переменную, a()?
    c('#define {0} (dk_input_state({1}))',
      name, len(g.input_states))
    g.input_states.append(name)

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

def b___getitem__(name, arr, idx):
    # %% use '#define' to allow assignments
    # c('$type {0} = ({1}[{2}]);', name, arr, idx)
    a('$type {0} = ({1}[{2}]);', name, arr, idx)

b_sbox = b___getitem__

def b_load(name, arg):
    # %% just rename instead?
    a('$type {0} = {1};', name, arg)
def b_store(name, arg):
    # %% just rename instead?
    c('{0} = {1};', name, arg)

def b___invert__(name, arg):
    # c('$type {0} = ~{1};', name, arg)
    a('$type {0} = ~{1};', name, arg)

def b_swap_to_be(name, arg):
    a('$type {0} = JOHNSWAP$bits({1});', name, arg)

b_swap_to_le = b_swap_to_be

def b_ror(name, arg1, arg2):
    a('$type {0} = dk_ror$bits({1}, {2});', name, arg1, arg2)

def b_rol(name, arg1, arg2):
    a('$type {0} = dk_rol$bits({1}, {2});', name, arg1, arg2)

def b_cycle_const_range(name, label, init, last, step):
    # if g.write_opencl:
    #     c('size_t {0};\n#pragma unroll 1\nfor ({0} = {1}; {0} <= {2}; {0} += {3}) {{',
    #       name, init, last, step)
    # else:
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
    # %% не надо ли тут фейлиться при повторе?
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

def b_print_var(name):
    c('printf("  {0} is 0x $formatx  u: $formatu\\n", {0}, {0});', name)

def b_print_many(*nums):
    f = " $formatx" * len(nums)
    c('printf("pm:{0}\\n", {1});', f, ', '.join(nums))

def b_goto(label):
    # %% automatic names?
    c('goto {0};', label)

def b_label(label):
    # c('{0}: ;', label)
    # %% пока что выключено, так как не дружит с анролом
    pass

def b_permute(result, name, table):
    c('''
    $type {0} = 0;
    {{
        size_t i;
        for (i = 0; i < {3}; i++) {{
            {0} |= ((({1} >> ($bits - {2}[i] - 1)) & 1) << ($bits - i - 1));
            //printf(">> %zd %lld %lld {1} {2} {3}  $formatx\\n", i, {2}[i], (({1} >> ($bits - {2}[i] - 1)) & 1), {0});
        }}
    }}
    ''', result, name, table, g.array_sizes[table])

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
        c_const("#define {0} {1}", name, g.bs_all_zero)
    else:
        c_const("#define {0} {1}", name, g.bs_all_one)

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
        # c('printf("first = $formatx  last = $formatx\\n", bs_first, bs_last);')
        c('printf(" $formatx\\n", bs_first);')

def b_bs_output(name, bit):
    # bit игнорируется на данный момент
    i = len(g.output_bs_names)
    g.output_bs_names.append(name)
    c('dk_bs_put_output({0}, {1});', name, i)

def b_bs_input(name, bit):
    # bit игнорируется на данный момент
    i = len(g.input_bs_names)
    g.input_bs_names.append(name)
    # c('#define {0} (bits[{1}])', name, i)
    c('#define {0} (dk_bs_read_input({1}))', name, i)

# ######################################################################
# vectorized versions b_v_*

def b_v_input(name):
    # bad_instruction()
    a('__m128i {0} = dk_v_read_input({1});', name, len(g.inputs))
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
    else:
        not_implemented()

def b_v_new_const(name, value):
    g.v_consts[name] = value
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

def b_v_store(name, arg):
    # c('_mm_store_si128(&{0}, {1});', name, arg)
    # c('_mm_store_si128((volatile __m128i *)&{0}, {1});', name, arg)
    c('*(volatile __m128i *)&{0} = {1};', name, arg)
    # c('{0} = {1};', name, arg)

def b_v_load(name, arg):
    # a('__m128i {0} = _mm_load_si128(&{1});', name, arg)
    # a('__m128i {0} = _mm_load_si128((volatile __m128i *)&{1});', name, arg)
    a('__m128i {0} = *(volatile __m128i *)&{1};', name, arg)
    # a('__m128i {0} = {1};', name, arg)

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
#ifndef dk_has_tmp
    __m128i tmp;
#define dk_has_tmp
#endif
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
# assembler output b_a_* and b_a_v_*

def b_a_v_print_var(name):
    # We don't print from asm, just save to global var to print later.
    # %% it should not work with cycles.
    nn = 'asm_print_vars_' + str(len(g.asm_print_vars))
    g.asm_print_vars.append(nn)
    g.asm_global_vars += '__m128i {0};'.format(nn)
    # b_a_v___floordiv__(nn, name)
    asm('movdqa {1}, {0}', nn, name)

def b_a_v_new_const(name, value):
    # %% vsize надо учитывать
    g.v_consts[name] = value
    # g.asm_global_vars += '$type {0}[] = {{ {1}$suffix, {1}$suffix, {1}$suffix, {1}$suffix }};\n'.format(name, value)
    # %% make correct suffix and type
    g.asm_global_vars += 'unsigned int {0}[] = {{ {1}U, {1}U, {1}U, {1}U }};\n'.format(name, value)

def b_a_new_const(name, value):
    # %% vsize надо учитывать
    g.consts[name] = value
    # %% копипаста с векторного варианта
    # g.asm_global_vars += '$type {0}[] = {{ {1}$suffix, {1}$suffix, {1}$suffix, {1}$suffix }};\n'.format(name, value)
    # %% make correct suffix and type
    # g.asm_global_vars += 'unsigned int {0}[] = {{ {1}U, {1}U, {1}U, {1}U }};\n'.format(name, value)
    g.asm_global_vars += 'unsigned int {0}[] = {{ {1}U, 0, 0, 0 }};\n'.format(name, value)

# no output, just assign real register to name
def b_a_v_new_register(name):
    rc = g.allocated_v_registers_count
    rn = "%xmm" + str(rc)
    g.registers[name] = rn
    g.allocated_v_registers_count += 1

def b_a_v___floordiv__(name, arg):
    # %% check: name in registers
    if arg in g.v_consts:
        # %% тут, похоже, надо выплёвывать статические переменные
        # asm('movdqa ${1}, {0}', name, g.v_consts[arg])
        if name in g.registers:
            asm('movdqa {1}, {0}', g.registers[name], arg)
        else:
            print >> sys.stderr, "asm mov:", name, arg
            die('unimplemented')
    elif arg in g.registers and name in g.registers:
        asm('movdqa {1}, {0}', g.registers[name], g.registers[arg])
    # elif arg in g.consts:
    #     asm('movdqa ${1}, {0}', name, g.consts[arg])
    else:
        print >> sys.stderr, "asm mov:", name, arg
        die('unimplemented')

def b_a_begin():
    g.asm_in = []
    g.asm_out = []
    c('asm( "\\n\\t"')

def b_a_end():
    # if len(g.asm_out) > 0:
    #     c(': {0}', ", ".join('"=x" ({0})'.format(v) for v in g.asm_out))
    # if len(g.asm_in) > 0:
    #     if len(g.asm_out) == 0:
    #         c(':')
    #     c(': {0}', ", ".join('"x" ({0})'.format(v) for v in g.asm_in))
    c(');')
    for v in g.asm_print_vars:
        b_v_print_var(v)

def b_a_v___lshift__(name, arg):
    if arg in g.consts:
        # c('"pslld ${1}, {0}\\n\\t"', name, g.consts[arg])
        asm('pslld {1}, {0}', name, arg)
    else:
        die('not scalar constant shift')

def b_a_v___rshift__(name, arg):
    if arg in g.consts:
        # c('"psrld ${1}, {0}\\n\\t"', name, g.consts[arg])
        asm('psrld {1}, {0}', name, arg)
    else:
        die('not scalar constant shift')

def b_a_v___or__(name, arg):
    asm('por {1}, {0}', name, arg)

def b_a_v___add__(name, arg):
    # %% должно различаться для разных size
    asm('paddd {1}, {0}', name, arg)

def b_a_v___invert__(name):
    # %% обычно это должно стать частью andnot
    asm('pxor dk_all_one, {0}', name)

def b_a_v_new_var(name):
    g.asm_global_vars += '__m128i {0};\n'.format(name)

def b_a_v_load(reg, mem):
    # if mem in g.asm_in:
    #     i = g.asm_in.index(mem)
    # else:
    #     i = len(g.asm_in)
    #     g.asm_in.append(mem)
    # asm('movdqa %{1}, {0}', reg, i)
    asm('movdqa {0}, {1}', mem, reg)

def b_a_v_store(mem, reg):
    # if mem in g.asm_out:
    #     i = g.asm_out.index(mem)
    # else:
    #     i = len(g.asm_out)
    #     g.asm_out.append(mem)
    # asm('movdqa {0}, %{1}', reg, i)
    asm('movdqa {0}, {1}', reg, mem)

def b_a_v_swap_to_be(reg):
    asm('pshufb dk_asm_byte_swap_mask, {0}', reg)

def b_a_v___and__(name, arg):
    asm('pand {1}, {0}', name, arg)

def b_a_v___xor__(name, arg):
    asm('pxor {1}, {0}', name, arg)

# ######################################################################
# other code

# aggregate functions into a dictionary: bytecode instruction -> function
bytecode_functions = {}
for i in dir():
    if i.startswith('b_'):
        b = i[2:]
        # %% вот тут от эвала легко можно избавиться
        bytecode_functions[b] = eval(i)

# for f in bytecode_functions:
#     if f not in B.instructions and not f.startswith('a_'): # and not f.startswith('v___'):
#         print f

def out_all(code):
    # c('size_t i, j;')
    # c('size_t i;')
    for l in code:
        if l[0] in bytecode_functions:
            # c('/* {0} */', ' '.join(l))
            try:
                bytecode_functions[l[0]](*l[1:])
            except:
                print >> sys.stderr, 'l:', l
                raise
        else:
            raise Exception("unknown instruction [{0}]".format(", ".join(l)))
    gen_var_defs()

def gen_to_str(code, template, args, additional_replacements = {}, func_name = None, gifs = None):
    if gifs == None:
        gifs = g.ifs = B.collect_ifs(code)
    else:
        g.ifs = gifs
    # вытаскиваем функции и генерируем код для них отдельно
    modules, modules_types = B.extract_modules(code)
    funcs = ''
    if modules:
        # print map(lambda x: x[0], modules.items())
        # print map(lambda x: x[0], B.sort_modules(modules))
        # for k, v in modules.iteritems():
        for k, v in B.sort_modules(modules):
            if k == '_main':
                continue
            funcs += gen_to_str(v, func_templates[modules_types[k][0]], args, additional_replacements, func_name = k, gifs = gifs)
        code = modules['_main']
    g.reset()
    # g.ifs = gifs
    if 'vectorize' in additional_replacements:
        g.vectorize = additional_replacements['vectorize']
    else:
        g.vectorize = 1
    # %% стоит вынести ror/rol, можно раскрывать в другие операции
    # sha512 = B.get_code_full('iuf', False, False, { 'size': 8 })
    # Global.c_output = funcs
    # %% ротейт на 0 - undefined behaviour при этом; при ксоре тут
    #  % может быть ошибка, так как сдвиг на размер может не изменить
    #  % значение
    # c('#define ror(a, b) (((a) << ($bits - (b))) | ((a) >> (b)))')
    # c('#define rol(a, b) (((a) >> ($bits - (b))) | ((a) << (b)))')
    # out_all(sha512)
    # Global.c_output = g
    out_all(code)
    # %% если мы накосячили, то у нас может быть перемешан код, это
    #  % стоит выверить и поправить
    g.code += ''.join(g.code_arr)
    # print >> sys.stderr, temp
    # c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(temp)), ', '.join(temp))
    # if len(g.output_names) > 0:
        # c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(g.output_names)), ', '.join(g.output_names))
        # if args['use_bitslice']:
        #     print_bs(g.output_names)
    # replace various global vars like size and type
    def subst_vars(code):
        # %% align only arrays?
        # ** During debugging, __attribute__ slows down coloring of .c
        #  * file in emacs.
        align = '__attribute__((aligned(16)))'
        align = ''
        return Template(code).safe_substitute(
            type = g.o_type,
            formatx = g.o_format_x,
            formatu = g.o_format_u,
            bits = g.bits,
            size = g.size,
            suffix = g.o_suffix,
            align = align,
            bstype = g.bs_o_type,
            bssize = g.bs_size,
            input_swap = g.need_input_swap,
            vsize = g.vsize,
            asm_global_vars = g.asm_global_vars,
            functions = funcs,
            func_name = func_name,
            output_count = len(g.output_names),
            **additional_replacements)
        # return Template(code).safe_substitute(
        #     type = "dk_o_type",
        #     formatx = "dk_o_format_x",
        #     formatu = "dk_o_format_u",
        #     bits = "dk_bits",
        #     size = "dk_size",
        #     suffix = g.o_suffix,
        #     vsize = "dk_vsize",
        #     align = align,
        #     bstype = g.bs_o_type,
        #     bssize = g.bs_size,
        #     input_swap = g.need_input_swap,
        #     asm_global_vars = g.asm_global_vars,
        #     **additional_replacements)
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

# def gen(code, template, args, additional_replacements = {}):
def gen(code, *args):
    # code_str = gen_to_str(code, '$code', args, additional_replacements)
    # align = ''
    # print Template(template).safe_substitute(
    #     code = code_str,
    #     type = g.o_type,
    #     formatx = g.o_format_x,
    #     formatu = g.o_format_u,
    #     bits = g.bits,
    #     size = g.size,
    #     suffix = g.o_suffix,
    #     align = align,
    #     bstype = g.bs_o_type,
    #     bssize = g.bs_size,
    #     input_swap = g.need_input_swap,
    #     vsize = g.vsize,
    #     asm_global_vars = g.asm_global_vars,
    #     **additional_replacements)
    out_file = args[0]
    with open(out_file, 'w') as f:
        print >> f, gen_to_str(code, *args[1:])
    return code
