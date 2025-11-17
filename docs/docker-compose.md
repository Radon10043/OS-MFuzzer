# docker-compose

This document details services in docker-compose files. We use `docker-compose/compose.linux-v6.12.40.yaml` as example.

|  Service   |                              Description                              |
| :--------: | :-------------------------------------------------------------------: |
|    iden    |                          Kernel MR synthesis                          |
|    impl    |                          Kernel MR encoding                           |
|    eval    |              Trial run kernel MRs for qulaity evaluation              |
|   myfuzz   |                  Fuzzing linux kernel via OS-MFuzzer                  |
| syzkaller  |                  Fuzzing linux kernel via syzkaller                   |
| moonshine  |                  Fuzzing linux kernel via moonshine                   |
|   healer   |                    Fuzzing linux kernel via healer                    |
|    mock    |                     Fuzzing linux kernel via mock                     |
|   actor    |                    Fuzzing linux kernel via actor                     |
| myfuzz-E-  |        Fuzzing linux kernel via myfuzz-E- (Trial run disabled)        |
| myfuzz-R-  |           Fuzzing linux kernel via myfuzz-R- (RAG disabled)           |
| myfuzz-RE- | Fuzzing linux kernel via myfuzz-RE- (Both RAG and trial run disbaled) |

You can also fuzzing linux kenrel in parallel, for exmaple:

Command:
```bash
docker compose -f docker-compose/compose.linux-v6.12.40.yaml up myfuzz --scale myfuzz=5 -d
```