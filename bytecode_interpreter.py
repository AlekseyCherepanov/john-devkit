# -*- coding: utf-8 -*-
# interpret() function, in a separate file

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from bytecode_util import *

from lang_spec import instructions
from util_main import *

# padding function
def make_merkle_damgard(msg_end_char):
    def merkle_damgard(endianness, size, s):
        block = size * 16
        ll = len(s)
        l = ll % block
        if l <= block - size * 2 - 1:
            zeros = block - size * 2 - 1 - l
        else:
            zeros = 2 * block - size * 2 - 1 - l
        s += msg_end_char
        s += '\0' * zeros
        ll <<= 3
        ll_bin = '{{0:0{0}x}}'.format(size * 2 * 2).format(ll).decode('hex')
        if endianness == 'le':
            # reverse order of bytes
            ll_bin = ''.join(reversed(ll_bin))
        s += ll_bin
        return s
    return merkle_damgard

merkle_damgard = make_merkle_damgard('\x80')
# merkle_damgard0x01 = make_merkle_damgard('\x01')

def split_to_ints(endianness, size, s):
    r = []
    for i in range(0, len(s), size):
        w_bin = s[i : i + size]
        if endianness == 'le':
            w_bin = ''.join(reversed(w_bin))
        r.append(int(w_bin.encode('hex'), 16))
    # print s
    # print r, len(r)
    return r

def int_to_hex(num, size, endianity):
    s = '{{0:0{0}x}}'.format(size * 2).format(num)
    if endianity == 'le':
        s = ''.join(list(reversed(s.decode('hex')))).encode('hex')
    return s

# If 'results' are given, then we check against them.
# If 'results' is 'run' (string), then we run silently and return
# values instead of code.
def interpret(code, data, results = None, key = None, initial_state = None, salt = None, rounds = None, salt2 = None, upper_modules_and_mt = None, ifs = None):
    # bytecode evaluator for debugging
    values = {}
    sizes = {}
    size = None
    arrays = {}
    bs_arrays = {}
    result_values = []
    output_value = 0
    cycles = {}

    modules, modules_types = extract_modules(code)
    if upper_modules_and_mt == None:
        upper_modules_and_mt = (modules, modules_types)
        ifs = collect_ifs(code)
    else:
        m2, mt2 = upper_modules_and_mt
        for m in m2:
            if m == '_main':
                continue
            if m in modules:
                die('upper has same module')
            modules[m] = m2[m]
            modules_types[m] = mt2[m]
    code = modules['_main']

    def handle_output(v):
        # if sizes[v] == 8:
        if size == 8:
            f = '{0:016x}'
        # elif sizes[v] == 4:
        elif size == 4:
            f = '{0:08x}'
        elif size == 1:
            f = '{0:02x}'
        else:
            # print >> sys.stderr, size
            die('unimplemented size')
        if results != None and results != 'run':
            r = results.pop(0)
            if v != r:
                print >> sys.stderr, bits
                die('test failure: {0}, expected {1}',
                    f.format(v),
                    f.format(r))
        elif results == 'run':
            result_values.append(v)
        else:
            print >> sys.stderr, 'output:', f.format(v)

    mask32 = 2 ** 32 - 1
    # %% copy-pasted from compute_const_expressions
    ops = {
        # # %% wrap negative?
        # '__sub__': lambda a, b: a - b,
        '__sub__': lambda a, b: (a - b) & mask_int,
        '__mul__': lambda a, b: (a * b) & mask_int,
        '__div__': lambda a, b: a // b,
        '__and__': lambda a, b: a & b,
        'andnot': lambda a, b: a & (mask_int ^ b),
        'bs_andnot': lambda a, b: a & (1 ^ b),
        '__xor__': lambda a, b: a ^ b,
        '__or__': lambda a, b: a | b,
        '__invert__': lambda a: mask_int ^ a,
        'bs_invert': lambda a: 1 ^ a,
        'high': lambda a: a >> 32,
        'low': lambda a: a & mask32,
        'ror': lambda a, b: (a >> b) | ((a << (bits - b)) & mask_int),
        'rol': lambda a, b: ((a << b) & mask_int) | (a >> (bits - b)),
        '__add__': lambda a, b: (a + b) & mask_int,
        '__rshift__': lambda a, b: (a >> b),
        '__lshift__': lambda a, b: (a << b) & mask_int,
        '__eq__': lambda a, b: int(a == b)
    }
    ops['bs_and'] = ops['__and__']
    ops['bs_or'] = ops['__or__']
    ops['bs_xor'] = ops['__xor__']

    l = None

    key_already_in = False
    salt_already_in = False
    salt2_already_in = False
    rounds_already_in = False

    try:
        # for l in code:
        instruction_index = 0
        while instruction_index < len(code):
            l = code[instruction_index]
            instruction_index += 1
            if instructions[l[0]].return_type in ['num', 'array']:
                # %% а не хочу ли я запоминать типы в качестве размера
                #  % для других типов?
                # %% надо проверять, что такой переменной нет ещё
                if l[0].startswith('bs_'):
                    sizes[l[1]] = 'bit'
                else:
                    assert size != None
                    sizes[l[1]] = size
            if l[0] == 'input':
                values[l[1]] = data.pop(0)
            elif l[0] == 'bs_input':
                if l[2] == '0':
                    # это первый бит, берём новое число
                    input_value = data.pop(0)
                values[l[1]] = (input_value >> (bits - 1 - int(l[2]))) & 1
            elif l[0] == 'input_key':
                assert key != None
                assert key_already_in == False
                key_already_in = True
                values[l[1]] = key
            elif l[0] == 'input_salt':
                assert salt != None
                assert salt_already_in == False
                salt_already_in = True
                values[l[1]] = salt
            elif l[0] == 'input_salt2':
                assert salt2 != None
                assert salt2_already_in == False
                salt2_already_in = True
                values[l[1]] = salt2
            elif l[0] == 'input_rounds':
                assert rounds != None
                assert rounds_already_in == False
                rounds_already_in = True
                values[l[1]] = rounds
            elif l[0] == 'input_state':
                values[l[1]] = initial_state.pop(0)
            elif l[0] in ['set_hfun_block_size', 'set_hfun_digest_size']:
                # %% implement?
                pass
            elif l[0] == 'run_merkle_damgard' or l[0] == 'run_merkle_damgard_with_state':
                res_var, fun_var, bytes_var = l[1 : 4]
                # %% хорошо бы иметь разные варианты мд
                # паддим, режем байты на числа, вызываем функцию в
                # цикле
                # %% надо брать интерфейс
                m_code = modules[fun_var]
                s = values[bytes_var]
                fun_size = ifs[fun_var]['size']
                fun_endianity = ifs[fun_var]['endianity']
                padded = merkle_damgard(fun_endianity, fun_size, s)
                iv = None
                if l[0] == 'run_merkle_damgard_with_state':
                    offset = values[l[4]]
                    # %% implement it
                    if offset != 0:
                        dummy = 'x' * offset
                        padded = merkle_damgard(fun_endianity, fun_size, dummy + s)
                        # print 'padded1:', padded
                        padded = padded[offset :]
                        # print 'padded2:', padded
                        # print 'offset:', offset
                        # die('non zero offset is not implemented')
                    iv = map(values.__getitem__, l[5 : ])
                ints = split_to_ints(fun_endianity, fun_size, padded)
                for i in range(0, len(ints), 16):
                    ins = ints[i : i + 16]
                    iv = interpret(m_code, ins, 'run', initial_state = iv, upper_modules_and_mt = upper_modules_and_mt, ifs = ifs)
                # %%% надо сцепить инты
                ivs = [int_to_hex(v, fun_size, fun_endianity) for v in iv]
                r = ''.join(ivs).decode('hex')
                values[res_var] = r
            elif l[0] == 'label':
                # We ignore labels
                pass
            elif l[0] == 'new_const':
                values[l[1]] = int(l[2])
                sizes[l[1]] = size
            elif l[0] == 'bs_new_const':
                assert l[2] == '0' or l[2] == '1'
                values[l[1]] = int(l[2])
            elif l[0] == 'var_setup':
                size = int(l[1])
                endianity = l[2]
                bits = size * 8
                max_int = 2 ** bits
                mask_int = max_int - 1
            elif l[0] == 'new_array':
                vname = l[1]
                # aname = l[2]
                elements = l[3:]
                assert vname not in arrays
                arrays[vname] = map(values.__getitem__, elements)
            elif l[0] == 'make_array':
                vname = l[1]
                # aname = l[2]
                asize = values[l[3]]
                assert vname not in arrays
                arrays[vname] = [None] * asize
            elif l[0] == 'set_item':
                avname = l[1]
                index = values[l[2]]
                value = values[l[3]]
                arrays[avname][index] = value
            elif l[0] == 'bs_make_array':
                vname = l[1]
                # aname = l[2]
                asize = values[l[3]]
                assert vname not in bs_arrays
                bs_arrays[vname] = [[None] * bits for i in range(asize)]
            elif l[0] == 'bs_set_item':
                avname = l[1]
                index = values[l[2]]
                value = values[l[3]]
                bit_index = int(l[4])
                bs_arrays[avname][index][bit_index] = value
            elif l[0] in ops:
                values[l[1]] = ops[l[0]](*[values[i] for i in l[2:]])
            elif l[0] == 'sbox':
                # print >> sys.stderr, l, values[l[2]]
                values[l[1]] = arrays[l[3]][values[l[2]]]
            elif l[0] == '__getitem__':
                values[l[1]] = arrays[l[2]][values[l[3]]]
            elif l[0] == 'output':
                # %% на данный момент значение обрабатывается согласно
                #  % текущему размеру, а не размеру значения
                handle_output(values[l[1]])
            elif l[0] == 'output_bytes':
                if results == 'run':
                    result_values.append(values[l[1]])
                else:
                    # %% print hex
                    print >> sys.stderr, 'bytes results:', values[l[1]]
            elif l[0] == 'bs_output':
                n = int(l[2])
                # assert bits == 32
                # assert set(values.values()) == set([1, 0])
                # for v in values:
                #     if values[v] not in [0, 1]:
                #         print >> sys.stderr, v, '{0:x}'.format(values[v])
                assert values[l[1]] in [0, 1]
                output_value |= values[l[1]] << (bits - 1 - n)
                if n == bits - 1:
                    handle_output(output_value)
                    output_value = 0
            elif l[0] == 'print_verbatim':
                print >> sys.stderr, 'verbatim:', l[1].decode('hex')
            elif l[0] == 'print_var':
                s = sizes[l[1]]
                fmt_size = str(s * 2)
                print >> sys.stderr, ('var {0}: {1:0' + fmt_size + 'x} {1} size {2}').format(l[1], values[l[1]], s)
            elif l[0] == 'print_many':
                r = []
                for v in l[1:]:
                    s = sizes[l[1]]
                    fmt_size = str(s * 2)
                    r.append(('{0:0' + fmt_size + 'x}').format(values[v]))
                print >> sys.stderr, "pm:", ' '.join(r)
            elif l[0] == 'debug_exit':
                # exit(1)
                die('debug_exit')
            elif l[0] == 'cycle_const_range' or l[0] == 'cycle_range':
                vname = l[1]
                label = l[2]
                from_value = values[l[3]]
                to_value = values[l[4]]
                step = values[l[5]]
                code_position = instruction_index
                assert label not in cycles
                t = 'const_range' if l[0] == 'cycle_const_range' else 'range'
                cycles[label] = [t, code_position, vname, from_value, to_value, step, from_value]
                values[vname] = from_value
                # %% если у нас ноль итераций выходит, то тут надо
                #  % пропускать до конца
            elif l[0] == 'cycle_end':
                label = l[1]
                # %% надо проверять вложенность циклов, стек?
                ctype, code_position, vname, from_value, to_value, step, current = cycles[label]
                if ctype == 'const_range' or ctype == 'range':
                    current += step
                    cycles[label][6] = values[vname] = current
                    if current <= to_value:
                        instruction_index = code_position
                    # else:
                    #     print >> sys.stderr, current
                    #     print >> sys.stderr, 'end'
                else:
                    die('not implemented cycle type: {0}', ctype)
            elif l[0] == 'bs_getitem':
                # if 'sha256_var147' in l:
                #     print >> sys.stderr, l
                # print >> sys.stderr, l, len(bs_arrays[l[2]]), values[l[3]], int(l[4])
                values[l[1]] = bs_arrays[l[2]][values[l[3]]][int(l[4])]
            elif l[0] == 'bs_new_var':
                values[l[1]] = None
            elif l[0] == 'new_var':
                values[l[1]] = None
            elif l[0] == 'new_state_var':
                if initial_state == None:
                    values[l[1]] = values[l[2]]
                else:
                    values[l[1]] = initial_state.pop(0)
            elif l[0] == 'bs_assign' or l[0] == '__floordiv__' or l[0] == 'bytes_assign':
                assert l[1] in values
                values[l[1]] = values[l[2]]
            elif l[0] == 'bs_new_array':
                vname = l[1]
                # aname = l[2]
                elements = l[3:]
                assert vname not in arrays
                assert len(elements) % bits == 0
                arr = map(values.__getitem__, elements)
                bs_arrays[vname] = [arr[i : i + bits] for i in range(0, len(arr), bits)]
            elif l[0] == 'bs_print_var':
                vname = l[1]
                i = int(l[2])
                if i == 0:
                    bs_printing_value = 0
                bs_printing_value |= values[vname] << (bits - 1 - i)
                if i == bits - 1:
                    # %% hard-coded 08x
                    print >> sys.stderr, 'bs_var: {0:08x} {0}'.format(bs_printing_value)
            elif l[0] == 'hfun_block_size':
                # %% implement
                values[l[1]] = 128
            elif l[0] == 'hfun_digest_size':
                # %% implement
                values[l[1]] = 64
            elif l[0] == 'new_bytes':
                values[l[1]] = ''
            elif l[0] == 'new_bytes_len':
                values[l[1]] = None
            elif l[0] == 'bytes_len':
                values[l[1]] = len(values[l[2]])
            elif l[0] == 'bytes_split_to_nums':
                # print values[l[2]], size * values[l[3]]
                # print len(values[l[2]]), values[l[3]]
                assert len(values[l[2]]) == size * values[l[3]]
                arrays[l[1]] = [None] * values[l[3]]
                s = values[l[2]]
                for i in range(values[l[3]]):
                    v = s[i * size : i * size + size]
                    if endianity == 'le':
                        v = ''.join(reversed(v))
                    v = int(v.encode('hex'), 16)
                    arrays[l[1]][i] = v
            elif l[0] == '__gt__':
                values[l[1]] = int(values[l[2]] > values[l[3]])
            elif l[0] == 'if_condition':
                label = l[1]
                if not values[l[2]]:
                    # skip till 'else' or 'end', go to instruction
                    # after that
                    while (code[instruction_index][0] != 'if_else' or code[instruction_index][0] != 'if_end') and code[instruction_index][1] != label:
                        instruction_index += 1
                    instruction_index += 1
            elif l[0] == 'if_else':
                # We are here only if the first was good, skip till end
                while code[instruction_index][0] != 'if_end' and code[instruction_index][1] != label:
                    instruction_index += 1
                instruction_index += 1
            elif l[0] == 'if_end':
                # just ignore
                pass
            elif l[0] == 'bytes_append_zeros_up_to':
                s = values[l[2]]
                values[l[1]] = s + '\0' * (values[l[3]] - len(s))
            elif l[0] == 'bytes_xor_each':
                s = values[l[2]]
                n = values[l[3]]
                values[l[1]] = ''.join(chr(n ^ ord(c)) for c in s)
            elif l[0] == 'bytes_concat':
                # %% проверка типов?
                values[l[1]] = values[l[2]] + values[l[3]]
            elif l[0] == 'bytes_hex':
                values[l[1]] = values[l[2]].encode('hex')
            elif l[0] == 'bytes_hex_upper':
                values[l[1]] = values[l[2]].encode('hex').upper()
            elif l[0] == 'invoke_plain':
                vname = l[1]
                fun = l[2]
                nums = l[3 : ]
                # print '>>', ifs
                in_k = ifs[fun]['inputs']
                ins = map(values.__getitem__, nums[ : in_k])
                state = map(values.__getitem__, nums[in_k : ])
                m_code = modules[fun]
                r = interpret(m_code, ins, 'run', initial_state = state,
                              upper_modules_and_mt = upper_modules_and_mt,
                              ifs = ifs)
                # assert vname not in arrays
                arrays[vname] = r
            elif l[0] in ['invoke_hfun', 'invoke_hfun_with_size']:
                res_var, hfun_var, arg_var = l[1:4]
                m_code = modules[hfun_var]
                r = interpret(m_code, None, 'run', key = values[arg_var], upper_modules_and_mt = upper_modules_and_mt, ifs = ifs)
                values[res_var] = r[0]
            elif l[0] == 'invoke_fun2':
                _, res_var, fun_var, arg1_var, arg2_var = l
                m_code = modules[fun_var]
                r = interpret(m_code, None, 'run',
                              key = values[arg1_var],
                              salt = values[arg2_var],
                              upper_modules_and_mt = upper_modules_and_mt,
                              ifs = ifs)
                values[res_var] = r[0]
            elif l[0] == 'print_bytes':
                s = values[l[1]]
                print 'pb {0}: {1}'.format(len(s), s)
            elif l[0] == 'print_hex':
                print 'ph:', values[l[1]].encode('hex')
            elif l[0] == 'bytes_append_num':
                # %% old size or current size?
                n = '{{0:0{0}x}}'.format(sizes[l[3]] * 2).format(values[l[3]])
                n = n.decode('hex')
                if endianity == 'le':
                    n = ''.join(reversed(n))
                values[l[1]] = values[l[2]] + n
            elif l[0] == 'bytes_xor':
                values[l[1]] = ''.join(chr(ord(x) ^ ord(y)) for x, y in zip(values[l[2]], values[l[3]]))
            elif l[0] == 'bytes_join_nums':
                r_var = l[1]
                to_join = map(values.__getitem__, l[2:])
                # %% old size or current size?
                # %% check that all sizes are same?
                h = map('{{0:0{0}x}}'.format(sizes[l[2]] * 2).format, to_join)
                values[r_var] = ''.join(h).decode('hex')
            elif l[0] == 'bytes_slice':
                values[l[1]] = values[l[2]][values[l[3]] : values[l[4]]]
            elif l[0] == 'bytes_zeros':
                values[l[1]] = '\0' * values[l[2]]
            elif l[0] == 'assume_length':
                # %% may check against real length
                pass
            elif l[0] == 'new_bytes_const':
                values[l[1]] = l[2].decode('hex')

            else:
                die('not implemented instruction: {0}', l)
        if results == 'run':
            return result_values
        return code
    except:
        print >> sys.stderr, 'l:', l
        raise

