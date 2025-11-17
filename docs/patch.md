# Patch description

- release.patch: Only add support for metamorphic fuzzing
- debug.patch: Modify Makefile and targets.go for debugging.
- create-image.patch: build a disk image without `mount` and `umount`, which can be used in `docker build`
- offline.patch: add support for syzkaller or SyzMeta offline running (if they are built first time, they will donwload mockery from internet automatically).
- Patches under fuzzers:
  - mock.patch: Patch mock for normally running.
- Patches under kernel:
  - linux.v*.actor.patch: Patch for kernel to run ACTOR on different versions of linux kernels.
  - linux.v5.4.296.myfuzz.patch: Patch for kernel to run documents processing on linux v5.4.296.
- Patches under pseudo-syscalls:
  - linux.v*.patch: Encoded kernel MRs generated based on docs of linux (only high-quality).
  - variant.E-.linux.v*.patch: Encoded kernel MRs generated based on docs of linux v5.4.296 (Trial run disabled).
  - variant.R-.linux.v*.patch: Encoded kernel MRs generated based on docs of linux v5.4.296 (RAG disabled).
  - variant.RE-.linux.v*.patch: Encoded kernel MRs generated based on docs of linux v5.4.296 (Both RAG and trial run disabled).