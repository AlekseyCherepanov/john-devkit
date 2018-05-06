# -*- coding: utf-8 -*-
# "plug" with implementation of modules (functions) and "bytes" type

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

def b_input_key(name):
    # a('$type {0} = dk_input_key();', name)
    c('#define {0} dk_input_key()', name)
    c('size_t {0}_len = dk_input_key_len();', name)

def b_input_salt(name):
    # a('$type {0} = dk_input_salt();', name)
    c('#define {0} dk_input_salt()', name)
    c('size_t {0}_len = dk_input_salt_len();', name)

def b_input_salt2(name):
    # a('$type {0} = dk_input_salt2();', name)
    c('#define {0} dk_input_salt2()', name)
    c('size_t {0}_len = dk_input_salt2_len();', name)

def b_output_bytes(string):
    c('dk_output_bytes({0});', string)


def b_run_merkle_damgard(res, function, string):
    die("don't use this, apply filter B.fix_run_merkle_damgard")

def b_hfun_block_size(name, fun):
    die("don't use this, apply filter B.compute_hfun_sizes")

func_template_plain = r'''
$functions
static void $func_name($type *in, $type *out)
{
#define dk_input(i) (in[(i)])
#define dk_output(v, i) (out[(i)] = (v))
#define dk_input_state(i) (out[(i)])
    $code
#undef dk_input
#undef dk_output
#undef dk_input_state
}
'''

func_template_hfun = r'''
$functions
static void $func_name(unsigned char *in_b, size_t in_b_len, unsigned char *out_b)
{
#define dk_input_key() in_b
#define dk_input_key_len() in_b_len
#define dk_output_bytes(v) memcpy(out_b, v, v ## _len)
    $code;
#undef dk_input_key_len
#undef dk_input_key
#undef dk_output_bytes
}
'''

func_template_fun2 = r'''
$functions
static void $func_name(unsigned char *in_b, size_t in_b_len, unsigned char *in2_b, size_t in2_b_len, unsigned char *out_b, size_t *out_b_len)
{
#define dk_input_key() in_b
#define dk_input_key_len() in_b_len
#define dk_input_salt() in2_b
#define dk_input_salt_len() in2_b_len
#define dk_output_bytes(v) memcpy(out_b, v, v ## _len); (*out_b_len = v ## _len)
    $code;
#undef dk_input_key_len
#undef dk_input_key
#undef dk_output_bytes
#undef dk_input_salt
#undef dk_input_salt_len
}
'''

func_templates = {}
for i in dir():
    prefix = 'func_template_'
    if i.startswith(prefix):
        b = i[len(prefix) : ]
        func_templates[b] = eval(i)


def b_run_merkle_damgard_with_state(res, function, string, offset, *initial_state):
    s = ''
    for i, v in enumerate(initial_state):
        s += 'out[{0}] = {1};\n'.format(i, v)
    i = g.ifs[function]
    size = i['size']
    endianity = i['endianity']
    inputs = i['inputs']
    outputs = i['outputs']
    # we use size of state for size of out array, because we pass
    # state through it and all (known to us) hashes has bigger or
    # equal state than outputs
    out_count = len(initial_state)
    if out_count < i['outputs']:
        die('sizes failure in run_m..d.._with_state')
    need_swap = 0 if endianity == 'le' else 1
    # %% insert type from func
    c(r'''
    // %% unique names for in and out
#define in {res}_in
#define out {res}_out
    // $type in[{inputs}] = {{ 0 }};
    $type in[{inputs}];
    $type out[{out_count}];
    {{
        {0}
        size_t i = 0;
        size_t t = {string}_len;
        while (t >= {inputs} * {size}) {{
            memcpy(in, ((unsigned char *){string}) + {string}_len - t, {inputs} * {size});
            t -= {inputs} * {size};
            if ({need_swap}) {{
                for (i = 0; i < {inputs}; i++) {{
                    in[i] = JOHNSWAP$bits(in[i]);
                }}
            }}
            {function}(in, out);
        }}
        memset(in, 0, {inputs} * {size});
        memcpy(in, ((unsigned char *){string}) + {string}_len - t, t);
        ((unsigned char *)in)[t] = 0x80;
        if ({need_swap}) {{
            for (i = 0; i < {inputs}; i++) {{
                in[i] = JOHNSWAP$bits(in[i]);
            }}
        }}
        if (t <= {inputs} * {size} - 2 * {size} - 1) {{
            in[{inputs} - 2 + {need_swap}] = (({string}_len + {offset}) << 3);
        }} else {{
            {function}(in, out);
            // %% is memset() needed here?
            memset(in, 0, {inputs} * {size});
            in[{inputs} - 2 + {need_swap}] = (({string}_len + {offset}) << 3);
        }}
        {function}(in, out);
        if ({need_swap}) {{
            for (i = 0; i < {outputs}; i++) {{
                out[i] = JOHNSWAP$bits(out[i]);
            }}
        }}
    }}
    unsigned char *{res} = (unsigned char *)out;
    size_t {res}_len = {outputs} * {size};
#undef in
#undef out
    ''', s, **locals())

# def b_new_bytes(name):
#     c('unsigned char *{0} = 0;', name)
#     c('size_t {0}_len = 0;', name)

def b_new_bytes(name):
    c('unsigned char {0}[1000];', name)
    c('size_t {0}_len = 0;', name)

b_new_bytes_len = b_new_var

def b_bytes_len(vname, name):
    a('$type {0} = ({1}_len);', vname, name)

def b_invoke_hfun(res, fun, string):
    die('use invoke_hfun_with_size instead: apply B.compute_hfun_sizes filter')

def b_invoke_plain(res, fun, *nums):
    in_k = g.ifs[fun]['inputs']
    out_k = g.ifs[fun]['outputs']
    ins = nums[ : in_k]
    state = nums[in_k : ]
    # %% в идеале out_k должно совпадать с количеством state_var;
    #  % возможно, количество state_var надо в интерфейс вынести
    assert len(state) == out_k
    ins = ', '.join(ins)
    state = ', '.join(state)
    c(r'''
#define in {res}_in
#define out {res}
    $type in[{in_k}] = {{ {ins} }};
    $type out[{out_k}] = {{ {state} }};
    {fun}(in, out);
#undef in
#undef out
    ''', **locals())

def b_invoke_hfun_with_size(res, fun, string, res_size):
    c(r'''
    unsigned char {res}[{res_size}];
    size_t {res}_len = {res_size};
    {fun}({string}, {string}_len, {res});
    ''', **locals())

# def b_invoke_fun2(res, fun, string, string2):
#     c(r'''
#     // %% 1000 should be computed better; may pass from function
#     size_t {res}_len = 1000;
#     unsigned char {res}[{res}_len];
#     {fun}({string}, {string}_len, {string2}, {string2}_len, {res}, &{res}_len);
#     ''', **locals())

# def b_bytes_assign(left, right):
#     c('{0} = {1};', left, right)
#     c('{0}_len = {1}_len;', left, right)

def b_bytes_assign(left, right):
    c('memcpy({0}, {1}, {1}_len);', left, right)
    c('{0}_len = {1}_len;', left, right)

def b_bytes_append_zeros_up_to(res, string, upto):
    c(r'''
    unsigned char {res}[{upto}] = {{ 0 }};
    size_t {res}_len = {upto};
    memcpy({res}, {string}, {string}_len);
    ''', **locals())

def b_bytes_xor_each(res, string, byte):
    c(r'''
    unsigned char {res}[{string}_len];
    size_t {res}_len = {string}_len;
    {{
        size_t i;
        for (i = 0; i < {string}_len; i++) {{
            {res}[i] = ((unsigned char *){string})[i] ^ {byte};
        }}
    }}
    ''', **locals())

def generic_bytes_hex(res, string, use_upper):
    letters = 'ABCDEF' if use_upper else 'abcdef'
    c(r'''
    size_t {res}_len = {string}_len * 2;
    unsigned char {res}[{res}_len];
    {{
        size_t i;
        for (i = 0; i < {string}_len; i++) {{
            unsigned char c = ((unsigned char *){string})[i];
            {res}[2 * i] = "0123456789{letters}"[c >> 4];
            {res}[2 * i + 1] = "0123456789{letters}"[c & 0xf];
            //printf("%c %02x %c\n", {res}[2 * i], c, {res}[2 * i + 1]);
        }}
    }}
    ''', **locals())

b_bytes_hex = lambda res, string: generic_bytes_hex(res, string, False)
b_bytes_hex_upper = lambda res, string: generic_bytes_hex(res, string, True)

def b_bytes_concat(res, a, b):
    c(r'''
    size_t {res}_len = {a}_len + {b}_len;
    unsigned char {res}[{res}_len];
    memcpy({res}, {a}, {a}_len);
    memcpy({res} + {a}_len, {b}, {b}_len);
    ''', **locals())

def b_print_bytes(s):
    c('printf("pb %zd: %s\\n", {0}_len, {0});', s)

def b_print_hex(s):
    c(r'''
    {{
        size_t i;
        for (i = 0; i < {0}_len; i++) {{
            printf("%02x", ((unsigned char *){0})[i]);
        }}
        printf("\n");
    }}''', s)

def b_bytes_split_to_nums(res, string, count):
    c(r'''
    size_t {res}_len = {count} * $size;
    $type {res}[{count}];
    {{
        size_t i;
        for (i = 0; i < {count}; i++) {{
            {res}[i] = JOHNSWAP$bits((($type *){string})[i]);
        }}
    }}
    ''', **locals());

def b_bytes_join_nums(res, *nums):
    s = ''
    for i, v in enumerate(nums):
        s += '(($type *){0})[{1}] = JOHNSWAP$bits({2});\n'.format(res, i, v)
    c(r'''
    size_t {0}_len = {1} * $size;
    unsigned char {0}[{0}_len];
    {2}
    ''', res, len(nums), s)

def b_bytes_append_num(res, string, num):
    c(r'''
    size_t {res}_len = {string}_len + $size;
    unsigned char {res}[{res}_len];
    memcpy({res}, {string}, {string}_len);
    $type {res}_t = JOHNSWAP$bits({num});
    memcpy({res} + {string}_len, &{res}_t, $size);
    ''', **locals())

def b_bytes_xor(res, string, string2):
    # %% проверка, что длины совпадают?
    c(r'''
    unsigned char {res}[{string}_len];
    size_t {res}_len = {string}_len;
    {{
        size_t i;
        for (i = 0; i < {string}_len; i++) {{
            {res}[i] = ((unsigned char *){string})[i] ^ ((unsigned char *){string2})[i];
        }}
    }}
    ''', **locals())

def b_bytes_slice(res, string, f, t):
    c(r'''
    size_t {res}_len = {t} - {f};
    //printf(">> %zd\n", {res}_len);
    unsigned char {res}[{res}_len];
    memcpy({res}, ((unsigned char *){string}) + {f}, {res}_len);
    ''', **locals())

def b_bytes_zeros(res, length):
    c(r'''
    size_t {res}_len = {length};
    unsigned char {res}[{res}_len];
    memset({res}, 0, {res}_len);
    ''', **locals())

def b_new_bytes_const(res, hexed):
    length = len(hexed) / 2
    string = re.sub('(..)', r'\\x\1', hexed)
    c(r'''
    size_t {res}_len = {length};
    unsigned char {res}[{length}] = "{string}";
    ''', **locals())

def b_set_hfun_block_size(label):
    pass
def b_set_hfun_digest_size(label):
    pass
def b_assume_length(v, n, c):
    pass
