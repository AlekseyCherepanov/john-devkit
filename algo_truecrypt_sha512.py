# TrueCrypt with sha512 and AES XTS, abstract

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

Var.setup('be', 4)

s = input_salt()
key = input_key()

assume_length(s, 64, 64)

s2 = input_salt2()

sha512 = load_hfun('sha512')

aes_encrypt = load_fun2('aes_encrypt')
aes_decrypt = load_fun2('aes_decrypt')

k = pbkdf2_hmac(sha512, key, s, 1000, 1)

def aes_xts_decrypt_block(double_key, encrypted):
    key1 = bytes_slice(double_key, 0, 32)
    key2 = bytes_slice(double_key, 32, 64)
    tweak = bytes_zeros(16)
    tweak = invoke_fun2(aes_encrypt, key2, tweak)
    assume_length(tweak, 16, 16)
    assume_length(encrypted, 16, 16)
    buf = bytes_xor(encrypted, tweak)
    out = invoke_fun2(aes_decrypt, key1, buf)
    assume_length(out, 16, 16)
    out = bytes_xor(out, tweak)
    return out

d = aes_xts_decrypt_block(k, s2)

# %% надо возвращать только первые 4 символа
t = bytes_slice(d, 0, 4)
e = bytes_slice(d, 12, 16)
r = bytes_concat(t, e)
output_bytes(r)
