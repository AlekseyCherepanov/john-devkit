# library, always included into algo_*

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

def hmac(hash_fun, key, message):

    block_size = hfun_block_size(hash_fun)
    digest_size = hfun_digest_size(hash_fun)

    key2 = new_bytes()
    key2_len = new_bytes_len()

    key_len = bytes_len(key)
    message_len = bytes_len(message)

    # if_begin('shortening')
    if_condition('shortening', key_len > block_size)
    bytes_assign(key2, invoke_hfun(hash_fun, key))
    if_else('shortening')
    bytes_assign(key2, key)
    if_end('shortening')

    key3 = bytes_append_zeros_up_to(key2, block_size)

    assume_length(key3, block_size, block_size)

    o_key_pad = bytes_xor_each(key3, 0x5c)
    i_key_pad = bytes_xor_each(key3, 0x36)

    inner = invoke_hfun(hash_fun, bytes_concat(i_key_pad, message))
    outer = invoke_hfun(hash_fun, bytes_concat(o_key_pad, inner))
    return outer

def pbkdf2_hmac(hash_fun, key, salt, rounds, dk_len_num):
    Var.setup('be', 4)

    prf = lambda p, s: hmac(hash_fun, p, s)

    def f(p, s, c, i):
        # print_bytes(p)
        # print_bytes(s)
        # print_var(c)
        # print_var(i)
        # print_hex(bytes_append_num(s, i))
        u1 = prf(p, bytes_append_num(s, i))
        # print_hex(u1)
        uj = new_bytes()
        bytes_assign(uj, u1)
        r = new_bytes()
        bytes_assign(r, u1)
        j = cycle_range('rounds', 2, c, 1)
        # print_var(j)
        a = prf(p, uj)
        b = bytes_xor(r, a)
        bytes_assign(uj, a)
        bytes_assign(r, b)
        cycle_end('rounds')
        return r

    # o = new_bytes()

    # ** hfun_digest_size(hash_fun) -- у hmac такая же длина
    # j = cycle_const_range('dk_len', 1, new_const(dk_len) / hfun_digest_size(hash_fun), 1)

    # j = cycle_const_range('dk_len', 1, dk_len_num, 1)
    # bytes_assign(o, bytes_concat(o, f(key, salt, rounds, j)))
    # cycle_end('dk_len')

    o = f(key, salt, rounds, 1)

    # print_hex(o)
    # debug_exit('quit')

    return o

def constify_arrays(*arrs):
    for a in arrs:
        for i in xrange(len(a)):
            a[i] = new_const(a[i])
