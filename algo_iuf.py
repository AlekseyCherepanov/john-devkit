# -*- coding: utf-8 -*-
# абстрактный код для sha512 не на одном блоке

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

# Var.setup('be', args['size'])

sha = algo_load('sha512')
block_int_count = algo_get_block_int_count(sha)

s = input_key()

l = get_length(s)

print_var(l)
print_buf(s, 128)

# %% 8 - размер
block_size = block_int_count * 8
# %% 16 bytes is for length, 1 byte is for 0x80
additional_size = 16 + 1
partial_size = block_size - additional_size

partial = l % block_size
# nl = l - partial
# if_condition('extending', partial <= partial_size)
# nl += block_size
# if_else('extending')
# nl += 2 * block_size
# if_end('extending')

nl = l - partial + block_size
if_condition('extending', partial > partial_size)
# nl += block_size
nl // (nl + block_size)
if_end('extending')

# print_var(partial)

# print_buf(s, l)

# дополняем до полных блоков
buf = string_copy_and_extend(s, l, nl)

put0x80(buf, l)

# print_buf(buf, nl)

# o1 = new_const(0)
o2 = l * 8

# count = nl / 8
count = nl >> 3
# put_int(s, count - 2, o1)
put_int(buf, count - 1, o2)

# print_buf(buf, nl)

# %% а заполнить нулями? string_copy_and_extend должна забивать нулями

state_init = algo_get_initial_state(sha)
state = []
for i in state_init:
    v = new_var()
    v // i
    state.append(v)

# k = new_var()
# k // 0
# # %% replace with 'while'
# label('blocks')
# if_condition('blocks_if', k >= count)
# goto('blocks_end')
# if_end('blocks_if')
# %% make not inclusive range to avoid 'count - 1' like [0, count)
k = cycle_range('blocks', 0, count - 1, block_int_count)
# cycle_while('blocks', k < count)

# %% мы длину переворачиваем дважды; при анроле последнего блока от
#  % этого можно избавиться
block = [get_int_raw(buf, k + i) for i in range(block_int_count)]
# for i in block:
#     print_var(i)
new_state = algo_insert(sha, *(block + state))
# for i in new_state:
#     print_var(i)
for i in range(len(state)):
    state[i] // new_state[i]

# k // (k + 16)
# goto('blocks')
# label('blocks_end')
cycle_end('blocks')

# %% do that automatically?
free(buf)

for v in state:
    output(v)
