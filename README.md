# john-devkit

john-devkit is an advanced code generator for John the Ripper. It aims to separate crypto primitives (sha-512, md5, crypt, pbdkf2 and so on), optimizations (interleave, loop unrolling, round unrolling, bitslice and so on) and output for different platforms (cpu, sse, gpu, fpga).

john-devkit uses its own domain specific language (dsl) on top of Python to describe crypto algorithms in an abstract way. Also there is a kind of instruction language for intermediate representation (referenced as "bytecode"). So there are two levels of code generation: dsl -> bytecode -> platform's language (for instance C for cpu).

## State

The current implementation is a Proof of Concept (unusable).

The current main priority is to support GPUs including on-gpu mask-mode.

john-devkit has now:
  * sha-512
  * sha-256
  * trivial merging of separately described algorithms
  * bitslice
  * output to standalone program
  * output to scalar code

Nearest plans:
  * output formats for john on gpu
  * incorporate on-gpu mask-mode
  * try kernel splitting
  * loop unrolling (full and partial)

There is no documentation for dsl and bytecode. It is not obvious how many times everything will be changed drastically.

## Usage

Current usage is very limited. Example of test for current sha-512 (using bitslice):

`$ CAND=MAXLENGTHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA time bash -c 'python format_standalone_sha256.py "$1" "$2" > t.c && echo "hi there $?" && gcc -Wfatal-errors t.c && ./a.out "$CAND" && printf '%s' "$CAND" | sha256sum | perl -pe "s/.{8}/$& /g"' -- '' b`

## Other approaches

While john-devkit may be viewed as a compiler, code generation is not the only way to achieve modularity without penalty on speed.

Incomplete list of approaches/implementations, just to name a few:

John the Ripper already has dynamic formats: separate crypto primitives could be combined at runtime without speed penalties due to work on optimal packs of candidates (attacker's position implies parallelism).

John the Ripper's bitslice implementation of descrypt supports easy configuration of output instructions through sets of macros. Even more, it may produce interleaved code including mix of vector and scalar instructions.

Billy Bob Brumley demonstrated application of simulated annealing algorithm to scheduling of des s-box instructions. It was considered possible to achieve 10% speed up over gcc modifying scheduling for specific cpu (though gcc is improved fast so the gap should be smaller).

NetBSD uses X-Macro technique: for example to make sha512-crypt and sha256-crypt from sha-512, sha-256 and crypt definitions.

[liborc](http://code.entropywave.com/orc/):
"Orc is a just-in-time compiler implemented as a library and set of associated tools for compiling and executing simple programs that operate on arrays of data.  Orc is unlike other general-purpose JIT engines: the Orc bytecode and language is designed so that it can be readily converted into SIMD instructions.  This translates to interesting language features and limitations: Orc has built-in capability for SIMD-friendly operations such as shuffling, saturated addition and subtraction, but only works on arrays of data."

GCC now has support for [OpenACC](http://www.openacc.org/) (via -fopenacc). So code can be easily converted into accelerated.

OpenCL and CUDA provide specialized languages for parallel computing.

These approaches have limitations. They are too low level, too implicit/smart, too inflexible, does not support multiple targets and/or neglect opportunity to get speed increasing compilation time. Also bitslice usually is not supported while it is an important optimization technique for some crypto algorithms. Nevertheless john's dynamic formats are a tough competitor on cpu (john-devkit will not replace it anyway due to runtime capabilities of dynamic formats, though it would be possible to generate primitives for dynamics if john-devkit outperformed current implementation).

