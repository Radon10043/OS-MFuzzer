# Docker Compose Services

This document details the services defined in the Docker Compose files. We use `docker-compose/compose.linux-v6.12.40.yaml` as an example.

| Service      | Description                                                   |
| :----------- | :------------------------------------------------------------ |
| `iden`       | Kernel MR Synthesis                                           |
| `impl`       | Kernel MR Encoding                                            |
| `eval`       | Trial run of Kernel MRs for quality evaluation                |
| `myfuzz`     | Fuzzing the Linux kernel with OS-MFuzzer                      |
| `syzkaller`  | Fuzzing the Linux kernel with Syzkaller                       |
| `moonshine`  | Fuzzing the Linux kernel with MoonShine                       |
| `healer`     | Fuzzing the Linux kernel with HEALER                          |
| `mock`       | Fuzzing the Linux kernel with MOCK                            |
| `actor`      | Fuzzing the Linux kernel with ACTOR                           |
| `myfuzz-E-`  | Fuzzing with OS-MFuzzer (Trial Run disabled)                  |
| `myfuzz-R-`  | Fuzzing with OS-MFuzzer (RAG disabled)                        |
| `myfuzz-RE-` | Fuzzing with OS-MFuzzer (Both RAG and Trial Run disabled)     |

You can also run fuzzing tasks in parallel. For example:

Command:
```bash
docker compose -f docker-compose/compose.linux-v6.12.40.yaml up myfuzz --scale myfuzz=5 -d
```