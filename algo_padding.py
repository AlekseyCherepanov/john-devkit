# -*- coding: utf-8 -*-
# экспериментальный набросок абстрактного кода для паддинга сообщения
# для sha512

# %% ограничение в 128 байт, энфорсить или отказаться, или сделать итератор

# на входе: строка байтов
# на выходе: 16 64-битных интов
# %% возможно, мне тут нужно что-то типа итератора, чтобы строку можно
#  % было бить на блоки продолжительно

Var.setup('be', 8)

s = input_string()

l = to_be(s.get_bit_length())

o = s.get_ints_with_bit_on_the_end(14)

o1 = Const(0)

for v in o:
    output(v)
# # The length is 16-byte long BE number, we use 8 bytes, so we switch
# # halves manually
# output(l)
# output(o1)
output(o1)
output(l)
