# -*- coding: utf-8 -*-
# Utility functions to manipulate bytecode

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from lang_spec import instructions

from util_main import *

class BGlobal():
    pass
g = BGlobal()
g.const_count = 0

def new_const(value):
    g.const_count += 1
    n = 'bconst_var' + str(g.const_count)
    return ['new_const', n, str(value)]

def new_name():
    g.const_count += 1
    n = 'b_var' + str(g.const_count)
    return n

def put_const(new_code, value):
    n = new_name()
    new_code.append(['new_const', n, str(value)])
    return n

def put_array_parts(new_code, array, k):
    out_list = []
    for i in range(k):
        r = new_name()
        ni = put_const(new_code, i)
        new_code.append(['__getitem__', r, array, ni])
        # new_code.append(['print_var', r])
        out_list.append(r)
    return out_list

def extract_modules(code):
    code = list(code)
    ms = {}
    main = []
    ms_types = {}
    while len(code) != 0:
        l = code.pop(0)
        if l[0] == 'module_begin':
            var_name = l[1]
            m_type = l[2]
            orig_name = l[3]
            ms_types[var_name] = [m_type, orig_name]
            m = []
            while True:
                l = code.pop(0)
                # %% надо проверять замыкания, разрешить замыкания на
                #  % константы
                if l[0] == 'module_end' and l[1] == var_name:
                    break
                m.append(l)
            ms[var_name] = m
        else:
            main.append(l)
    ms['_main'] = main
    # ms_types['_main'] = '_main'
    return ms, ms_types

def collect_ifs(code):
    modules, modules_types = extract_modules(code)
    ifs = {}
    for m, c in modules.iteritems():
        if m == '_main':
            continue
        ifs[m] = get_interface(c)
        # Collect recursively
        sub_if = collect_ifs(c)
        for i in sub_if:
            assert i not in ifs
            ifs[i] = sub_if[i]
    return ifs

def count_instructions(code):
    r = {}
    for l in code:
        if l[0] not in r:
            r[l[0]] = 0
        r[l[0]] += 1
    return r

def count_instructions_main(code):
    modules, modules_types = extract_modules(code)
    return count_instructions(modules['_main'])

def collect_consts(code):
    consts = {}
    for l in code:
        if l[0] == 'new_const':
            if l[1] in consts:
                die('known const')
            consts[l[1]] = l[2]
    return consts

# def collect_consts_computed(code):
#     consts = collect_consts(code)
#     lengths = collect_bytes_lengths(code)
#     for l in code:
#         # %% make filter to insert new_const
#         if l[0] == 'bytes_len' and lengths[l[2]] != 'unknown':
#             consts[l[1]] = lengths[l[2]]
#         elif instructions[l[0]].return_type != 'void' and ((len(instructions[l[0]].args) == 2 and l[2] in consts and l[3] in consts) or (len(instructions[l[0]].args) == 1 and l[2] in consts)):
#             # %% that's a bit from compute_const_expressions()
#             if l[0] == '__add__':
#                 # %% wrap?
#                 consts[l[1]] = int(consts[l[2]]) + int(consts[l[3]])
#             elif l[0] == '__sub__':
#                 # %% мы поддерживаем отрицательные?
#                 consts[l[1]] = int(consts[l[2]]) - int(consts[l[3]])
#     return consts

def get_interface(code):
    modules, mt = extract_modules(code)
    code = modules['_main']
    # Мы проходим по коду, запоминаем входы и выходы, а так же их
    # размеры.
    # %% input_key и прочее
    sizes = {}
    inputs = []
    outputs = []
    input_names = []
    output_names = []
    state = []
    size = None
    endianity = None
    hfun_block_size = None
    hfun_digest_size = None
    consts = collect_consts(code)
    for l in code:
        if l[0] == 'var_setup':
            size = int(l[1])
            endianity = l[2]
        elif l[0] == 'set_hfun_block_size':
            hfun_block_size = int(l[1])
        elif l[0] == 'set_hfun_digest_size':
            hfun_digest_size = int(l[1])
        elif l[0] == 'input':
            inputs.append((size, endianity))
            input_names.append(l[1])
        elif l[0] == 'output':
            outputs.append(sizes[l[1]])
            output_names.append(l[1])
        elif l[0] == 'input_state':
            state.append((l[1], None))
        elif l[0] == 'new_state_var':
            state.append((l[1], consts[l[2]]))
        elif instructions[l[0]].return_type != 'void':
            sizes[l[1]] = (size, endianity)
    # Проверяем, что входы и выходы одинаковые
    arr = inputs + outputs
    if len(arr) > 0:
        size = arr[0][0]
        endianity = arr[0][1]
        for e in arr:
            if not (e[0] == size and e[1] == endianity):
                print e, size, endianity
                die('different input/output formats are not implemented')
    r = { 'size' : size, 'endianity' : endianity,
          'inputs' : len(inputs), 'outputs' : len(outputs),
          'input_names' : input_names, 'output_names' : output_names,
          'state_vars' : len(state),
          'state_var_names_values' : state }
    if hfun_digest_size != None:
        r['hfun_digest_size'] = hfun_digest_size
    if hfun_block_size != None:
        r['hfun_block_size'] = hfun_block_size
    return r

def check_name_uniqueness(code):
    t = set()
    for l in code:
        if instructions[l[0]].return_type != 'void':
            if l[1] in t:
                die('non-unique name in {0}', l)
            t.add(l[1])
    # return code

def collect_sizes(code):
    check_name_uniqueness(code)
    ms, mt = extract_modules(code)
    sizes = {}
    for m in ms:
        size = None
        endianity = None
        for l in ms[m]:
            if l[0] == 'var_setup':
                size = int(l[1])
                endianity = l[2]
            elif instructions[l[0]].return_type != 'void':
                sizes[l[1]] = (size, endianity)
    return sizes

def sort_modules(modules):
    # считаем зависимости
    dependencies = {}
    p = modules.items()
    for m, c in p:
        d = set()
        for l in c:
            for e in l:
                if e in modules:
                    d.add(e)
        dependencies[m] = d
    # проверка: саморекурсия
    for m, d in dependencies.items():
        if m in d:
            die('self recursion')
    # формируем список
    # %% надо ловить циклические зависимости; взаимная рекурсия
    r = []
    while len(p) > 0:
        m, c = p.pop(0)
        d = dependencies[m]
        for other in p:
            if other[0] in d:
                p.append((m, c))
                break
        else:
            r.append((m, c))
    return r

def collect_bytes_lengths(code):
    ls = {}
    ifs = collect_ifs(code)
    sizes = collect_sizes(code)
    consts = collect_consts(code)
    for l in code:
        if l[0] in ['input_key', 'input_salt', 'input_salt2']:
            # We'll use float for 'unknown', so all arithmetics will
            # save it for free.
            ls[l[1]] = 0.0
        elif l[0] == 'assume_length':
            # %% support ranges
            assert consts[l[2]] == consts[l[3]]
            ls[l[1]] = int(consts[l[2]])
        elif l[0] in ['run_merkle_damgard', 'run_merkle_damgard_with_state']:
            i = ifs[l[2]]
            ls[l[1]] = i['outputs'] * i['size']
        elif l[0] == 'bytes_len' and type(ls[l[2]]) != float:
            consts[l[1]] = str(ls[l[2]])
        elif l[0] == 'bytes_xor_each':
            ls[l[1]] = ls[l[2]]
        elif l[0] == 'bytes_concat':
            ls[l[1]] = ls[l[2]] + ls[l[3]]
        elif l[0] == 'bytes_xor':
            # print ls[l[2]], ls[l[3]]
            assert ls[l[2]] == ls[l[3]]
            ls[l[1]] = ls[l[2]]
        elif l[0] == 'bytes_append_num':
            ls[l[1]] = ls[l[2]] + sizes[l[3]][0]
        elif l[0] == 'bytes_slice':
            # %% это может быть константное выражение
            ls[l[1]] = int(consts[l[4]]) - int(consts[l[3]])
        elif l[0] == 'bytes_zeros':
            ls[l[1]] = int(consts[l[2]])
        elif l[0] == 'bytes_join_nums':
            ls[l[1]] = sum(sizes[t][0] for t in l[2 : ])
        elif l[0] == 'bytes_assign':
            # %% если мы внутри ифа, то мы можем иметь разные длины,
            #  % стоит трекать это
            ls[l[1]] = ls[l[2]]
        elif l[0] == 'invoke_hfun':
            ls[l[1]] = ifs[l[2]]['hfun_digest_size']
        elif l[0] == 'invoke_hfun_with_size':
            # тут можно как обычный invoke_hfun, а можно взять значение
            ls[l[1]] = int(consts[l[4]])
        elif l[0] == 'invoke_fun2':
            ls[l[1]] = 0.0
        elif l[0] == 'new_bytes':
            # %% хм, если это будет где-то использоваться, то у нас
            #  % нельзя определить длину при статическом анализе,
            #  % скажем: bytes_assign(a, bytes_concat(a, b)) в цикле;
            #  % это же относится к bytes_append_num
            ls[l[1]] = 'no_len'
        elif l[0] == 'bytes_append_zeros_up_to':
            # # %% а если длина уже больше этого?
            # ls[l[1]] = int(consts[l[3]])
            ls[l[1]] = 0.0
        elif instructions[l[0]].return_type == 'bytes':
            die('unsupported op returning bytes {0}', l)
        # %% invoke_* instructions
    for i in ls:
        if type(ls[i]) == float:
            ls[i] = 'unknown'
    return ls

def print_bytes_lengths(code):
    ls = collect_bytes_lengths(code)
    kn = 0
    for i in ls:
        if ls[i] == 'unknown':
            print 'unknown:', i
        else:
            print 'known len:', i, ls[i]
            kn += 1
    print ' stats: known', kn, 'of', len(ls)
    exit(1)

def print_bytes(code):
    for l in code:
        if 'bytes' in instructions[l[0]].all_types or l[0].startswith(('cycle_', 'module_')):
            print ' '.join(l)
    exit(1)

def find_cycle(code, name):
    idx1 = idx2 = None
    for i, l in enumerate(code):
        if l[0].startswith('cycle_') and ((len(l) > 2 and l[2] == name) or l[1] == name):
            if idx1 == None and l[0] != 'cycle_end':
                idx1 = i
            elif idx2 == None and l[0] == 'cycle_end':
                idx2 = i
            else:
                die('cycle already found, 2+ are not implement')
    return idx1, idx2

def collect_mutable_bytes_in_cycle(code, name):
    idx1, idx2 = find_cycle(code, name)
    body = code[idx1 + 1 : idx2]
    track = {}
    for l in body:
        if l[0] == 'bytes_assign':
            track[l[1]] = 1
    for l in body:
        if l[0] == 'new_bytes':
            del track[l[1]]
    return track.keys()

def pattern_group(name, *matchers):
    return { 'name' : name, 'type' : 'group', 'matchers' : matchers }

def pattern_lines(*matchers):
    # %% any matchers or just lines?
    return { 'type' : 'many_any', 'matchers' : matchers }

def pattern_var(name):
    return { 'name' : name, 'type' : 'var' }

def pattern_reference(name):
    return { 'name' : name, 'type' : 'reference' }

def pattern_many_vars(name):
    return { 'name' : name, 'type' : 'many_vars' }

pattern_functions = [
    # named group of lines
    pattern_group,
    # named single variable
    pattern_var,
    # reference to named variable
    pattern_reference,
    # named array of variables
    pattern_many_vars,
    # anonymous matcher for many lines from set (any order)
    pattern_lines
]
