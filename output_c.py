# -*- coding: utf-8 -*-
# библиотека для вывода кода в скалярный си в отдельном файле

from string import Template
from bytecode_main import drop, clean

size_type = {
    8: 'unsigned long long',
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

class Global:
    g = None
    def __init__(self):
        self.code = ''
        self.out_names = []
        self.bit_lengths = {}
        self.bit_length_bits = []
        if Global.g == None:
            Global.g = self
        else:
            raise Exception('Global is singleton')

g = Global()

# функция добавления кода в глобальную строку
def c(code, *args):
    Global.g.code += code.format(*args) + "\n"

# %% move it, handle $suffix according to output type, not algo's type
# все константы и переменные состояния можно сделать дефайнами
def out_const(code):
    for l in code:
        if l[0] == 'const' or (l[0] == 'declare' and len(l) == 5):
            c('#define {0} {1}$suffix', l[1], l[2])
            l[0] = drop
    return clean(code)

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

def out_all(code):
    bits = g.bits
    c('size_t i, len;')
    for l in code:
        if l[0] == 'op':
            # op sha512_var634 sha512_var632 sha512_var633 ^
            if l[4] == 'bit_length':
                c('size_t {0} = strlen({1}) * 8;', l[1], l[2])
                c('printf(">> $formatx\\n", {0});', l[1])
            elif l[4] == 'to_be':
                # to big endian
                # %% быстрее
                # %% использовать переменную?
                # %% почему это не нужно?
                #c('#define {0} ({1})', l[1], " | ".join('((({1} & (0xff << ({0} * 8))) >> ({0} * 8)) << ((8 - {0} - 1) * 8))'.format(i, l[2]) for i in range(8)))
                c('#define {0} {1}', l[1], l[2])
                c('printf(">> $formatx\\n", {0});', l[1])
            elif l[4] == 'noop':
                # %% другие типы, параметризация этого
                # %% описание типов у операций
                c('$type {0};', l[1])
            elif l[4] == '~':
                c('$type {0} = {3}{1};', *l[1:])
            elif l[4] == 'getitem':
                c('$type {0} = {1}[{2}];', *l[1:])
            elif l[4] == 'ror' or l[4] == 'rol':
                c('$type {0} = {3}({1}, {2});', *l[1:])
            else:
                c('$type {0} = {1} {3} {2};', *l[1:])
        elif l[0] == 'declare_string':
            # declare_string padding_input_string0
            # %% это заглушка для связи, нужна параметризация
            c('#define {0} (argv[1])', l[1])
        elif l[0] == 'bitslice_string_get_ints_with_bit_on_the_end':
            # %% update it
            # string_get_ints padding_input_string0 be 8 14 padding_var2 ...
            # %% быстрее?
            # %% опять тип
            # %% обработка того же эндианнесса
            # %% проверка, что типы совпадают заявленному
            # раскладываем на биты
            string = l[1]
            number = l[4]
            # двумерный массив: [число1:[бит1,бит2...], ...]
            c('len = strlen({0});', string)
            names = partition(l[5:], bits)
            for i, ns in enumerate(names):
                for j, n in enumerate(ns):
                    # для каждого бита в каждом числе берём бит из
                    # строки
                    # %% несколько строк
                    # %% длина
                    # %% optimize
                    c('''
                    if ({2} * $bits + {3} < len * 8) {{
                        {0} = ((($type *){1})[{2}] & (1$suffix << ($bits - (($size - 1 - {3} / 8) * 8 + {3} % 8) - 1))) >> ($bits - (($size - 1 - {3} / 8) * 8 + {3} % 8) - 1);
                    }} else {{
                        {0} = ({2} * $bits + {3} == len * 8);
                    }}
                    ''', n, string, i, j)
            print_bs(l[5:])
        elif l[0] == 'string_get_ints':
            # %% use string_get_ints_with_bit_on_the_end
            # string_get_ints padding_input_string0 be 8 14 padding_var2 ...
            # %% быстрее?
            # %% опять тип
            # %% обработка того же эндианнесса
            # %% проверка, что типы совпадают заявленному
            names = l[5:]
            s = l[1]
            c('len = strlen({0});', s)
            for i, n in enumerate(names):
                # %% optimize strlen with already used op-strlen
                # %% optimize
                c('''
                for (i = 0; i < $size; i++) {{
                    ((char *)&{0})[$size - i - 1] = ($size * {2} + i < len ? {1}[$size * {2} + i] : 0);
                }}''', n, s, i)
                # c('printf(">> %016llx\\n", {0});', n)
            # в конец цепляем бит
            # %% надо это вынести
            # %% реализовать
            # c('((char *)&{0})[0] = 0x80;', names[0])
            c('((char *)&{0})[0] = 0x80;', names[13])
            c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(names)), ', '.join(names))
        elif l[0] == 'comment':
            c('/* {0} */', " ".join(l[1:]))
            if l[1] == 'input:':
                c('printf("input: {0}\\n", {1});', ' '.join(('$formatx',) * len(l[2:])), ', '.join(l[2:]))
        elif l[0] == 'bitslice_array':
            # array array_w padding_var2 padding_var3 ...
            # %% type again, derive it from variables
            c('$type {0} [][$bits] = {{ {{ {1} }} }};', l[1], "}, {".join(', '.join(v) for v in partition(l[2:], bits)))
        elif l[0] == 'array':
            # array array_w padding_var2 padding_var3 ...
            # %% type again, derive it from variables
            c('$type {0} [] = {{ {1} }};', l[1], ", ".join(l[2:]))
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
        elif l[0] == 'bitslice_bit_length':
            # bit_length padding_var0 padding_input_string0 0
            # для взятия длины у нас много операций идёт, каждая даёт
            # 1 бит, номер бита задан в конце
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
            c('$type {0} = ({1}_bit_length & (1$suffix << {2})) >> {2};', *l[1:])
            g.bit_length_bits.append(l[1])
            if len(g.bit_length_bits) % bits == 0:
                print_bs(g.bit_length_bits)
                g.bit_length_bits = []
        elif l[0] == 'bitslice_debug_print_var':
            v = l[1:bits+1]
            comment = " ".join(l[bits+1:])
            # %% quoting
            c('printf("%s:", "{0}");', comment)
            print_bs(v)
        elif l[0] == 'debug_print_var':
            comment = " ".join(l[2:])
            # %% quoting
            c('printf("%s: $formatx\\n", "{0}", {1});', comment, l[1])
        elif l[0] == 'output':
            # output sha512_var661
            g.out_names.append(l[1])
        elif l[0] == 'bitslice_getitem':
            c('$type {0} = {1}[{2}][{3}];', *l[1:])
        else:
            raise Exception("unknown instruction [{0}]".format(", ".join(l)))

def main(code, args):
    code = out_const(code)
    c('#define ror(a, b) (((a) << ($bits - (b))) | ((a) >> (b)))')
    c('#define rol(a, b) (((a) >> ($bits - (b))) | ((a) << (b)))')
    out_all(code)
    c('printf("{0}\\n", {1});', ' '.join(('$formatx',) * len(g.out_names)), ', '.join(g.out_names))
    if args['use_bitslice']:
        print_bs(g.out_names)
    # replace various global vars like size and type
    g.code = Template(g.code).safe_substitute(type = g.o_type, formatx = g.o_format_x, bits = g.bits, size = g.size, suffix = g.o_suffix)
    print code_template.safe_substitute(code = g.code)


# %% стоит вынести ror/rol, можно раскрывать в другие операции
code_template = Template("""
#include <stdio.h>
#include <string.h>

int main(int argc, const char ** argv)
{
    if (argc < 1)
        return 1;

/* #define ror(a, b) (((a) << (sizeof(a)*8 - (b))) | ((a) >> (b))) */
/* #define rol(a, b) (((a) >> (sizeof(a)*8 - (b))) | ((a) << (b))) */

    $code

    return 0;
}
""")
# %% вывод со вставкой имён
# %% эндианнес при выводе?


