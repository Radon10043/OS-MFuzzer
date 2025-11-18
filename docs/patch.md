# Patch Descriptions

This document provides an overview of the patches available in this repository.

- `release.patch`: Enables support for metamorphic fuzzing.
- `debug.patch`: Modifies `Makefile` and `targets.go` for debugging purposes.
- `create-image.patch`: Builds a disk image without `mount` and `umount`, allowing it to be used within a `docker build` process.
- `offline.patch`: Adds support for running OS-MFuzzer in an offline environment. If run for the first time, they will automatically download `mockery`.

### Fuzzer Patches

- `fuzzers/mock.patch`: A patch to ensure `mock` runs correctly.

### Kernel Patches

- `kernel/linux.v*.actor.patch`: Patches for running ACTOR on various Linux kernel versions.
- `kernel/linux.v5.4.296.myfuzz.patch`: A patch for processing documentation on Linux v5.4.296.

### Pseudo-Syscall Patches

- `pseudo-syscalls/linux.v*.patch`: High-quality encoded kernel MRs generated from Linux documentation.
- `pseudo-syscalls/variant.E-.linux.v*.patch`: Encoded kernel MRs from Linux documentation (trial run disabled).
- `pseudo-syscalls/variant.R-.linux.v*.patch`: Encoded kernel MRs from Linux documentation (RAG disabled).
- `pseudo-syscalls/variant.RE-.linux.v*.patch`: Encoded kernel MRs from Linux documentation (both RAG and trial run disabled).