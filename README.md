# john-devkit

john-devkit is an advanced code generator for [John the Ripper](https://github.com/magnumripper/JohnTheRipper). It aims to separate crypto primitives (sha-512, md5, crypt, pbdkf2 and so on), optimizations (interleave, loop unrolling, round reversing, bitslice and so on) and output for different computing devices (cpu, sse, gpu, fpga).

john-devkit uses its own domain specific language (dsl) on top of Python to describe crypto algorithms in an abstract way. Also there is a kind of instruction language for intermediate representation (referenced as "bytecode"). So there are two levels of code generation: dsl -> bytecode -> platform's language (for instance C for cpu).

"bytecode" is a wrong word for the intermediate language/representation and will be fixed soon.

## Current State

The current implementation is a Proof of Concept.

There is no documentation for dsl and bytecode. It is not obvious how many times everything will be changed drastically.

There is a draft of hash parsing library by Alexander Cherepanov. It is not finished (and works by pure luck). It is included into john-devkit but it will be removed when the library become a persistent part of John the Ripper.

7 "raw" formats were implemented: raw-sha256, raw-sha224, raw-sha512, raw-sha384, raw-md4, raw-md5, raw-sha1. SHA-2 family got speed up (~20% for SHA-256, ~5% for SHA-512). md5, md4 and sha1 got noticable slowdown (it needs investigation). (Such speed up for raw-sha256 may be caused by changes in test vector. Accurate benchmarks are needed.)

raw-sha256 lost cisco hashes (base64 encoded) so benchmarks differ from John the Ripper not only due to optimizations.

The current main priority is to try more complex formats like sha256crypt.

john-devkit has now:
  * formats: raw-sha256, raw-sha224, raw-sha512, raw-sha384, raw-md4, raw-md5, raw-sha1
  * optimizations: vectorization (sse only), early reject, interleave, loop unrolling, additional batching in crypt_all() method

broken:
  * reverse (there is only initial implementation, it has problems with vectorization)
  * bitslice (there is no support in template file; no long vectors, only regular ints for vectors)
  * output to standalone program (it will not be fixed soon)

Nearest plans:
  * output to avx and avx2 for better benchmarking
  * fix bitslice and play with it
  * investigate md5/md4 slowdown (on sse)
  * fix reverse
  * sha2crypt scheme
  * output formats for john on gpu
  * incorporate on-gpu mask-mode
  * try kernel splitting

## Usage

To run john-devkit, you need
  * john-devkit in `john-devkit-dirty/` directory
  * working folder `john-devkit-temp/` as sibling to `john-devkit-dirty/`
  * John the Ripper in `john-devkit-temp/JohnTheRipper/`
  * run john's `./configure` (and `make` optionally)
  * `parsing_plug.c` and `parsing.h` in `john-devkit-temp/JohnTheRipper/src/` (symlinks or real files)

Then the following will work:

`...john-devkit-temp$ sh ../john-devkit-dirty/run_format_raw.sh sha256`

After the first run (for each format), you need to cd into JohnTheRipper/src/ , rerun ./configure script (otherwise you'll get "Unknown ciphertext format name requested") and rerun the command.

## License

Each file in john-devkit has its license written in a comment close to the beginning of the file. Usually it is the following cut-down BSD license:
`Redistribution and use in source and binary forms, with or without modification, are permitted.`

Some (template) files are derived from files of John the Ripper. They are subject for original license of John the Ripper. See `LICENSE.jtr` in john-devkit or `doc/LICENSE` in John the Ripper.

## Other approaches

While john-devkit may be viewed as a compiler, code generation is not the only way to achieve modularity without penalty on speed and john-devkit is not the only way to perform code generation.

Incomplete list of approaches/implementations, just to name a few:

John the Ripper already has dynamic formats: separate crypto primitives could be combined at runtime without speed penalties due to work on optimal packs of candidates (attacker's position implies parallelism).

John the Ripper's bitslice implementation of descrypt supports easy configuration of output instructions through sets of macros. Even more, it may produce interleaved code including mix of vector and scalar instructions.

Billy Bob Brumley demonstrated application of simulated annealing algorithm to scheduling of des s-box instructions. It was considered possible to achieve 10% speed up over gcc modifying scheduling for specific cpu (though gcc is improved fast so the gap should be smaller).

Roman Rusakov [researched and developed](http://www.openwall.info/wiki/sbox-opt/des) the way to generate current formulas for des s-boxes used in John the Ripper (and some others hash crackers). Formulas were sorted by length and then by latency on different processors (so different formulas are used depending on platform). The problem of getting formulas is like in VLSI but optimization criteria is a bit different because levels of circuit does directly affect performance as of we are limited by number of registers while use of memory is slow.

NetBSD's libcrypt uses X-Macro technique to make [hmac-sha1](https://github.com/rumpkernel/netbsd-userspace-src/blob/3280867f12bbd346f39d5a4efb41fcf9b087bf33/lib/libcrypt/hmac_sha1.c) from hmac template and SHA-1 primitives.

[liborc](http://code.entropywave.com/orc/):
"Orc is a just-in-time compiler implemented as a library and set of associated tools for compiling and executing simple programs that operate on arrays of data.  Orc is unlike other general-purpose JIT engines: the Orc bytecode and language is designed so that it can be readily converted into SIMD instructions.  This translates to interesting language features and limitations: Orc has built-in capability for SIMD-friendly operations such as shuffling, saturated addition and subtraction, but only works on arrays of data."

GCC now has support for [OpenACC](http://www.openacc.org/) (via -fopenacc). So code can be easily converted into accelerated.

OpenCL and CUDA provide specialized languages for parallel computing.

These approaches have limitations. They are too low level, too implicit/smart, too inflexible, does not support multiple targets, know nothing about John the Ripper and/or neglect opportunity to get speed increasing compilation time. Also bitslice usually is not supported while it is an important optimization technique for some crypto algorithms. Nevertheless john's dynamic formats are a tough competitor on cpu (john-devkit will not replace it anyway due to runtime capabilities of dynamic formats, though it would be possible to generate primitives for dynamics if john-devkit outperformed current implementation).

