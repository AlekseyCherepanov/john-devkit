# -*- coding: utf-8 -*-
# библиотека для вывода кода в скалярный си
# в отдельный файл или в формат джона

# аргументы сгенерированного бинарника: key salt rounds

import sys

from string import Template
from bytecode_main import drop, clean

import bytecode_main as B
# import output_c as O

size_type = {
    # 8: 'unsigned long long',
    8: 'int',
    4: 'unsigned int'
}
size_format_x = {
    8: '%016llx',
    4: '%08x'
}
size_suffix = {
    8: 'ULL',
    4: 'U'
}

def not_implemented():
    raise Exception('not implemented')

def bad_instruction():
    raise Exception('bad instruction (see backtrace)')

class Global:
    c_output = None
    def __init__(self):
        self.code = ''
        self.funcs_code = ''
        self.out_names = []
        self.bit_lengths = {}
        self.bit_length_bits = []
        self.cycles = {}
        self.use_define = [False]
        self.inputs = []

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
    g.o_suffix = size_suffix[size]
    g.bits = size * 8


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

# словарь определений переменных: тип => { имя => 1, имя => 1 }
var_definitions = {}

# одна переменная может быть описана несколько раз, реально она будет
# описана только один раз
def def_var(t, var):
    # # No definition if we use define to express assignment
    # if Global.c_output.use_define[0]:
    #     return
    if True:
        # Declaration go before the code
        if t not in var_definitions:
            var_definitions[t] = {}
        var_definitions[t][var] = 1
    else:
        # In-place declarations
        c('{0} {1} $align;', t, var)

def def_var_default(var):
    def_var('$type', var)
def def_var_vector(var):
    def_var('__m128i', var)

def gen_var_defs():
    for i in var_definitions:
        vs = var_definitions[i]
        c_prepend('{0} {1} $align;', i, " $align, ".join(vs.keys()))

types = {}

# ######################################################################
# b_* - definitions of functions to handle each bytecode instruction.
# b_v_* - vectorized, has its own section

def b_use_define(label):
    # %% parity?
    if label == 'yes':
        Global.c_output.use_define.insert(0, True)
    else:
        Global.c_output.use_define.pop(0)

def b_new_const(name, value):
    # %% handle $suffix according to output type, not algo's type
    c('#define {0} {1}$suffix', name, value)

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

def b_input_key(name):
    types[name] = 'string'
    if Global.c_output is g:
        c('#define {0} (argv[1])', name)
        # c('#define {0} ((const char *)saved_key[index/MMX_COEF_SHA512 + myindex])', name)
    elif Global.c_output is funcs:
        c('#define {0} (state->buf)', name)
    else:
        not_implemented()

def b_input_salt(name):
    types[name] = 'string'
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
        # }}''', var, len(g.out_names))
        # c('''
        # for (i = 0; i < $size; i++) {{
        #     ((unsigned char*)&( (($type*)(crypt_out[index/MMX_COEF_SHA512]))[myindex + {1} * MMX_COEF_SHA512] ))[i] = ((unsigned char*)&{0})[$size - i - 1];
        # }}''', var, len(g.out_names))
        c('''
(($type*)(crypt_out[index/MMX_COEF_SHA512]))[myindex + {1} * MMX_COEF_SHA512] = {0};
        ''', var, len(g.out_names))
        g.out_names.append(var)
    elif Global.c_output is funcs:
        c('result->H[{0}] = {1};', len(funcs.out_names), var)
        funcs.out_names.append(var)
    else:
        not_implemented()

def b_input(name):
    # В момент вывода отметки о входах должны быть убраны.
    # bad_instruction()
    c('#define {0} ((($type*)saved_key[index/MMX_COEF_SHA512])[myindex + {1} * MMX_COEF_SHA512])',
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

lengths = { '_count': 0 }

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
    if arr in types and types[arr] == 'string':
        print >> sys.stderr, name, arr, idx
        # Если мы индексируем строку, то это означает взять инт из
        # неё, а не байт.
    elif arr in types and types[arr] == 'digest':
        # c('$type {0} = ({1}->H[{2}]);', name, arr, idx)
        a('$type {0} = ({1}->H[{2}]);', name, arr, idx)
    else:
        # %% use '#define' to allow assignments
        # c('$type {0} = ({1}[{2}]);', name, arr, idx)
        a('$type {0} = ({1}[{2}]);', name, arr, idx)

def b___invert__(name, arg):
    # c('$type {0} = ~{1};', name, arg)
    a('$type {0} = ~{1};', name, arg)

def b_ror(name, arg1, arg2):
    # c('$type {0} = ror({1}, {2});', name, arg1, arg2)
    a('$type {0} = ror({1}, {2});', name, arg1, arg2)

# def b_rol(name, arg1, arg2):
#     c('$type {0} = rol({1}, {2});', name, arg1, arg2)

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
    types[state_name] = 'digest_state'
    # load_iuf(algo)
    c('struct digest_state* {0} = init();', state_name)

def b_update(state_name, string, length):
    c('update({0}, {1}, {2});', state_name, string, length)

def b_final(digest_name, state_name):
    types[digest_name] = 'digest'
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
    c('printf("  {0} is 0x $formatx %lld\\n", {0}, {0});', name)

def b_goto(label):
    # %% automatic names?
    c('goto {0};', label)

def b_label(label):
    # %% 1; is a workaround to put labels anywhere, kind of noop.
    c('{0}: (void)1;', label)

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
# vectorized versions b_v_*

def b_v_input(name):
    # В момент вывода отметки о входах должны быть убраны.
    # bad_instruction()
    # c('''
    # for (i = 0; i < 16; i++) {{
    #     printf("%02x", ((unsigned char *)&(((__m128i*)(saved_key[index/MMX_COEF_SHA512]))[{1}]))[i]);
    # }}
    # printf("\\n");
    # ''', name, len(g.inputs))
    # c('#define {0} _mm_load_si128(&(((__m128i*)(saved_key[index/MMX_COEF_SHA512]))[{1}]))',
    a('__m128i {0} = _mm_load_si128(&(((__m128i*)(saved_key[index/MMX_COEF_SHA512]))[{1}]));',
    name, len(g.inputs))
    g.inputs.append(name)

def b_v_output(var):
    if Global.c_output is g:
        # _mm_store_si128((__m128i *) &(crypt_out[index/MMX_COEF_SHA512][{1}]), {0});
        c('''
_mm_store_si128(&(((__m128i*)(crypt_out[index/MMX_COEF_SHA512]))[{1}]), {0});
        ''', var, len(g.out_names))
        g.out_names.append(var)
    # elif Global.c_output is funcs:
    #     c('result->H[{0}] = {1};', len(funcs.out_names), var)
    #     funcs.out_names.append(var)
    else:
        not_implemented()

def b_v_new_const(name, value):
    # %% handle $suffix according to output type, not algo's type
    # %% make an option to choose between set1 and load
    c('#define {0} _mm_set1_epi64x({1}$suffix)', name, value)
    # c('#define {0} _mm_set_epi64x({1}$suffix, {1}$suffix)', name, value)
    # # %% correct $type here
    # c_prepend('static unsigned long long {0}_stored[4] __attribute__((aligned(16))) = {{ {1}$suffix, {1}$suffix, {1}$suffix, {1}$suffix }};', name, value)
    # c('#define {0} _mm_load_si128((__m128i *){0}_stored)', name)

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
    a('__m128i {0} = _mm_roti_epi64({1}, {2});', name, arg1, arg2)

v_bin_ops = {
'__add__': '_mm_add_epi64',
'__sub__': '_mm_sub_epi64',
'__xor__': '_mm_xor_si128',
'__mul__': '_mm_mullo_epi64',
'__rshift__': '_mm_srli_epi64',
'__lshift__': '_mm_slli_epi64',
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
    # c('__m128i {0} = _mm_xor_si128({1}, _mm_set1_epi32(0xFFFFFFFF));', name, arg)
    bad_instruction()

def b_v___getitem__(name, arr, idx):
    # %% use '#define' to allow assignments
    a('__m128i {0} = ({1}[{2}]);', name, arr, idx)

b_v_set_item = b_set_item

def b_v_print_var(name):
    c('''
    _mm_store_si128(&tmp, {0});
    printf(" 0x $formatx 0x $formatx\\n", *(unsigned long long*)&tmp, *((unsigned long long*)&tmp + 1));
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
    for l in code:
        if l[0] in bytecode_functions:
            bytecode_functions[l[0]](*l[1:])
        else:
            raise Exception("unknown instruction [{0}]".format(", ".join(l)))
    gen_var_defs()

def gen(code, template, args, additional_replacements = {}):
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
    if len(g.out_names) > 0:
        # c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(g.out_names)), ', '.join(g.out_names))
        if args['use_bitslice']:
            print_bs(g.out_names)
    # replace various global vars like size and type
    def subst_vars(code):
        # %% align only arrays?
        # ** During debugging, __attribute__ slows down coloring of .c
        #  * file in emacs.
        align = '__attribute__((aligned(16)))'
        align = ''
        return Template(code).safe_substitute(type = g.o_type, formatx = g.o_format_x, bits = g.bits, size = g.size, suffix = g.o_suffix, align = align)
    # g.code = subst_vars(g.code)
    # g.funcs_code = subst_vars(g.funcs_code)
    # print code_template.safe_substitute(code = g.code, funcs = g.funcs_code)
    print subst_vars(Template(template).safe_substitute(code = g.code, funcs = funcs.code, **additional_replacements))

def main(code, args):
    # %% copy-pasted, see gen()
    # %% стоит вынести ror/rol, можно раскрывать в другие операции
    sha512 = B.get_code_full('iuf', False, False, { 'size': 8 })
    Global.c_output = funcs
    c('#define ror(a, b) (((a) << ($bits - (b))) | ((a) >> (b)))')
    c('#define rol(a, b) (((a) >> ($bits - (b))) | ((a) << (b)))')
    out_all(sha512)
    Global.c_output = g
    out_all(code)
    # print >> sys.stderr, temp
    # c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(temp)), ', '.join(temp))
    if len(g.out_names) > 0:
        c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(g.out_names)), ', '.join(g.out_names))
        if args['use_bitslice']:
            print_bs(g.out_names)
    # replace various global vars like size and type
    def subst_vars(code):
        return Template(code).safe_substitute(type = g.o_type, formatx = g.o_format_x, bits = g.bits, size = g.size, suffix = g.o_suffix)
    # g.code = subst_vars(g.code)
    # g.funcs_code = subst_vars(g.funcs_code)
    # print code_template.safe_substitute(code = g.code, funcs = g.funcs_code)
    print subst_vars(Template(template).safe_substitute(code = g.code, funcs = funcs.code))
    # gen(code, code_template, args)


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


