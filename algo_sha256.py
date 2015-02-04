# SHA256 abstract
# http://en.wikipedia.org/wiki/SHA256

Var.setup('be', 4)

# Getting in
w = [None for i in range(0, 64)]
for i in range(0, 16):
    w[i] = input()

# State, Getting in too
H_default = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
H = [state(v) for v in H_default]

k = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]
k = [Const(v) for v in k]
# for jt, vt in enumerate(k):
#     debug_print_var(vt, 'k[{0}]'.format(jt))
k = MyArray('k', k)
# %% use my_const_array

# comment('before extension of w')

# %% hint that for optimization too
for i in range(16, 64):
    s0 = ror(w[i - 15], 7) ^ ror(w[i - 15], 18) ^ (w[i - 15] >> 3)
    s1 = ror(w[i - 2], 17) ^ ror(w[i - 2], 19) ^ (w[i - 2] >> 10)
    w[i] = w[i - 16] + s0 + w[i - 7] + s1

# for v in w:
#     comment("v in w: " + str(v))

# # do that not on MyArray
# for jt, vt in enumerate(w):
#     debug_print_var(vt, 'w[{0}]'.format(jt))

w = MyArray('w', w)

# comment('after extension of w')
# comment('before main loop')

a, b, c, d, e, f, g, h = [Var() for i in range(8)]
a // H[0];
b // H[1];
c // H[2];
d // H[3];
e // H[4];
f // H[5];
g // H[6];
h // H[7];
# comment('varsbefore ' + "X" + ' ' + ' '.join(str(v) for v in (a, b, c, d, e, f, g, h)))

# Main loop
i = cycle_const_range('main', 0, 63, 1)

# debug_print_var(a, "a")
# debug_print_var(b, "b")
# debug_print_var(c, "c")
# debug_print_var(d, "d")
# debug_print_var(e, "e")
# debug_print_var(f, "f")
# debug_print_var(g, "g")
# debug_print_var(h, "h")

s0 = ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)
maj = (a & b) ^ (a & c) ^ (b & c)
t2 = s0 + maj
s1 = ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)
ch = (e & f) ^ (~e & g)
t1 = h + s1 + ch + k[i] + w[i]

h // g
g // f
f // e
e // (d + t1)
d // c
c // b
b // a
a // (t1 + t2)
# comment('vars ' + "X" + ' ' + ' '.join(str(v) for v in (a, b, c, d, e, f, g, h)))

# End of main loop
cycle_end('main')

# a, b, c, d, e, f, g, h = H
# for i in range(64):
#     s0 = ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)
#     maj = (a & b) ^ (a & c) ^ (b & c)
#     t2 = s0 + maj
#     s1 = ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)
#     ch = (e & f) ^ (~e & g)
#     t1 = h + s1 + ch + k[i] + w[i]
#     h = g
#     g = f
#     f = e
#     e = (d + t1)
#     d = c
#     c = b
#     b = a
#     a = (t1 + t2)

# comment('after main loop')

# Updating state
H[0] += a
H[1] += b
H[2] += c
H[3] += d
H[4] += e
H[5] += f
H[6] += g
H[7] += h

# Getting out
for v in H:
    output(v)
