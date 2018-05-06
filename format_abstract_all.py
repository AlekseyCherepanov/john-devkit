# -*- coding: utf-8 -*-
# all formats in interpreter

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

import struct
import subprocess

import lang_main as L
import bytecode_main as B
from util_main import *

import util_ui as U
import output_c as O

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
merkle_damgard0x01 = make_merkle_damgard('\x01')

# special variant for whirlpool: 256-bit length
def merkle_damgard_whirlpool(endianness, size, s):
    endianness = 'le'
    size = 8
    block = size * 8
    ll = len(s)
    l = ll % block
    len_size = 256 / 8
    if l <= block - len_size - 1:
        zeros = block - len_size - 1 - l
    else:
        zeros = 2 * block - len_size - 1 - l
    s += '\x80'
    s += '\0' * zeros
    ll <<= 3
    ll_hex = '{{0:0{0}x}}'.format(len_size * 2).format(ll)
    ll_bin = ll_hex.decode('hex')
    # if endianness == 'le':
    #     # reverse order of bytes
    #     ll_bin = ''.join(reversed(ll_bin))
    s += ll_bin
    return s

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

def unhex_hash(endianness, size, h):
    h = re.sub(r'^\$[^$]+\$', '', h)
    # %% надо проверять, что хеш - целиком хекс
    return split_to_ints(endianness, size, h.decode('hex'))

def unhex_hash_no_ints(h):
    h = re.sub(r'^\$[^$]+\$', '', h)
    # %% надо проверять, что хеш - целиком хекс
    return [h.decode('hex')]

def read_tests(name):
    contents = slurp_dk_file('hash_tests/john_{0}.c'.format(name))
    # r = re.findall(r'"([A-Fa-f0-9]*)",\s*"([^"]*)"', contents)
    r = re.findall(r'"((?:\\.|[^"])*)",\s*"([^"]*)"', contents)
    r = [(h, re.sub(r'\\x(..)', lambda m: chr(int(m.group(1), 16)), p))
         for h, p in r]
    # print len(r), contents.count('\n{')
    # assert len(r) == contents.count('\n{')
    return r

def test(algo_name, test_name, padding_func, hash_reader, use_c = False):
    # Load tests
    tests = None
    if type(test_name) == str:
        tests = read_tests(test_name)
    # Load algo
    code = B.get_code_full(algo_name)
    interface = B.get_interface(code)
    endianness = interface['endianity']
    size = interface['size']
    # We assume empty message to give full 1 block
    # %% it is not true for all hashes
    max_len1 = len(padding_func(endianness, size, ''))
    block_size = max_len1 / size
    t = 'x'
    while len(padding_func(endianness, size, t)) == max_len1:
        t += 'x'
    max_len = len(t) - 1
    # %% endianness vs endianity, consistency would be great
    all_tests_ints = [(i,
                   hash_reader(endianness, size, h),
                   split_to_ints(endianness, size,
                                 padding_func(endianness, size, p)))
                  for i, (h, p) in enumerate(tests)]
    tests_ints = filter(lambda args: len(args[2]) == block_size, all_tests_ints)
    len_diff = len(all_tests_ints) - len(tests_ints)
    code = B.replace_state_with_const(code)

    B.dump(code, 'dump.bytecode')

    # code = B.drop_print(code)

    assert len(tests) != 0

    def print_err():
        print tests[i][1], '<-- password'
        f = '{{0:0{0}x}}'.format(size * 2).format
        print map(f, p), 'padded password'
        print map(f, h), 'expected hash'
        print tests[i][0], 'hash'
        if r != None:
            # %% endianness?
            print ''.join(map(f, r)), 'our hash (short)'
            print map(f, r), 'our hash'
    for i, h, p in tests_ints:
        r = None
        # print p, 'p'
        # print h, 'h'
        try:
            executor = run_c if use_c else B.interpret
            r = executor(code, list(p), 'run')
            if r != h:
                print '>>', r
                print '>>', h
                die('failed hash')
        except:
            print_err()
            raise
    print 'ok: {0}, {1} tests done ({2} skipped as multiblock, max len {3})'.format(algo_name, len(tests_ints), len_diff, max_len)
    return True


def test_salted(algo_name, test_name, hash_reader, use_c = False, transforms = [], get_code = B.get_code_full, test_reader = read_tests):
    tests = test_reader(test_name)
    assert len(tests) != 0
    code = get_code(algo_name)
    print 'code len:', len(code)
    B.dump(code, 'dump.bytecode')
    B.check_types(code)
    code = B.thread_code(code, *transforms)
    # code = B.change_inputs_for_functions(code)
    # code = B.drop_print(code)
    max_key_len = max_salt_len = skipped = 0
    for i, hhpmu in enumerate(tests):
        if len(hhpmu) == 2:
            hh, p = hhpmu
            user = None
        else:
            hh, p, user = hhpmu
        hhh = hash_reader(hh)
        if hhh == None:
            skipped += 1
            continue
        if len(hhh) == 1:
            h = hhh[0]
            salt = ''
            salt2 = None
            rounds = None
        elif len(hhh) == 3:
            salt, h, rounds = hhh
            salt2 = None
        else:
            salt, h, rounds, salt2 = hhh
        if user != None:
            assert salt2 == None
            salt2 = user
        if salt != None:
            max_salt_len = max(len(salt), max_salt_len)
        max_key_len = max(len(p), max_key_len)
        executor = run_c if use_c else B.interpret
        # print repr(p)
        # print repr(salt)
        # print hhpmu, repr(salt)
        r = executor(code, [], 'run',
                     key = p, salt = salt, rounds = rounds, salt2 = salt2)
        if len(r) != 1 or r[0] != h:
            print '>>', repr(p), '<- input'
            print '>>', repr(hh), '<- orig hash'
            print '>>', repr(r), '<- result'
            print '>>', repr(h), '<- expected'
            die('failed hash')
    if salt == None:
        max_salt_len = None
    print 'ok: {0}, {1} tests done (skipped {4}, max_key_len is {2}, max_salt_len is {3})'.format(algo_name, len(tests) - skipped, max_key_len, max_salt_len, skipped)
    return True

def md2_padding(endianness, size, s):
    # arr = [chr(i) * i for i in range(16 + 1)]
    i = 16 - len(s) % 16
    s += chr(i) * i
    return s

def crc32_padding(endianness, size, s):
    l = 4 - len(s) % 4
    s += '\0' * l
    return s

def read_hmac_hash(s):
    # %% /* mockup JWT hash */ не поддерживается
    i = s.rfind('#')
    salt = s[ : i]
    h = s[i + 1 : ]
    h = h.decode('hex')
    return salt, h, None

# just like hmac, but salt and hash switched positions
def read_decrypt_hash(s):
    # %% /* mockup JWT hash */ не поддерживается
    i = s.rfind('#')
    salt = s[ : i]
    h = s[i + 1 : ]
    h = h.decode('hex')
    return h, salt, None

def read_pbkdf2_hash(s):
    if s.startswith('$pbkdf2-hmac-sha512$'):
        h = s.split('$')[-1]
        rounds, salt, h = h.split('.')
        rounds = int(rounds)
        return salt.decode('hex'), h.decode('hex'), rounds

def read_truecrypt_hash(s):
    if s.startswith('truecrypt_SHA_512$'):
        h = s.split('$')[-1]
        b = h.decode('hex')
        salt = b[ : 64]
        data = b[64 : 64 + 16]
        # %% а вообще, трукрипт - необычный хеш, значения нет
        return salt, "TRUE\0\0\0\0", None, data


def run_c(code, data, ignored, key = None, salt = None, rounds = None, salt2 = None):
    c_code = U.load_code_template('tester')
    O.gen(code, 'test.c', c_code, {}, {})
    if os.system('gcc test.c -o test.bin') != 0:
        die('compilation failure')
    def enc(a):
        if type(a) == str:
            return 'b' + a.encode('hex')
        if type(a) == int or type(a) == long:
            return 'u{0:016x}'.format(a)
        if a == None:
            return 'n'
    cmd = ['./test.bin', 'f'] + map(enc, (key, salt, rounds, salt2)) + map(enc, data)
    print cmd
    p = subprocess.Popen(cmd, stderr = subprocess.PIPE)
    out = p.stderr.read()
    # %% надо проверять код возврата
    # p.kill()
    return [out]

def test_salted_c(algo_name, test_name, hash_reader, transforms = [], get_code = B.get_code_full, test_reader = read_tests):
    return test_salted(algo_name, test_name, hash_reader, use_c = True, transforms = transforms, get_code = get_code, test_reader = test_reader)

def test_c(algo_name, test_name, padding_func, hash_reader, use_c = False):
    return test(algo_name, test_name, padding_func, hash_reader, use_c = True)

# test('sha256', 'raw-sha256', merkle_damgard, unhex_hash)
# test('sha512', 'raw-sha512', merkle_damgard, unhex_hash)
# test('md5', 'raw-md5', merkle_damgard, unhex_hash)
# test('md4', 'raw-md4', merkle_damgard, unhex_hash)
# test('sha1', 'raw-sha1', merkle_damgard, unhex_hash)
# test('md2', 'raw-md2', md2_padding, unhex_hash)
# test('tiger', 'tiger', merkle_damgard0x01, unhex_hash)
# test('ripemd160', 'ripemd-160', merkle_damgard, unhex_hash)
# test('whirlpool', 'whirlpool', merkle_damgard_whirlpool, unhex_hash)
# test_hfun('sha512', 'raw-sha512', unhex_hash_no_ints)
# test_salted('hmac-sha512', 'hmac-sha512', read_hmac_hash)
# test_salted('pbkdf2-hmac-sha512', 'pbkdf2-hmac-sha512', read_pbkdf2_hash)
# test_salted('aes_encrypt', 'my_aes_encrypt', read_hmac_hash)
# test_salted('aes_decrypt', 'my_aes_encrypt', read_decrypt_hash)
# test_salted('truecrypt_sha512', 'truecrypt_sha512', read_truecrypt_hash)

# test_salted('hfun_sha512', 'raw-sha512', unhex_hash_no_ints)

fix = dict(transforms = [
    B.fix_run_merkle_damgard,
    B.compute_hfun_sizes,
    [B.dump, 'all.bytecode']
    ])

# test_salted_c('hfun_sha512', 'raw-sha512', unhex_hash_no_ints, **fix)

# test_salted_c('hmac-sha512', 'hmac-sha512', read_hmac_hash, **fix)

# test_salted('pbkdf2-hmac-sha512', 'pbkdf2-hmac-sha512', read_pbkdf2_hash)

# test_salted_c('pbkdf2-hmac-sha512', 'pbkdf2-hmac-sha512', read_pbkdf2_hash, **fix)

# test_salted_c('truecrypt_sha512', 'truecrypt_sha512', read_truecrypt_hash, **fix)


# # Format name "GOST R 34.11-94"
# test('gost', 'gost', merkle_damgard0x01, unhex_hash)

def read_dynamic_conf(fname):
    p = U.john_base + '/../run/' + fname + '.conf'
    o = []
    c = None
    with open(p) as f:
        for l in f:
            ll = '[List.Generic:dynamic_'
            le = 'Expression='
            lt = 'Test'
            if l.startswith(ll):
                o.append(c)
                c = { 'tests' : [] }
                c['name'] = l[len(ll) : ].strip().strip(']')
            elif l.startswith(le):
                assert 'expression' not in c
                c['expression'] = l[len(le) : ].strip()
            elif l.startswith(lt):
                t = l.split('=')[1].rstrip('\n')
                c['tests'].append(t)
        o.append(c)
        if o[0] == None:
            o.pop(0)
    return o

dynas_d = {}

def load_dynas_from_conf():
    dynas = read_dynamic_conf('dynamic')
    dynas += read_dynamic_conf('dynamic_flat_sse_formats')
    for d in dynas:
        dynas_d[d['name']] = d
    return dynas

def get_tests_by_list(fmt_label):
    # %% quoting
    cmd = "./JohnTheRipper/run/john --list=format-tests --format='" + fmt_label + "'"
    t = []
    with os.popen(cmd, 'r') as p:
        for l in p:
            n, i, h, p = l.rstrip('\n').split('\t')
            # %% remove dupes?
            h = h.split(':')
            if len(h) == 1:
                h = h[0]
            elif len(h) == 2:
                h = h[1] + '$$U' + h[0]
            else:
                die('unknown case {0}', h)
            t.append(h + ':' + p)
    return t

def get_thin_dynamics():
    cmd = "./JohnTheRipper/run/john --format=dynamic_'*' --list=format-details | cut -f 1,7"
    with os.popen(cmd, 'r') as p:
        f = p.read()
    f = f.strip().split('\n')
    o = []
    for l in f:
        l = re.sub(r' \d+/\d+.*', '', l)
        l = l.split('\t')
        l[0] = l[0].replace('dynamic_', '')
        if l[0] not in dynas_d:
            t = get_tests_by_list('dynamic_' + l[0])
            d = { 'name': l[0], 'expression': l[1], 'tests': t }
            o.append(d)
    return o

def load_dynas_thin(dynas):
    thin_dynas = get_thin_dynamics()
    for d in thin_dynas:
        dynas_d[d['name']] = d
        dynas.append(d)

def get_synthetic_dynamics(dynas):
    forms = r'''
    hash($p.$s)
    hash($s.$p)
    hash($s.$p.$s)
    hash($p.$s.$p)
    hash(hash($p))
    hash(hash_raw($p))
    hash(hash($p).$s)
    hash($s.hash($p))
    hash($s.hash($s.$p))
    hash(hash($s).$p)
    hash($p.hash($s))
    hash(hash($p).hash($s))
    hash(hash($p).hash($p))
    '''.strip().replace(' ', '').split('\n')
    hashes = 'md4 md5 sha1 sha256 sha512'.split(' ')
    oe = []
    for f in forms:
        for h in hashes:
            e = f.replace('hash', h)
            # print e, e == 'sha512(sha512($p).sha512($s))'
            if e in ['sha512(sha512($p).sha512($s))', 'sha512(sha512($p).sha512($p))']:
                # %% it fails in john
                continue
            for d in dynas:
                if d['expression'].startswith(e):
                    # print e
                    break
            else:
                oe.append(e)
    ds = []
    for i, e in enumerate(oe):
        # print e
        name = 'syn' + str(i)
        t = get_tests_by_list('dynamic=' + e)
        t = [ '$dynamic_' + name + '$' + v.split('@')[2] for v in t ]
        ds.append({ 'name': name, 'expression': e, 'tests': t })
    return ds

def load_dynas_synthetic(dynas):
    syn_dynas = get_synthetic_dynamics(dynas)
    for d in syn_dynas:
        dynas_d[d['name']] = d
        dynas.append(d)

def load_dynas_all():
    dynas = load_dynas_from_conf()
    load_dynas_thin(dynas)
    load_dynas_synthetic(dynas)
    return dynas

# import json
# import yaml
import pickle
if 0:
    dynas = load_dynas_all()
    print len(dynas)
    with open('dynamics_descriptions.cache', 'w') as f:
        # json.dump(dynas, f)
        # yaml.dump(dynas, f)
        pickle.dump(dynas, f)
    exit(1)
else:
    with open('dynamics_descriptions.cache', 'r') as f:
        # dynas = json.load(f)
        # dynas = yaml.load(f)
        dynas = pickle.load(f)
        for d in dynas:
            dynas_d[d['name']] = d

# for d in dynas:
#     if ') (' in d['expression']:
#         print d['expression']

# es = [d['expression'] for d in dynas]
# h = {}
# for e in es:
#     l = e.split(' ')[0]
#     if l not in h:
#         h[l] = 0
#     h[l] += 1
# for k, v in h.items():
#     print v, k

funcs = 'md4 md5 sha1 sha256 sha512'.split(' ')
# ** order matters!
consts = r':XDB: : \nskyper\n Y 0xF7'.split(' ')
tokens = 'pad100( trunc32( hex_upper( $p $s $u . )'.split(' ')

tokens += consts

tokens += [f + '(' for f in funcs]
tokens += [f + '_raw(' for f in funcs]

def split_expression(e):
    o = []
    while len(e) > 0:
        for t in tokens:
            if e.startswith(t):
                o.append(t)
                e = e[len(t) : ]
                break
        else:
            die("can't parse {0}", e)
    return o

# print dynas_d['1008']

def to_tree(l):
    c = []
    s = []
    r = c
    for t in l:
        # print c, '  ::  ', s
        # print t
        if t.endswith('('):
            n = [ t ]
            c.append(n)
            c = n
            s.append(c)
        elif t == ')':
            s.pop()
            if len(s) != 0:
                c = s[-1]
            else:
                c = None
                s = None
        else:
            c.append(t)
    return r[0]

# t = ['md5(', 'md5(', '$p', ')', '.', 'md5(', '$p', ')', ')']
# t = to_tree(t)
# print t
# exit(1)

def tree_walk(t, fun):
    r = []
    for e in t:
        if type(e) == list:
            e = tree_walk(list(e), fun)
        e = fun(e)
        r.append(e)
    r = fun(r)
    return r

def cb_concat(t):
    if type(t) == list:
        while '.' in t:
            i = t.index('.')
            t[i - 1] = ['concat(', t[i - 1], t[i + 1]]
            del t[i + 1]
            del t[i]
    return t

def make_cb_ks(d):
    def cb_key_salt(t):
        if t == '$p':
            d['key'] = True
            return 'key'
        if t == '$s':
            d['salt'] = True
            return 'salt'
        if t == '$u':
            d['user'] = True
            return 'user'
        if t in consts:
            return [ 'const_str(', repr(t).replace(r'\\n', r'\n').replace('0xF7', '\xF7') ]
        return t
    return cb_key_salt


def tree_to_str(t):
    assert t[0].endswith('(')
    r = 'exp_' + t[0]
    first = True
    for e in t[1:]:
        if type(e) == list:
            e = tree_to_str(e)
        if not first:
            r += ', '
        first = False
        r += e
    r += ')'
    return r

class Empty(object):
    pass
g = Empty()

def evaluate_expression(s, d):
    print s
    code = []
    assert 'key' in d
    with L.evaluate_to(code):
        key = L.input_key()
        if 'salt' in d:
            salt = L.input_salt()
        if 'user' in d:
            user = L.input_salt2()

        # my_globals = Empty()
        # python_globals = globals()
        # python_locals = locals()
        # for f in 'md5 concat'.split(' '):
        #     python_locals[f] = lambda *args: python_globals['exp_' + f](my_globals, *args)

        r = eval(s)
        L.output_bytes(r)
    return code

code_plain_cache = {}

def exp_really_load_plain(name):
    if name == 'sha224':
        lname = 'sha256'
    elif name == 'sha384':
        lname = 'sha384'
    else:
        lname = name
    code = []
    with L.evaluate_to(code):
        p = L.load_plain(lname)
    if name == 'sha224':
        state = [
            0xc1059ed8, 0x367cd507, 0x3070dd17, 0xf70e5939, 0xffc00b31, 0x68581511, 0x64f98fa7, 0xbefa4fa4
        ]
        code = B.thread_code(
            code,
            [ B.override_state, state ],
            B.drop_last_output
        )
    if name == 'sha384':
        state = [
            0xcbbb9d5dc1059ed8, 0x629a292a367cd507,
            0x9159015a3070dd17, 0x152fecd8f70e5939,
            0x67332667ffc00b31, 0x8eb44a8768581511,
            0xdb0c2e0d64f98fa7, 0x47b5481dbefa4fa4
        ]
        code = B.thread_code(
            code,
            [ B.override_state, state ],
            B.drop_last_output,
            B.drop_last_output,
            B.drop_last_output
        )
    return code, p

def exp_load_plain_cached(name):
    if name in code_plain_cache:
        p, code, i = code_plain_cache[name]
    else:
        code, p = exp_really_load_plain(name)
        i = None
        i = B.collect_ifs(code)[p.name]
        code_plain_cache[name] = (p, code, i)
    L.Code.append_code(code)
    return p

def exp_make_hfun(name):
    if name not in g.hfun_cache:
        m = L.module_begin('hfun', name)
        # cfun = L.load_plain(name)
        cfun = exp_load_plain_cached(name)
        i = code_plain_cache[name][2]
        L.set_hfun_block_size(str(i['inputs'] * i['size']))
        # %% use 'state'
        L.set_hfun_digest_size(str(i['outputs'] * i['size']))
        L.Var.setup(i['size'], i['endianity'])
        k = L.input_key()
        r = L.run_merkle_damgard(cfun, k)
        L.output_bytes(r)
        L.module_end(m)
        g.hfun_cache[name] = m
    else:
        m = g.hfun_cache[name]
    return m

def make_exp_hfun(name):
    def exp_some_name_raw(b, do_hex = False):
        # L.print_bytes(b)
        m = exp_make_hfun(name)
        r = L.invoke_hfun(m, b)
        if do_hex:
            r = L.bytes_hex(r)
        # L.print_bytes(r)
        # L.debug_exit('d')
        return r
    def exp_some_name(b):
        r = exp_some_name_raw(b, True)
        return r
    return exp_some_name, exp_some_name_raw

for f in funcs:
    exec('exp_{0}, exp_{0}_raw = make_exp_hfun("{0}")'.format(f))

def exp_pad100(a):
    # %% what if password is longer than 100?
    return L.bytes_append_zeros_up_to(a, 100)

def exp_concat(a, b):
    return L.bytes_concat(a, b)

def exp_trunc32(b):
    return L.bytes_slice(b, 0, 32)

def exp_const_str(s):
    return L.new_bytes_const(s)

def exp_hex_upper(b):
    return L.bytes_hex_upper(b)

def read_dyna_tests(d):
    r = []
    for t in d['tests']:
        parts = t.split(':')
        h = parts[0]
        p = parts[1]
        if len(parts) > 2:
            assert len(parts) == 3
            user = parts[2]
            r.append((h, p, user))
        else:
            r.append((h, p))
    return r

def make_rdh(name):
    def read_dyna_hash(s):
        # if s.startswith('@dynamic'):
        #     t = s.split('@')
        #     h = t[2]
        #     t = h.split('$')
        #     if len(t) == 1:
        #         return None, t[0], None, None
        #     if len(t) == 2:
        #         return t[1], t[0], None, None
        #     die('not implemented {0}', s)
        tag = '$dynamic_' + name + '$'
        if s.startswith(tag):
            s = s[len(tag) : ]

            a = s.split('$', 1)
            h = a[0]
            if name != '1588':
                h = h.lower()
            salt = None
            salt2 = None
            if len(a) == 2:
                salt = a[1]
                hex_tag = 'HEX$'
                if salt.startswith(hex_tag):
                    salt = salt[len(hex_tag) : ].decode('hex')
                if salt.startswith('$U'):
                    salt2 = salt[2:]
                    salt = None
                else:
                    t = salt.split('$$U', 1)
                    if len(t) == 2:
                        salt, salt2 = t
                    else:
                        salt = t[0]
            return salt, h, None, salt2
    return read_dyna_hash

def gen_dyna_code(name, exp = None):
    g.hfun_cache = {}
    if exp == None:
        d = dynas_d[name]
        exp = d['expression']
    # Fixes
    exp = exp.replace('$p null_padded_to_len_100', 'pad100($p)')
    # exp = exp.replace('md5($p null_padded_to_len_100) RAdmin v2.x MD5', 'hex_upper(md5_raw(pad100($p)))')
    exp = exp.replace('PMD5(username)', '$s')
    exp = exp.replace('):$s', ').:.$s')
    # %% This one might be done using flag
    # exp = exp.replace('sha256($s.sha1($p)) (ColdFusion 11)', 'sha256($s.hex_upper(sha1_raw($p)))')
    exp = exp.replace('sha256($s.sha1($p)) (ColdFusion 11)', 'hex_upper(sha256_raw($s.hex_upper(sha1_raw($p))))')
    e = exp.split(' ')[0]
    if '(hash truncated to length 32)' in exp:
        e = 'trunc32(' + e + ')'
    l = split_expression(e)
    t = to_tree(l)
    # print l
    # print t
    t = tree_walk(t, cb_concat)
    properties = {}
    # %% properties may be checked by string search in the very beginning
    t = tree_walk(t, make_cb_ks(properties))
    s = tree_to_str(t)
    code = evaluate_expression(s, properties)
    return code, s

dyna_tested = {}
dyna_code = {}

dyna_disabled_parts = 'whirlpool gost utf16 tiger ripemd $s2 haval md2 panama skein uc( lc( sha3_ pad16( pad20( keccak sha224 sha384'.split(' ')

def test_dyna(name):
    exp = dynas_d[name]['expression']
    for h in dyna_disabled_parts:
        if h in exp:
            print 'due to', h, 'skipped hash', name, exp,
            print
            return 0
    print '  dyna', name, '=', exp
    # name = str(name)
    code, s = gen_dyna_code(name)
    dyna_code[name] = code
    # %% когда будут хеши со второй солью, надо будет их сводить вместе
    # s = s.replace('user', 'salt2')
    if s in dyna_tested:
        print 'dupe of formula:', s
        print '      this:', exp
        print '  previous:',  dyna_tested[s]
        return 0
    else:
        dyna_tested[s] = exp
    gc_fun = lambda *args: code
    tests = read_dyna_tests(dynas_d[name])
    if '(Skype MD5)' in exp:
        off = len('$dynamic_1401$') + 32
        tests = [(a[0][ : off] + a[0][off + 8 : ],) + a[1:] for a in tests]
    tr_fun = lambda *args: tests
    test_fun = test_salted_c if g.use_c else test_salted
    test_fun(name, name, make_rdh(name), get_code = gc_fun, test_reader = tr_fun, **fix)
    return 1

dynamics = dynas_d.keys()
dynamics.sort()

def test_both_dyna(name):
    g.use_c = False
    print '>>>> INTERPRETER'
    try:
        test_dyna(name)
    except Exception as e:
        if e.message != 'debug_exit':
            raise
    g.use_c = True
    print
    print '>>>> C BACKEND'
    # %% возможно, стоит делать пометку о тесте в си, то есть
    #  % различать си и интерпретатор, не считая повторы; или вообще,
    #  % не считать повторы для си
    for k in dyna_tested.keys():
        del dyna_tested[k]
    try:
        test_dyna(name)
    except Exception as e:
        if e.message == 'failed hash':
            print 'Exception:', e.message
        else:
            raise
    exit(1)

g.use_c = False

# g.use_c = True

# salt = 0
# pw = 0
# user = 0
# user_no_salt = 0
# pw_no_salt = 0
# for n in dynamics:
#     exp = dynas_d[n]['expression']
#     if '$s' in exp:
#         salt += 1
#     if '$p' in exp:
#         pw += 1
#         if '$s' not in exp:
#             pw_no_salt += 1
#     if '$u' in exp:
#         user += 1
#         if '$s' not in exp:
#             user_no_salt += 1
# print pw, salt, pw_no_salt, user, user_no_salt

def dyna_tests_to_c(l):
    o = []
    for t in l:
        a = t.split(':')
        if len(a) == 2:
            h, p = a
        elif len(a) == 3:
            h, p, u = a
            u = '$$U' + u
            if '$HEX$' in h:
                u = u.encode('hex')
            h += u
        s = '{"' + h + '", "' + p + '"},\n'
        o.append(s)
    return ''.join(o)

def dyna_use_salt(expression):
    return '$s' in expression or 'PMD5(username)' in expression

def quote_to_c(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')

def simple_parse(f, h, d):
    print f
    if type(f) == str:
        if f == h[ : len(f)]:
            return len(f)
        else:
            return None
    if type(f) != list:
        die('unreachable')
    if f[0] == 'seq':
        i = 0
        for e in f[1:]:
            r = simple_parse(e, h[i:], d)
            if r == None:
                return None
            i += r
        return i
    elif f[0] == 'hex':
        l = str(f[1])
        r = '' if f[2] == None else str(f[2])
        p = '[0-9a-fA-F]{' + l + ',' + r + '}'
        m = re.match(p, h)
        if m == None:
            return None
        t = m.group(0)
        ll = len(t)
        if f[3] == 'decode':
            t = t.decode('hex')
            if type(f[4]) == list:
                r = simple_parse(f[4], t, d)
                if r == None:
                    return None
                if r != ll / 2:
                    return None
                return ll
            else:
                d[f[4]] = t
                return ll
        else:
            d[f[3]] = t
            return ll
    elif f[0] == 'or':
        i = 1
        while i < len(f):
            if f[i] == True:
                r = 0
            else:
                # %% if f[i] is not a string, we may need to revert d
                r = simple_parse(f[i], h, d)
                if r == None:
                    i += 2
                    continue
            r2 = simple_parse(f[i + 1], h[r : ], d)
            if r2 == None:
                i += 2
                continue
            else:
                return r + r2
        return None
    elif f[0] == 'split':
        r = h.split(f[1], 1)
        if len(r) == 1:
            return None
        # забавно, а вот тут мы не можем передать исходную строку,
        # нужно обрезать её
        l = simple_parse(f[2], r[0], d)
        if l == None:
            return None
        rr = simple_parse(f[3], r[1], d)
        if rr == None:
            return None
        # а как же длина константа?
        return l + rr
    elif f[0] == 'any':
        d[f[1]] = h
        return len(h)
    die('unreachable 2')

g.trace_parser = False

def tracer(fun):
    def f2(f, level, save):
        # g.trace_parser = False
        r = fun(f, level, save)
        ind = '  ' * level
        typ = 'str' if type(f) == str else f[0]
        pre = 'printf("{1}tracer,  in {0}: {2} %d %d %.*s\\n", r{0}, len{0}, len{0}, h{0});\n'.format(level, ind, typ)
        # %% можно добавить пометки, когда не всё сматчилось
        post = 'printf("{1}tracer, out {0}: {2} %d\\n", r{0});\n'.format(level, ind, typ)
        return pre + r + post if g.trace_parser else r
    return f2

# def substitute_level(fun):
#     def f2(f, level, save):
#         r = fun(f, level, save)
#         r = Template(r).safe_substitute(upper = level, inner = level + 1)
#         return r
#     return f2

@tracer
# @substitute_level
def gen_parser(f, level, save):
    # Variable name may be 'ignore', it is ignored because
    # it is not in set for saving.
    assert 'ignore' not in save
    upper = level
    inner = level + 1
    # print f
    if type(f) == str:
        s = 'r{0} = ((strncmp(h{0}, "{1}", {2}) == 0) ? {2} : -1);\n'.format(level, quote_to_c(f), len(f))
        return s
    if type(f) != list:
        die('unreachable')
    if f[0] == 'seq':
        l = level + 1
        s = 'do {\n'
        s += 'char *h{0} = h{1}; int len{0} = len{1}; int r{0} = 0;\n'.format(l, level)
        for e in f[1:]:
            if e == None:
                # This branch allows to insert optional subpatterns.
                # %% support it in simple_parse()
                assert f[1:].count(None) != len(f[1:])
                continue
            s += 'r{0} = 0;\n'.format(l)
            s += gen_parser(e, l, save)
            s += 'if (r{0} == -1) {{ r{1} = -1; break; }}\n'.format(l, level)
            s += 'r{1} += r{0}; len{0} -= r{0}; h{0} += r{0};\n'.format(l, level)
        # Тут можно было бы проверить, что ничего не осталось; но не стоит.
        s += '} while (0);\n'
        return s
    elif f[0] == 'hex':
        l = str(f[1])
        min_len, max_len = f[1:3]
        if max_len == None:
            # %% better way?
            max_len = 1000
        s = 'do {\n'
        s += 'for (i = 0; i < {0}; i++)\n'.format(max_len)
        s += '    if (atoi16[ARCH_INDEX(h{0}[i])] == 0x7F)\n'.format(level)
        s += '        break;\n'
        # %% check parity here? trunc to lower even?
        s += 'if (i < {0}) {{ r{1} = -1; break; }}\n'.format(min_len, level)
        s += 'r{0} += i;\n'.format(level)
        if f[3] != 'decode':
            if f[3] in save:
                s += 'memcpy({0}, h{1}, i); {0}_len = i;\n'.format(f[3], level)
            # s += 'break;\n'
        else:
            l = level + 1
            # %% using max length, we might get rid of VLA
            s += 'int len{0} = i / 2; char h{0}[len{0}];\n'.format(l)
            s += 'for (i = 0; i < len{0}; i++)\n'.format(l)
            s += '    h{0}[i] = (atoi16[ARCH_INDEX(h{1}[i * 2])] << 4) | atoi16[ARCH_INDEX(h{1}[i * 2 + 1])];\n'.format(l, level)
            if type(f[4]) == list:
                s += 'int r{0} = 0;\n'.format(l)
                s += gen_parser(f[4], l, save)
                s += 'if (r{0} != len{0}) r{1} = -1;\n'.format(l, level)
            else:
                if f[4] in save:
                    s += 'memcpy({0}, h{1}, i); {0}_len = i;\n'.format(f[4], l)
                # s += 'break;\n'
        s += '} while (0);\n'
        return s
    elif f[0] == 'b64':
        from_t = f[1][0]
        to_t = f[1][1]
        flags = f[1][2:]
        if len(flags) == 0:
            flags.append('NO_FLAGS')
        flags = ' | '.join('flg_Base64_' + f for f in flags)
        max_len = 1000
        # %% if we decoded something, we report full len.
        # %% base64_convert resets length to strlen(), it is not good
        #  % for us!
        s = r'''
        do {
            char h$inner[$max_len];
            int len$inner = base64_convert(h$upper, e_b64_$from_t, len$upper, h$inner, e_b64_$to_t, $max_len, $flags);
            printf("len: %d\n", len$inner);
            if (len$inner == 0) { r$upper = -1; break; }
            r$upper = len$upper;
        '''.strip() + '\n'
        if f[2] == 'decode':
            if type(f[3]) == list:
                s += 'int r$inner = 0;\n'
                s += gen_parser(f[3], inner, save)
                # print s
                # s += 'printf("b64: %d %d\\n", r$inner, len$inner);\n'
                s += 'if (r$inner != len$inner) { r$upper = -1; break; }\n'
            else:
                if f[3] in save:
                    s += 'memcpy({0}, h$inner, len$inner); {0}_len = len$inner;\n'.format(f[3])
        else:
            if f[2] in save:
                # %% save undecoded?
                s += 'memcpy({0}, h$inner, len$inner); {0}_len = len$inner;\n'.format(f[2])
        s += '} while (0);\n'
        s = Template(s).safe_substitute(**locals())
        return s
    elif f[0] == 'or':
        l = level + 1
        s = 'do {\n'
        s += 'char *h{0} = h{1}; int len{0} = len{1}; int r{0} = 0;\n'.format(l, level)
        s += 'int r{0}_beginning;\n'.format(l)
        for i in range(1, len(f), 2):
            if f[i] == True:
                s += 'r{0}_beginning = 0;\n'.format(l)
            else:
                s += gen_parser(f[i], l, save)
                s += 'r{0}_beginning = r{0};\n'.format(l)
            s += 'if (r{0}_beginning != -1) {{\n'.format(l)
            s += 'h{0} = h{1} + r{0}_beginning; len{0} = len{1} - r{0}_beginning;\n'.format(l, level)
            # %% если проверять, что мы всегда добавляем, то можно
            #  % сократить обнуления и некоторые сложения; в частности
            #  % избавиться от r*_beginning
            s += 'r{0} = 0;\n'.format(l)
            s += gen_parser(f[i + 1], l, save)
            s += 'r{1} = ((r{0} == -1) ? -1 : r{0}_beginning + r{0});\n'.format(l, level)
            # если мы попали в ветку, то всё, другие варианты не смотрим
            s += 'break;\n'
            s += '}\n'
            # если мы дошли до конца проверок, значит, ничего не нашли
            s += 'r{0} = -1;\n'.format(level)
        s += '} while (0);\n'
        return s
    elif f[0] == 'split' or f[0] == 'split_right':
        assert len(f) == 4
        parser_left = gen_parser(f[2], inner, save)
        parser_right = gen_parser(f[3], inner, save)
        const = quote_to_c(f[1])
        const_len = len(f[1])
        s = r'''
        do {
            printf("split: begin, %d\n", r$upper);
        '''
        if f[0] == 'split':
            s += r'''
            char *sub = memmem(h$upper, len$upper, "$const", $const_len);
            if (sub == 0) { r$upper = -1; break; }
            '''
        else:
            s += r'''
            char *sub, *last = 0;
            int sub_len = len$upper;
            sub = memmem(h$upper, len$upper, "$const", $const_len);
            while (sub) {
                last = sub;
                sub += $const_len;
                sub_len = len$upper - (sub - h$upper);
                sub = memmem(sub, sub_len, "$const", $const_len);
            }
            if (last == 0) { r$upper = -1; break; }
            sub = last;
            '''
        s += r'''
            r$upper += $const_len;
            char *h$inner = h$upper;
            int len$inner = sub - h$upper;
            int r$inner = 0;
            $parser_left
            if (r$inner != len$inner) { r$upper = -1; break; }
            r$upper += r$inner;
            h$inner = sub + $const_len;
            len$inner = len$upper - len$inner - $const_len;
            r$inner = 0;
            $parser_right
            printf("split: r_upper %d r_inner %d\n", r$upper, r$inner);
            if (r$inner == -1) { r$upper = -1; break; }
            printf(">> %d %d\n", r$upper, r$inner);
            r$upper += r$inner;
            printf("split, in cycle: %d\n", r$upper);
        } while (0);
        printf("split, end: %d\n", r$upper);
        '''.strip() + '\n'
        s = Template(s).safe_substitute(**locals())
        return s
    elif f[0] == 'any':
        s = ''
        if f[1] in save:
            s += 'memcpy({0}, h{1}, len{1}); {0}_len = len{1};\n'.format(f[1], level)
        s += 'r{1} = len{1};\n'.format(f[1], level)
        return s
    elif f[0] == 'decimal':
        var = f[1]
        # %% overflows (and related undefined behaviour)
        saving = r'''
            $var = 0;
            for (i = 0; '0' <= h$upper[i] && h$upper[i] <= '9'; i++) {
                $var *= 10;
                $var += h$upper[i] - '0';
            }
        '''.strip() + '\n'
        saving = Template(saving).safe_substitute(**locals()) if var in save else ''
        s = r'''
        do {
            for (i = 0; i < len$upper && '0' <= h$upper[i] && h$upper[i] <= '9'; i++)
                ;
            if (i == 0) {
                r$upper = -1;
                break;
            } else {
                r$upper += i;
            }
            $saving
        } while (0);
        '''.strip() + '\n'
        return Template(s).safe_substitute(**locals())
    elif f[0] == 'set':
        s = ''
        if f[1] in save:
            s = '{0} = {1};\n'.format(f[1], f[2])
        return s
    die('unreachable 2 on: {0}', f[0])

def gen_parser_full(f, save):
    s = 'char *h0 = ciphertext;\n'
    s += 'int len0 = strlen(ciphertext);\n'
    s += 'int r0 = 0;\n'
    s += 'int i;\n'
    s += gen_parser(f, 0, save)
    # %% assert that result is smaller than lengths?
    # s += 'if (r0 == -1) return 0;'
    return s

# int atoi16[128] = {
# 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 127, 127, 127, 127, 127, 127, 127, 10, 11, 12, 13, 14, 15, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 10, 11, 12, 13, 14, 15, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127
# };

parser_test = r'''
#define _GNU_SOURCE
#include <string.h>
#include <stdio.h>
#include "$john_base/base64_convert.h"
int main(void)
{
    char *ciphertext = "$hash";
    char hash[200] = { 0 };
    int hash_len;
    char salt[200] = { 0 };
    int salt_len;
    char salt2[200] = { 0 };
    int salt2_len;
    unsigned long long rounds = 0;
    char *h0 = ciphertext;
    int len0 = strlen(ciphertext);
    int r0 = 0;
    int i;
    $parser_code;
    printf("r: %d %d\n", r0, strlen(ciphertext));
    printf("hash: %s <<\n", hash);
    printf("salt: %s <<\n", salt);
    printf("salt2: %s <<\n", salt2);
    printf("rounds: %llu <<\n", rounds);
    return 0;
}
'''

def debug_parser(f, h):
    g.trace_parser = True
    vc = gen_parser(f, 0, save = set(['hash', 'salt', 'salt2', 'rounds']))
    vc = parser_test.replace('$parser_code;', vc).replace('$hash', h).replace('$john_base', U.john_base)
    with open('t.c', 'w') as f:
        f.write(vc)
    # %% quoting
    os.system('''(sed -ne '0,/simple conerter of strings or raw memory/ p' < {0}base64_convert.c; cat t.c) > t2.c && (d=`pwd`; cd {0}; gcc "$d"/t2.c -o "$d"/a.out) && ./a.out'''.format(U.john_base))
    exit(0)

# h = "$dynamic_1015$1d586cc8d137e5f1733f234d224393e8$HEX$f063f05d242455706f737467726573"
# d = {}
# i = simple_parse(f, h, d)
# print h
# print i, len(h), i == len(h), d
# exit(1)

to_be_tested = []

def gen_dyna_format(name):
    dyna = dynas_d[name]
    exp =  dyna['expression']
    uses_salt = int(dyna_use_salt(exp))
    uses_user = int('$u' in exp)
    if test_dyna(name) == 0:
        return 0
        die('unsupported')
    code = dyna_code[name]
    c_template = 'john_dyna_pw'
    c_code = U.load_code_template(c_template)
    tag = '$dynamic_' + name + '$'
    algo_label = 'dk_dyna_' + name
    # interface = B.get_interface(code)
    tests = dyna_tests_to_c(dyna['tests'])
    bfs = None
    # %% use interface
    # We store as hex, hence doubled size
    if '(hash truncated to length 32)' in exp:
        bfs = 32
    elif exp.startswith('sha1('):
        bfs = 40
    elif exp.startswith(('md5(', 'md4(')):
        bfs = 32
    elif exp.startswith('sha256('):
        bfs = 64
    elif exp.startswith('sha512('):
        bfs = 128
    if bfs == None:
        die('not implemented')
    vs = {
        'fmt_struct_name': algo_label,
        'format_name': algo_label,
        'algo_name': 'dk ' + quote_to_c(exp),
        'tag': tag,
        'plaintext_length': 125,
        # %% compute 32
        'binary_form_size': bfs,
        'tests': tests,
        'salted': int(uses_salt or uses_user)
    }
    U.setup_vars(vs)
    if uses_salt and uses_user:
        f = [ 'seq',
              tag, [ 'hex', bfs, bfs, 'hash' ],
              '$', [ 'or',
                     # %% this construct with hex might work
                     #  % differently: unhex if tag, then apply split
                     #  % (this code should be inserted once then, but
                     #  % work with different pointers); it may need a
                     #  % special construction.
                     'HEX$', [ 'hex', 0, None, 'decode',
                               [ 'split', '$$U',
                                 [ 'any', 'salt' ],
                                 [ 'any', 'salt2' ] ] ],
                     True, [ 'split', '$$U',
                             [ 'any', 'salt' ],
                             [ 'any', 'salt2' ] ] ] ]
    elif uses_salt:
        f = [ 'seq',
              tag, [ 'hex', bfs, bfs, 'hash' ],
              '$', [ 'or',
                     'HEX$', [ 'hex', 0, None, 'decode', 'salt' ],
                     True, [ 'any', 'salt' ] ] ]
    elif uses_user:
        f = [ 'seq',
              tag, [ 'hex', bfs, bfs, 'hash' ],
              # fix for Skype MD5
              '00000000' if name == '1401' else None,
              '$', [ 'or',
                     'HEX$', [ 'hex', 0, None, 'decode',
                               [ 'seq', '$U', [ 'any', 'salt2' ] ] ],
                     '$U', [ 'any', 'salt2' ] ] ]
    else:
        f = [ 'seq', tag, [ 'hex', bfs, bfs, 'hash' ] ]
    # %% maybe generate 1 function and call from valid() and others?
    B.global_vars['code_valid'] = gen_parser_full(f, save = set())
    B.global_vars['code_binary'] = gen_parser_full(f, save = set(['hash']))
    B.global_vars['code_get_salt'] = gen_parser_full(f, save = set(['salt', 'salt2']))
    interleave = 1
    B.global_vars['batch_size'] = 1
    B.global_vars['interleave'] = interleave
    # B.global_vars['vectorize'] = 1
    d = B.thread_code(code, *fix['transforms'])
    out_file = U.john_base + 'dk_dyna_' + name + '_fmt_plug.c'
    B.thread_code(d, [ O.gen, out_file, c_code, {}, B.global_vars ])
    # print 'copy:', out_file
    to_be_tested.append((algo_label, out_file))
    # if U.build_john():
    #     U.run_test(algo_label, 1)
    #     U.count_bytes(out_file[:-1] + 'o')
    return 1

# gen_dyna_format('1001')

# gen_dyna_format('1008')

# gen_dyna_format('1506')

# gen_dyna_format('1401')

# gen_dyna_format('1016')

# gen_dyna_format('1015')

# for n in '1034 1401 1506'.split(' '):
#     gen_dyna_format(n)

# test_both_dyna('1008')

# test_both_dyna('1350')

# test_dyna('1401')

# test_dyna('1588')

# k = 0
# for n in dynamics:
#     k += test_dyna(n)
#     print
# print 'dynamics, good count:', k

# k = 0
# for n in dynamics:
#     k += gen_dyna_format(n)
#     print
# print k

# ######################################################################

# # Template to make generator
# def gen_format(name):
#     uses_salt = %%
#     uses_user = %%
#     code = %%
#     c_template = 'john_dyna_pw'
#     c_code = U.load_code_template(c_template)
#     tag = %%
#     algo_label = %%
#     # interface = B.get_interface(code)
#     tests = %% slurp
#     bfs = %%
#     vs = {
#         'fmt_struct_name': algo_label,
#         'format_name': algo_label,
#         'algo_name': 'dk ' + quote_to_c(exp),
#         'tag': tag,
#         'plaintext_length': 125,
#         # %% compute 32
#         'binary_form_size': bfs,
#         'tests': tests,
#         'salted': int(uses_salt or uses_user)
#     }
#     U.setup_vars(vs)
#     f = %%
#     # %% maybe generate 1 function and call from valid() and others?
#     B.global_vars['code_valid'] = gen_parser_full(f, save = set())
#     B.global_vars['code_binary'] = gen_parser_full(f, save = set(['hash']))
#     B.global_vars['code_get_salt'] = gen_parser_full(f, save = set(['salt', 'salt2']))
#     interleave = 1
#     B.global_vars['batch_size'] = 1
#     B.global_vars['interleave'] = interleave
#     # B.global_vars['vectorize'] = 1
#     d = B.thread_code(code, *fix['transforms'])
#     # %%
#     # out_file = U.john_base + 'dk_dyna_' + name + '_fmt_plug.c'
#     B.thread_code(d, [ O.gen, out_file, c_code, {}, B.global_vars ])
#     to_be_tested.append(algo_label)
#     return 1

def gen_format(label, bfs, code, hash_format):

    g.trace_parser = True

    # debug_parser(hash_format, "$pbkdf2-sha256$1000$b1dWS2dab3dKQWhPSUg3cg$UY9j5wlyxtsJqhDKTqua8Q3fMp0ojc2pOnErzr8ntLE")

    counts = B.count_instructions_main(code)
    uses_salt = int('input_salt' in counts or 'input_salt2' in counts or 'input_rounds' in counts)
    c_template = 'john_dyna_pw'
    c_code = U.load_code_template(c_template)
    if type(label) == tuple:
        label, tests = label
    else:
        tests = U.slurp_dk_file('hash_tests/john_' + label + '.c')
    algo_label = 'dk_' + label
    # interface = B.get_interface(code)
    vs = {
        'fmt_struct_name': algo_label.replace('-', '_'),
        'format_name': algo_label,
        'algo_name': 'dk',
        'tag': 'should not be used',
        'plaintext_length': 125,
        'binary_form_size': bfs,
        'tests': tests,
        'salted': int(uses_salt or uses_user)
    }
    U.setup_vars(vs)
    f = hash_format
    # %% maybe generate 1 function and call from valid() and others?
    B.global_vars['code_valid'] = gen_parser_full(f, save = set())
    B.global_vars['code_binary'] = gen_parser_full(f, save = set(['hash']))
    B.global_vars['code_get_salt'] = gen_parser_full(f, save = set(['salt', 'salt2', 'rounds']))
    interleave = 1
    B.global_vars['batch_size'] = 1
    B.global_vars['interleave'] = interleave
    # B.global_vars['vectorize'] = 1
    d = B.thread_code(code, *fix['transforms'])
    # %%
    # out_file = U.john_base + 'dk_dyna_' + name + '_fmt_plug.c'
    out_file = U.john_base + 'dk_' + label + '_fmt_plug.c'
    B.dump(code, 'dump.bytecode')
    B.thread_code(d, [ O.gen, out_file, c_code, {}, B.global_vars ])
    to_be_tested.append((algo_label, out_file))
    return 1

def no_gen_format(*args):
    pass

# no_gen_format = gen_format

# no_gen_format('pbkdf2-hmac-sha512', 64,
#            B.get_code_full('pbkdf2-hmac-sha512'),
#            [ 'or',
#              '$pbkdf2-hmac-sha512$', [ 'seq',
#                                        [ 'decimal', 'rounds' ],
#                                        '.',
#                                        [ 'split', '.',
#                                          # [ 'any', 'salt' ],
#                                          [ 'hex', 0, None, 'decode', 'salt'],
#                                          [ 'hex', 128, 128, 'decode', 'hash']
#                                          ] ],
#              '$ml$', [ 'seq',
#                        [ 'decimal', 'rounds' ],
#                        '$',
#                        [ 'split', '$',
#                          # [ 'any', 'salt' ],
#                          [ 'hex', 0, None, 'decode', 'salt'],
#                          [ 'hex', 128, 128, 'decode', 'hash' ] ],
#                        # We ignore blocks after the first.
#                        # %% it might be good for cmp_exact() though
#                        # %% можно было бы проверять, что длина кратна 128
#                        [ 'hex', 0, None, 'ignore' ] ],
#              'grub.pbkdf2.sha512.', [ 'seq',
#                                        [ 'decimal', 'rounds' ],
#                                        '.',
#                                        [ 'split', '.',
#                                          # [ 'any', 'salt' ],
#                                          [ 'hex', 0, None, 'decode', 'salt'],
#                                          [ 'hex', 128, 128, 'decode', 'hash']
#                                          ] ] ]
#            )

def make_pbkdf2(name):
    g.hfun_cache = {}
    code = []
    with L.evaluate_to(code):
        L.Var.setup('be', 4)
        s = L.input_salt()
        key = L.input_key()
        rounds = L.input_rounds()
        hfun = exp_make_hfun(name)
        r = L.pbkdf2_hmac(hfun, key, s, rounds, 1)
        L.output_bytes(r)
    return code

# no_gen_format(
#     'pbkdf2-hmac-sha256', 32,
#     make_pbkdf2('sha256'),
#     [ 'or',
#       '$pbkdf2-sha256$', [ 'seq',
#                            [ 'decimal', 'rounds' ],
#                            '$',
#                            [ 'split', '$',
#                              [ 'b64', [ 'mime', 'raw', 'MIME_PLUS_TO_DOT' ], 'decode', 'salt' ],
#                              [ 'b64', [ 'mime', 'raw', 'MIME_PLUS_TO_DOT' ], 'decode', 'hash' ] ] ],
#       '$8$', [ 'split', '$',
#                # %% check len == 14?
#                [ 'any', 'salt' ],
#                [ 'seq',
#                  [ 'b64', [ 'crypt', 'raw' ], 'decode', 'hash' ],
#                  [ 'set', 'rounds', 20000 ] ] ] ]
# )

def rounds_salt_hash_hex_dollars(bfs):
    hex_len = bfs * 2
    return [
        'seq',
        [ 'decimal', 'rounds' ],
        [ 'or',
            '$', [ 'split', '$',
                    [ 'hex', 0, None, 'decode', 'salt' ],
                    [ 'seq',
                      [ 'hex', hex_len, hex_len, 'decode', 'hash' ],
                      [ 'hex', 0, None, 'ignore' ] ] ],
            '.', [ 'split', '.',
                    [ 'hex', 0, None, 'decode', 'salt' ],
                    [ 'seq',
                      [ 'hex', hex_len, hex_len, 'decode', 'hash' ],
                      [ 'hex', 0, None, 'ignore' ] ] ] ] ]

# no_gen_format(
#     'pbkdf2-hmac-md5', 16,
#     make_pbkdf2('md5'),
#     [ 'seq', '$pbkdf2-hmac-md5$', rounds_salt_hash_hex_dollars(16) ]
# )

# gen_format(
#     'pbkdf2-hmac-md4', 16,
#     make_pbkdf2('md4'),
#     [ 'seq', '$pbkdf2-hmac-md4$', rounds_salt_hash_hex_dollars(16) ]
# )

# no_gen_format(
#     'pbkdf2-hmac-sha1', 20,
#     make_pbkdf2('sha1'),
#     [ 'or',
#       '$pbkdf2-hmac-sha1$', rounds_salt_hash_hex_dollars(20),
#       # '{PKCS5S2}', [ 'b64', [ 'mime', 'raw' ], 'decode',
#       #                [ 'seq',
#       #                  [ 'fixed_len', 16, 'salt'],
#       #                  [ 'fixed_len', 32, 'hash'] ] ],
#       # '$p5k2$', [ 'seq',
#       #             [ 'decimal', 'rounds' ],
#       #             '$',
#       #             [ 'split', '$',
#       #               [ 'b64', [ 'mime', 'raw', 'MIME_DASH_UNDER' ], 'decode', 'salt' ],
#       #               [ 'b64', [ 'mime', 'raw', 'MIME_DASH_UNDER' ], 'decode', 'hash' ] ] ]
#     ]
# )


def make_hmac(name):
    g.hfun_cache = {}
    code = []
    with L.evaluate_to(code):
        L.Var.setup(8, 'be')
        key = L.input_key()
        s = L.input_salt()
        hfun = exp_make_hfun(name)
        r = L.hmac(hfun, key, s)
        L.output_bytes(r)
    return code

def hmac_hash_format(bfs):
    f = [
        'or',
        # %% we use any+ignore, but there should nothing; either
        #  % implement 'or' without beginning, or 'empty' matcher.
        # %% right-to-left search would be easier, searching for 1
        #  % char, not substring
        [ 'split_right', '#',
          [ 'any', 'salt' ],
          [ 'hex', bfs * 2, bfs * 2, 'decode', 'hash' ] ], [ 'any', 'ignore' ],
        # JWT hash format
        [ 'split_right', '.',
          [ 'any', 'salt' ],
          [ 'b64', [ 'mime', 'raw' ], 'decode', 'hash' ] ], [ 'any', 'ignore'] ]
    return f

def gen_hmac(name, bfs, tests = None):
    label = 'hmac-' + name
    if tests != None:
        label = (label, tests)
    gen_format(label, bfs, make_hmac(name), hmac_hash_format(bfs))

# gen_format(
#     'hmac-sha512', 64,
#     make_hmac('sha512'),
#     [ 'split_right', '#',
#       [ 'any', 'salt' ],
#       [ 'hex', 128, 128, 'decode', 'hash' ] ]
# )

# gen_hmac('sha512', 64)

def grep_tests(fname, mark_from, in_each = None):
    with open(U.john_base + fname, 'r') as f:
        reading = False
        tests = []
        for l in f:
            if '{NULL}' in l and reading:
                break
            if reading and (in_each == None or in_each in l):
                l = l.lstrip('\t')
                tests.append(l)
            if mark_from in l:
                reading = True
        return ''.join(tests)


# gen_hmac('sha256', 32, grep_tests('hmacSHA256_fmt_plug.c', 'fmt_tests tests'))

# gen_hmac('sha1', 20, grep_tests('hmacSHA1_fmt_plug.c', 'tests'))


# gen_format(
#     ('hmac-md5', grep_tests('hmacMD5_fmt_plug.c', 'tests')), 16,
#     make_hmac('md5'),
#     [ 'or',
#       '$cram_md5$', [ 'split', '$',
#                       [ 'b64', [ 'mime', 'raw', 'MIME_TRAIL_EQ' ], 'decode', 'salt' ],
#                       [ 'b64', [ 'mime', 'raw', 'MIME_TRAIL_EQ' ], 'decode',
#                         [ 'split_right', ' ',
#                           [ 'any', 'ignore' ],
#                           [ 'hex', 32, 32, 'decode', 'hash' ] ] ] ],
#       True, [ 'split_right', '#',
#               [ 'any', 'salt' ],
#               [ 'hex', 32, 32, 'decode', 'hash' ] ] ]
# )

# %% failure
# gen_hmac('sha224', 32 - 4, grep_tests('hmacSHA256_fmt_plug.c', 'tests_224'))

# gen_format(
#     ('IPB2', grep_tests('IPB2_fmt_plug.c', 'tests')), 32,
#     gen_dyna_code('no_name', 'md5(md5($s).md5($p))')[0],
#     [ 'seq',
#       '$IPB2$', [ 'split', '$',
#                   [ 'hex', 0, None, 'decode', 'salt' ],
#                   # [ 'any', 'salt' ],
#                   [ 'hex', 32, 32, 'hash' ] ] ]
# )


# # unfinished
# def make_md5crypt():
#     def concat(*args):
#         if len(args) == 1:
#             return args[0]
#         return L.bytes_concat(concat(*args[:-1]), args[-1])
#     def append(var, *args):
#         L.bytes_assign(var, concat(var, *args))
#     g.hfun_cache = {}
#     code = []
#     with L.evaluate_to(code):
#         L.Var.setup(4, 'le')
#         pw = L.input_key()
#         s = L.input_salt()
#         magic = L.new_bytes_const("$1$")
#         hfun = exp_make_hfun('md5')
#         md5 = lambda k: L.invoke_hfun(hfun, k)
#         t = pw
#         # t = concat(t, magic)
#         t = concat(t, s)
#         final = md5(concat(pw, s, pw))
#         tt = L.new_bytes()
#         pl = L.bytes_len(pw)
#         i = L.cycle_range('fill', 0, pl - 1, 16)
#         diff = pl - i
#         L.if_condition('fill_len', diff >= 16)
#         append(tt, final)
#         L.if_else('fill_len')
#         append(tt, L.bytes_slice(final, 0, diff))
#         L.if_end('fill_len')
#         L.cycle_end('fill')
#         tt2 = L.new_bytes()
#         i = L.new_var()
#         i // pl
#         fb = L.bytes_slice(final, 0, 1)
#         pb = L.bytes_slice(pw, 0, 1)
#         L.cycle_while_begin('weird')
#         L.cycle_while('weird', i > 0)
#         L.if_condition('in_weird', i & 1)
#         append(tt2, fb)
#         L.if_else('in_weird')
#         append(tt2, pb)
#         L.if_end('in_weird')
#         i // (i >> 1)
#         L.cycle_end('weird')
#         final = md5(concat(t, tt, tt2))
#         # i = L.cycle_const_range('main', 0, 1000 - 1, 1)
#         # L.cycle_end('main')
#         # for i in range(1000):
#         #     if i & 1:
#         #         a = pw
#         #     else:
#         #         a = final
#         #     if i % 3:
#         #         a = concat(a, s)
#         #     if i % 7:
#         #         a = concat(a, pw)
#         #     if i & 1:
#         #         a = concat(a, final)
#         #     else:
#         #         a = concat(a, pw)
#         #     final = md5(a)
#         pw_pw = concat(pw, pw)
#         s_pw = concat(s, pw)
#         s_pw_pw = concat(s, pw, pw)
#         pw_s = concat(pw, s)
#         pw_s_pw = concat(pw, s, pw)
#         for i in range(0, 1000, 2):
#             t = (('s_' if i % 3 else '') +
#                  ('pw_' if i % 7 else '') +
#                  'pw')
#             final = md5(concat(final, eval(t)))
#             t = ('pw' +
#                  ('_s' if i % 3 else '') +
#                  ('_pw' if i % 7 else ''))
#             final = md5(concat(eval(t), final))
#         L.output_bytes(final)
#     return code
# gen_format(
#     # %% add other tests too
#     ('md5crypt', grep_tests('MD5_fmt.c', 'tests', '"$1$')), 16,
#     make_md5crypt(),
#     [ 'or',
#       '$1$', [ 'split_right', '$',
#                 [ 'any', 'salt' ],
#                 # [ 'hex', 0, None, 'decode', 'salt' ],
#                 [ 'b64', [ 'cryptBS', 'raw' ], 'decode', 'hash' ] ] ]
# )

def print_benchmark(name, second = False):
    search_for = 'Benchmarking: ' + name
    search_for = search_for.lower()
    search_for = (search_for + ' ', search_for + ', ')
    printed = False
    with open('j_benchmark1', 'r') as f:
        reading = False
        for l in f:
            if l.lower().startswith(search_for):
                reading = True
            if reading:
                print l.rstrip('\n')
                printed = True
            if l == '\n':
                reading = False
    if printed == False:
        if second == True:
            die("benchmark was not found and can't be generated")
        # %% quoting?
        r = os.system("./JohnTheRipper/run/john --format='" + name + "' --test=1 >> j_benchmark1")
        if r != 0:
            die('john failure')
        print_benchmark(name, True)

# print_benchmark('afs')

def dk_to_john_name(n):
    if n.startswith('dk_dyna_syn'):
        n = n.replace('dk_dyna_', '')
        return 'dynamic=' + dynas_d[n]['expression']
    if n.startswith('dk_dyna_'):
        return n.replace('dk_dyna', 'dynamic')
    return n.replace('dk_', '')

def finish_with_build():
    if U.build_john():
        for n, f in to_be_tested:
            if not os.path.exists(f[:-1] + 'o'):
                # %% quoting?
                print 'reconfiguring'
                r = os.system('cd {0} && ./configure --disable-openmp >/dev/null'.format(U.john_base))
                print 'reconf done, exit code:', r
                if 0 == r:
                    U.build_john()
        for n, f in to_be_tested:
            # if 'syn' not in n:
            #     continue
            U.run_test(n, 1)
            jn = dk_to_john_name(n)
            print_benchmark(jn)

gen_dyna_format('0')

finish_with_build()
