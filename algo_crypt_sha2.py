# crypt with sha2 scheme
# %% draft implementation
# %% sha512 only

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

# http://www.akkadia.org/drepper/SHA-crypt.txt

# Var.setup('be', args['size'])

sha = load_hfun('sha512')

# Algo

key = input_key()
salt = input_salt()
rounds = input_rounds()

key_length = bytes_length(key)
salt_length = bytes_length(salt)
# key_bit_length = get_bit_length(key)

ks = bytes_concat(key, salt)
ksk = bytes_concat(ks, key)
b = invoke_hfun(sha, ksk)

a = sha_init()
ksa = bytes_concat(ks, b)

# 11
# maximal password length is 125
# %% хорошо бы тут использовать другой тип
c = new_var()
c // key_length
bb = new_bytes()
bytes_assign(bb, ksa)
cycle_while_begin('step11')
cycle_while('step11', c > 0)

if_condition('c1', c & 1)
bytes_assign(bb, bytes_concat(bb, b))
if_else('c1')
bytes_assign(bb, bytes_concat(bb, key))
if_end('c1')

c // (c >> 1)
cycle_end('step11')

# 12
a = invoke_hfun(sha, bb)

# %% not inclusive
kkk = new_bytes()
unused = cycle_range('step14', 0, key_length - 1, 1)
bytes_assign(kkk, bytes_concat(kkk, key))
cycle_end('step14')
dp = invoke_hfun(sha, kkk)


# %%% я остановился тут

p = fill_string(key_length, dp_string, dp_string_length)
p_length = key_length

# 18
ds = sha_init()
# for i in range(16 + a[0]):
#     sha_update(ds, salt)
# %% big endian?
# %% not inclusive
c = cycle_range('setup_s', 0, new_const(16) + ((a[0] & (0xff << 56)) >> 56) - 1, 1)
sha_update(ds, salt, salt_length)
cycle_end('setup_s')
ds = sha_final(ds)

ds_string = digest_to_string(ds)
ds_string_length = 8 * 8

s = fill_string(salt_length, ds_string, ds_string_length)
s_length = salt_length

# 21

# # pseudo code
# for r in range(rounds - 1):
#     c = sha_init()
#     sha_update(c, p if r & 1 else ac)
#     if r % 3 != 0: sha_update(c, s)
#     if r % 7 != 0: sha_update(c, p)
#     sha_update(c, ac if r & 1 else p)
#     c = sha_final(c)
#     ac = c

# Notice that computation of some blocks maybe lifted from the loop

# Statistics of sequences for first 5k rounds:
# perl -e 'for (0 .. 5000) { if ($_ & 1) { print " ac," } else { print " p," } print " s," if $_ % 3; print " p," if $_ % 7; if ($_ & 1) { print " p" } else { print " ac" } print "\n" }' | sort | uniq -c
#     119  ac, p
#     714  ac, p, p
#     238  ac, s, p
#    1429  ac, s, p, p
#     120  p, ac
#     714  p, p, ac
#     238  p, s, ac
#    1429  p, s, p, ac
#   =5001, 1667 ps and psp may be brought upper

# The full cycle is 2 * 3 * 7 == 42 rounds, having such unroll it is
# possible to avoid most "if"s in the loop. There are 21 variants
# Without ac/p.
# %% Right?

# %% It'd be nice to do such optimization automatically...

# # %% add 0x80 and compute lengths
# # Only ac is variable. Other parts may be extracted:
# pp = string_concat(p, p)
# sp = string_concat(s, p)
# spp = string_concat(s, p, p)
# ps = string_concat(p, s)
# psp = string_concat(p, s, p)
# pp = string_to_ints(pp)
# sp = string_to_ints(sp)
# spp = string_to_ints(spp)
# ps = string_to_ints(ps)
# psp = string_to_ints(psp)

# %% It is possible to reduce memory footprint storing pp in spp, and
# sp in psp; also it is possible to store ps inside psp, but it may
# be needed to pass lengths then

# for r in range(rounds - 1):
#     c = sha_init()
#     if r & 1:
#         if r % 3 and r % 7:
#             sha_update(c, psp)
#         elif r % 7:
#             sha_update(c, pp)
#         elif r % 3:
#             sha_update(c, ps)
#         else:
#             sha_update(c, p)
#         sha_update(c, ac)
#     else:
#         sha_update(c, ac)
#         if r % 3 and r % 7:
#             sha_update(c, spp)
#         elif r % 7:
#             sha_update(c, pp)
#         elif r % 3:
#             sha_update(c, sp)
#         else:
#             sha_update(c, p)
#     c = sha_final(c)
#     ac = c

# r = cycle_range('main', 0, rounds, 1)
# # %% Compute 8?
# c_array = [Var() for i in range(8)]
# # ints_concat is "macro", free
# f = lambda x, y: sha_ints(ints_concat(x, y))
# c = iff(r & 1,
#         # %% lift computation of some blocks from the cycle
#         iff(r % 3 and r % 7, f(psp, c),
#             iff(r % 7, f(pp, c),
#                 iff(r % 3, f(ps, c),
#                     f(p, c)))),
#         iff(r % 3 and r % 7, f(c, spp),
#             iff(r % 7, f(c, pp),
#                 iff(r % 3, f(c, sp),
#                     f(c, p)))))
# for i, v in enumerate(c):
#     c_array[i] // c[i]
# cycle_end('main')

ac = a

# %% not inclusive
r = cycle_range('main', 0, rounds - 1, 1)
c = sha_init()
# print_var(r)
# print_digest(ac)
ac_string = digest_to_string(ac)
ac_string_length = 8 * 8
if_condition('r1', r & 1)
sha_update(c, p, p_length)
if_else('r1')
sha_update(c, ac_string, ac_string_length)
if_end('r1')
if_condition('r3', r % 3)
sha_update(c, s, s_length)
if_end('r3')
if_condition('r7', r % 7)
sha_update(c, p, p_length)
if_end('r7')
if_condition('r2', r & 1)
sha_update(c, ac_string, ac_string_length)
if_else('r2')
sha_update(c, p, p_length)
if_end('r2')
# мы затираем 'a'
# %% memory leak?
ac // sha_final(c)
cycle_end('main')

# %% avoid hardcoded value, how?
for i in range(8):
    output(ac[i])
