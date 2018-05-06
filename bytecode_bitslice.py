# -*- coding: utf-8 -*-
# bitslice() function, in a separate file

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from util_main import *
from bytecode_util import new_name

# %% надо слить со старой версией; эта версия new_array не заменяет
def bitslice(code):
    # проходим по коду и заменяем часть операций на новые; ведём
    # таблицу имён: имя -> вектор битов
    bits = None
    size = None
    new_code = []
    names = {}
    consts = {}
    saved_consts = {}
    # Создаём константы для 0 и 1
    bs_zero = new_name()
    new_code.append(["bs_new_const", bs_zero, 0])
    bs_one = new_name()
    new_code.append(["bs_new_const", bs_one, 1])
    # Проходим код, чтобы записать константы, которые не надо
    # битслайсить. В этом плане, битслайс очень похож на векторизацию.
    # не все константы надо векторизовывать, размеры битовых
    # сдвигов/ротейтов не надо
    # %% надо бы проверять, что константы не используются в разных
    #  % местах и разделять на векторную и скалярную
    # %% Copy-pasting is evil! Copied from vectorize()
    no_vec = {}
    array_vars = {}
    for l in code:
        if l[0] == 'cycle_const_range':
            array_vars[l[1]] = 1
            # %% это наверное надо и в vectorize добавить
            no_vec[l[3]] = 1
            no_vec[l[4]] = 1
            no_vec[l[5]] = 1
        if l[0] in ['ror', 'rol', '__rshift__', '__lshift__', '__getitem__', 'make_array']:# or (l[0].startswith('cycle_') and l[0] != 'cycle_end'):
            no_vec[l[3]] = 1
        if l[0] in ['set_item']:
            no_vec[l[2]] = 1
        if l[0] == '__sub__' and l[2] in array_vars:
            # %% очередной костыль...
            # %% эта проверка копируется для самой операции вычитания
            # %% любой аргумент, а не только левый
            # Проверяем, что левый аргумент является переменной цикла.
            # Тогда не векторизуем константу, которая вычитается.
            no_vec[l[3]] = 1
        # if l[0] not in to_vector:
        #     for i in l[1:]:
        #         no_vec[i] = 1
        if l[0] == 'make_array':
            # Размер массива
            no_vec[l[2]] = 1
        # if l[0] == 'sbox' and ('b_var40682' in no_vec or 'b_var9225' in no_vec or 'b_var42193' in no_vec):
        #     print >> sys.stderr, l
        #     exit()
    tables = {}

    for l in code:
        # Собираем константы
        if l[0] == 'new_const':
            consts[l[1]] = l[2]
        # Собираем таблицы
        if l[0] == 'new_array':
            tables[l[1]] = [int(consts[i]) for i in l[3:]]

    # Обрабатываем код
    for l in code:
        # %% надо сделать различную генерации в зависимости от размера
        #  % выходных векторов
        if l[0] == 'var_setup':
            size = int(l[1])
            bits = size * 8
            new_code.append(l)
            continue
        if l[1] in no_vec:
            # Добавляем инструкции, которые не надо битслайсить, как есть
            if l[0] == 'sbox':
                print >> sys.stderr, "skip", l
            # Если инструкция использует константы, то мы и их
            # сохраняем тоже.
            if l[0] == 'new_const':
                saved_consts[l[1]] = 1
            else:
                for e in l[1:]:
                    if e in consts and e not in saved_consts:
                        new_code.append(['new_const', e, consts[e]])
                        saved_consts[e] = 1
            new_code.append(l)
            continue
        if l[0] == 'make_array':
            new_code.append(["bs_" + l[0]] + l[1:])
        elif l[0] == 'new_array':
            # Мы сплошным списком держим биты, вывод в код должен
            # сделать двумерный массив по количеству битов
            def flatten(a):
                return map([].__iadd__, a)[0]
            vname = l[1]
            aname = l[2]
            elements = l[3:]
            new_code.append(["bs_" + l[0], vname, aname] + flatten([names[n] for n in elements]))
        elif l[0] == '__getitem__':
            v = []
            for i in range(bits):
                n = new_name()
                v.append(n)
                # Взятие элемента из массива теперь ещё несёт бит
                new_code.append(["bs_getitem", n, l[2], l[3], i])
            names[l[1]] = v
        elif l[0] == 'set_item':
            # set_item(array, idx, value)
            # bs_set_item(array, idx, value, bit)
            for i, j in zip(range(bits), names[l[3]]):
                new_code.append(['bs_set_item', l[1], l[2], j, i])
        elif l[0] == 'new_var':
            v = []
            for i in range(bits):
                n = new_name()
                v.append(n)
                new_code.append(['bs_new_var', n])
            names[l[1]] = v
        elif l[0] in ['print_var', 'output']:
            for i, j in enumerate(names[l[1]]):
                new_code.append(['bs_' + l[0], j, i])
        elif l[0] == 'input':
            v = []
            for i in range(bits):
                n = new_name()
                v.append(n)
                new_code.append(['bs_input', n, i])
            names[l[1]] = v
        elif l[0] == 'input_length':
            v = []
            for i in range(bits):
                n = new_name()
                v.append(n)
                new_code.append(['bs_input_length', n, i])
            names[l[1]] = v
        elif l[0] in ['__xor__', '__or__', '__and__']:
            op = 'bs_' + l[0].replace('_', '')
            # для аргументов берём пары из векторов, для каждой пары
            # делаем новую операцию, вектор новых имён запоминаем
            v = []
            for i, j in zip(names[l[2]], names[l[3]]):
                n = new_name()
                v.append(n)
                new_code.append([op, n, i, j])
            names[l[1]] = v
        elif l[0] == '__invert__':
            # %% copy-pasting is evil! тут можно было подсократить,
            #  % потому что скопирован код
            op = 'bs_' + l[0].replace('_', '')
            v = []
            for i in names[l[2]]:
                n = new_name()
                v.append(n)
                new_code.append([op, n, i])
            names[l[1]] = v
        elif l[0] == '__getitem__':
            # __getitem__(name, array, idx)
            # bs_getitem(name, array, idx, bit)
            # Подобно другим операциям, но при взятии элемента, ещё
            # номер бита указывается.
            # %% В некоторых хешах всё-таки нужно делать битовые
            #  % индексы (например, в sunmd5 на этапе coin flip). Там
            #  % они не константы, операция при этом должна быть другой.
            op = 'bs_' + l[0].replace('_', '')
            v = []
            for i in range(bits):
                n = new_name()
                v.append(t)
                new_code.append([op, n, l[2], l[3], i])
            names[l[1]] = v
        elif l[0] == '__add__':
            # op = lambda *args: new_code.append('bs_{2} {0} {1} {3}'.format(*args))
            op = lambda r, a, op, b: new_code.append(['bs_' + op, r, a, b])
            a = names[l[2]]
            b = names[l[3]]
            # создаём все имена впрок
            # (возможно, есть лишние, это не страшно)
            r, n, x, q, w = [[new_name() for j in range(i)]
                            for i in [bits] * 5]
            # r - result bit
            # n - carry bit
            for i in reversed(range(bits)):
                if i == bits - 1:
                    op(r[i], a[i], 'xor', b[i])
                    op(n[i], a[i], 'and', b[i])
                else:
                    op(x[i], a[i], 'xor', b[i])
                    op(r[i], x[i], 'xor', n[i + 1])
                    # %% Better circuit here.
                    # n[i] = b[i] ^ (x[i] & (b[i] ^ n[i + 1]))
                    op(w[i], b[i], 'xor', n[i + 1])
                    op(q[i], x[i], 'and', w[i])
                    op(n[i], b[i], 'xor', q[i])
            names[l[1]] = r
        elif l[0] == '__floordiv__':
            # assignment
            # %% rotate has problems overriding values: a = rol(a, 1)
            #  % is broken; maybe temp vars can solve that
            #  % (предположительно, компилятор уберёт ненужные)
            # Для всех пар битов, присваиваем правый в левый.
            for i, j in zip(names[l[1]], names[l[2]]):
                new_code.append(['bs_assign', i, j])
        elif l[0] == 'new_const':
            # Режем константу на биты и запоминаем в виде вектора
            # битов.
            c = int(l[2])
            # ** Биты идут со старших: старшие биты - в начале вектора,
            #  * младшие - в конце. Начало вектора - слева, конец -
            #  * справа. Соответствует битовым сдвигам.
            names[l[1]] = [bs_one if c & (1 << i) else bs_zero for i in range(bits - 1, -1, -1)]
        elif l[0] == '__rshift__':
            # We just manipulated names.
            # У нас 3 аргумента: результат, переменная, сдвиг.
            # В таблицу имён мы присваиваем сдвинутый вектор,
            # дополненный нулями, нужны нули. Операции при этом не
            # получается.
            s = int(consts[l[3]])
            names[l[1]] = [bs_zero] * s + names[l[2]][: bits - s]
        elif l[0] == 'low':
            a = names[l[2]]
            assert len(a) == 2 * bits
            # names[l[1]] = a[len(a) - bits :]
            names[l[1]] = a[bits :]
        elif l[0] == 'high':
            a = names[l[2]]
            assert len(a) == 2 * bits
            names[l[1]] = a[: bits]
        elif l[0] == 'combine_low_high':
            names[l[1]] = names[l[3]] + names[l[2]]
        elif l[0] == '__lshift__':
            s = int(consts[l[3]])
            names[l[1]] = names[l[2]][s :] + [bs_zero] * s
        elif l[0] == 'ror':
            # Как сдвиг, только мы не дополняем нулями, а берём другой
            # кусок.
            s = int(consts[l[3]])
            names[l[1]] = names[l[2]][bits - s :] + names[l[2]][: bits - s]
        elif l[0] == 'rol':
            s = int(consts[l[3]])
            names[l[1]] = names[l[2]][s :] + names[l[2]][: s]
        elif l[0] == 'permute':
            # Как сдвиг, только биты переставляются произвольно.
            names[l[1]] = [bs_zero] * bits
            table = tables[l[3]]
            var = names[l[2]]
            for i in range(len(table)):
                names[l[1]][i] = var[table[i]]
        elif l[0] == 'swap_to_be':
            names[l[1]] = bs_swap_bytes(names[l[2]], size)
            # # %% swap_to* is noop now. This implementations "works" in BE.
            # names[l[1]] = names[l[2]]
        elif l[0] == 'sbox':
            # Вставляем схему, и паддим до полного числа; берём
            # только нужные биты; используются младшие биты - те, что
            # справа
            table, n_inputs, n_outputs = bs_pick_sbox(tables[l[3]])
            # Берём имена входов из общей схемы
            orig_inputs = names[l[2]][bits - n_inputs:]
            outputs = []
            substs = {}
            # Добавляем инструкции, переименовывая всё
            for al in table:
                if al[0] == 'input':
                    orig_name = orig_inputs.pop(0)
                    substs[al[1]] = orig_name
                elif al[0] == 'output':
                    outputs.append(substs[al[1]])
                else:
                    # Для всех остальных операций мы заменяем все
                    # аргументы по таблице, а для результата создаём
                    # новое имя. Инструкцию сохраняем.
                    op = 'bs_' + al[0].replace('__', '')
                    substs[al[1]] = new_name()
                    new_code.append([op] + [substs[n] for n in al[1:]])
            # Код встроен. Надо по массиву выходов сделать запись в
            # таблице раскрытия имён, добавив нули слева.
            names[l[1]] = [bs_zero] * (bits - n_outputs) + outputs
        elif l[0] == 'new_array':
            # We skip this op.
            pass
        elif l[0] == 'label':
            # We skip this op.
            pass
        else:
            # operation that should not be bitsliced, pass as is
            print >> sys.stderr, "warning: passed as is:", l
            new_code.append(l)
    return new_code
