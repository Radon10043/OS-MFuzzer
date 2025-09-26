#!/bin/bash
ssh -p 2324 \
    -F /dev/null \
    -o UserKnownHostsFile=/dev/null \
    -o IdentitiesOnly=yes \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -i $SSHKEY \
    root@localhost "cd /tmp && ./syz-execprog -enable=all -repeat=0 -procs=8 ./repro.syz"