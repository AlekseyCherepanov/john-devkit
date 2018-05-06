# -*- coding: utf-8 -*-

# Copyright © 2016 Aleksey Cherepanov <lyosha@openwall.com>
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.

from Crypto.Cipher import AES

# Encryption
key = 'This is a key123This is a key123'
msg = "A really secret!"
# msg = "B really secret!"

encryption_suite = AES.new(key, AES.MODE_ECB)
cipher_text = encryption_suite.encrypt(msg)

c_hex = cipher_text.encode('hex')

# Decryption
decryption_suite = AES.new(key, AES.MODE_ECB)
plain_text = decryption_suite.decrypt(cipher_text)

assert plain_text == msg

print '{{"{0}#{1}", "{2}"}},'.format(msg, c_hex, key)
