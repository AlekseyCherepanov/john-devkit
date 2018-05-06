# -*- coding: utf-8 -*-
# абстрактный код паддинга сообщения длиной меньше одного блока для sha-2

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

# имеет параметризованный размер чисел (args['size'])

# %% ограничение в 128 байт, энфорсить или отказаться, или сделать итератор

# на входе: строка байтов
# на выходе: 16 64-битных интов
# %% возможно, мне тут нужно что-то типа итератора, чтобы строку можно
#  % было бить на блоки продолжительно

# print >>sys.stderr, args

Var.setup('be', args['size'])

s = input_key()

l = get_length(s)

o1 = new_const(0)

put0x80(s, l)

for i in range(14):
    output(get_int(s, i, l + 1))
# # The length is 16-byte long BE number, we use 8 bytes, so we switch
# # halves manually
# output(l)
# output(o1)
output(o1)
output(l * 8)
