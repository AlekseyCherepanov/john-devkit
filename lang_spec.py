# -*- coding: utf-8 -*-
# описание инструкций

# Copyright © 2015 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import re

# в байткоде у нас есть числа, строки, числа-константы, переменные
# цикла, массивы, дайджесты и промежуточные состояния, метки; все
# операции, кроме присваивания, создают новую переменную, однако
# некоторые функции могут менять; ещё бывают состояния

# у некоторых функций есть тип condition - по выполнению это число

# в коде помимо этого могут быть константы и массивы; строковые
# константы скорее всего будут метками

# в качестве числа может быть передана константа

# %% хм, cycle_const_range и cycle_range можно различить по типам
#  % параметров


# num new_const(const_num)
# 'label' means pass "as is"

spec = """
const_num new_const(label)
num new_var()
num new_state_var(const_num)

array new_array(label, *num)
array make_array(label, const_num)

#                     idx  value
void set_item(!array, num, num)

num input()
num input_rounds()
bytes input_key()
bytes input_salt()
bytes input_salt2()

void output(num)
void output_bytes(bytes)

num __add__(num, num)
num __sub__(num, num)
num __xor__(num, num)
num __mul__(num, num)
num __div__(num, num)
num __rshift__(num, num)
num __lshift__(num, num)
num __and__(num, num)
num __or__(num, num)
num __invert__(num)
num __getitem__(array, num)
num __mod__(num, num)

bool __le__(num, num)
bool __lt__(num, num)
bool __ge__(num, num)
bool __gt__(num, num)
bool __eq__(num, num)
bool __ne__(num, num)
# assignment
void __floordiv__(!num, num)

num ror(num, num)
num rol(num, num)
num andnot(num, num)

num v_andnot(num, num)

num cycle_const_range(label, const_num, const_num, const_num)
num cycle_range(label, num, num, num)
void cycle_while_begin(label)
void cycle_while(label, bool)
void cycle_end(label)

void label(label)
void goto(label)

void if_condition(label, bool)
void if_else(label)
void if_end(label)

void print_var(num)
void print_many(*num)
void print_verbatim(label)
void print_bytes(bytes)
void print_hex(bytes)

void use_define(label)

num swap_to_be(num)

void check_output(num)

num permute(num, array)
# %% (array, num) would be more natural
num sbox(num, array)

void store(num, num)
num load(num)

void in_memory(num)
void in_register(num)

num bs_xor(num, num)
num bs_or(num, num)
num bs_and(num, num)
num bs_invert(num)
num bs_new_const(num)
num bs_input(num)
num bs_input_length(num)
void bs_output(num, num)
void bs_print_var(num, num)
array bs_make_array(label, num)
void bs_set_item(!array, num, num, num)
num bs_getitem(array, num, num)
num bs_new_var()
void bs_assign(!num, num)
array bs_new_array(label, *num)

num low(num)
num high(num)
num combine_low_high(num, num)

void var_setup(label, label)
void var_setup_pop()

void may_split_here(label)

void debug_exit(label)

bytes run_merkle_damgard(function, bytes)
bytes run_merkle_damgard_with_state(function, bytes, num, *num)

# the first label is for type/kind of func, the second is for comment
function module_begin(label, label)
void module_end(function)

const_num hfun_block_size(function)
const_num hfun_digest_size(function)
bytes invoke_hfun(function, bytes)
bytes invoke_hfun_with_size(function, bytes, num)
bytes invoke_fun2(function, bytes, bytes)
array invoke_plain(function, *num)

bytes new_bytes()

# %% len instead of num here
num new_bytes_len()
num bytes_len(bytes)
bytes bytes_append_zeros_up_to(bytes, num)

bytes bytes_xor_each(bytes, const_num)
bytes bytes_concat(bytes, bytes)
bytes bytes_xor(bytes, bytes)
bytes bytes_append_num(bytes, num)
bytes bytes_zeros(const_num)
bytes bytes_hex(bytes)
bytes bytes_hex_upper(bytes)

bytes new_bytes_const(label)

#    bytes_slice: data, from, to
bytes bytes_slice(bytes, num, num)

array bytes_split_to_nums(bytes, const_num)
bytes bytes_join_nums(*num)

void bytes_assign(!bytes, bytes)

void set_hfun_block_size(label)
void set_hfun_digest_size(label)

void assume_length(bytes, const_num, const_num)

"""

# %% надо ли добавить тип len()? new_bytes_len - как new_var, только с
#  % типом len

# %% не симметрично: разделяем в массив, а упаковываем отдельные;
#  % возможно, split стоит переименовать в _to_array

# %% bytes_concat might use *bytes instead of bytes, bytes

# %% bs_* operate on 'bit's, not on 'num's. Also there is bit index.
# %% it is not the full list bs_* instructions.

# %% some of instruction defined here are not suitable for users,
#  % define separately?

class Instruction:
    pass
instructions = {}

def parse_spec(text):
    # разбираем spec
    for l in text.split('\n'):
        if l == '' or l[0] == '#':
            continue
        m = re.match(r'^(\w+) (\w+)\(((?:(?:[!*]?\w+)(?:, )?)*)\)', l)
        if not m:
            raise Exception("can't parse spec: {0}".format(l))
        # %% check errors
        return_type = m.group(1)
        name = m.group(2)
        arg_str = m.group(3)
        if arg_str == '':
            arguments = []
        else:
            arguments = arg_str.split(', ')
        i = Instruction()
        i.return_type = return_type
        i.name = name
        i.args = arguments
        # all_types represents types with same indexes as arguments in
        # line of bytecode
        if return_type == 'void':
            i.all_types = [None] + i.args
        else:
            i.all_types = [None, return_type] + i.args
        instructions[name] = i

parse_spec(spec)
