{"$crc32$00000000.fa455f6b", "ripper"},
{"$crc32$00000000.4ff4f23f", "dummy"},
//	{"$crc32$00000000.00000000", ""},         // this one ends up skewing the benchmark time, WAY too much.
{"$crc32$4ff4f23f.ce6eb863", "password"}, // this would be for file with contents:   'dummy'  and we want to find a password to append that is 'password'
{"$crc32$fa455f6b.c59b2aeb", "123456"},   // ripper123456
