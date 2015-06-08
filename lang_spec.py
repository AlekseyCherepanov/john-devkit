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


spec = """
num new_const(const_num)
num new_var()
num new_state_var(const_num)
array new_array(label, *num)
num input_rounds()
string input_key()
string input_salt()
void output(num)
num input()

num __add__(num, num)
num __sub__(num, num)
num __xor__(num, num)
num __mul__(num, num)
num __rshift__(num, num)
num __lshift__(num, num)
num __and__(num, num)
num __or__(num, num)
void __floordiv__(!num, num)
num __invert__(num)
num __getitem__(array, num)
num __mod__(num, num)

num __le__(num, num)
num __lt__(num, num)
num __ge__(num, num)
num __gt__(num, num)
num __eq__(num, num)
num __ne__(num, num)

num ror(num, num)
num rol(num, num)

num get_length(string)

num cycle_const_range(label, const_num, const_num, const_num)
num cycle_range(label, num, num, num)
void cycle_while_begin(label)
void cycle_while(label, condition)
void cycle_end(label)

void label(label)
void goto(label)

string digest_to_string(digest)
string fill_string(num, string)

void if_condition(label, condition)
void if_else(label)
void if_end(label)

digest_state init(label)
void update(!digest_state, string)
digest final(digest_state)

void put0x80(!string, num)
num get_int(string, num, num)
num get_int_raw(string, num)
void put_int(!string, num, num)

void set_item(!array, num, num)
array make_array(label, num)

string string_copy_and_extend(string, num, num)
void free(!string)

void print_buf(string, num)
void print_var(num)
void print_digest(digest)

num v_andnot(num, num)

void use_define(label)

num swap_to_be(num)

num get_from_key_0x80_padding_length(string)

void check_output(num)

void print_verbatim(label)

"""

# %% some of instruction defined here are not suitable for users,
#  % define separately?

class Instruction:
    pass
instructions = {}

def parse_spec(text):
    # разбираем spec
    for l in text.split('\n'):
        if l == '':
            continue
        m = re.match(r'^(\w+) (\w+)\(((?:(?:[!*]?\w+)(?:, )?)*)\)', l)
        if not m:
            raise Exception("can't parse spec: {0}".format(l))
        # %% check errors
        return_type = m.group(1)
        name = m.group(2)
        arguments = m.group(3).split(', ')
        i = Instruction()
        i.return_type = return_type
        i.name = name
        i.args = arguments
        instructions[name] = i

parse_spec(spec)
