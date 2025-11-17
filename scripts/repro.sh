#!/bin/bash

# Stop all repro-related containers:
# docker ps -a --filter "name=repro-*" -q | xargs -r docker stop

set -euo pipefail

# Required args
SYZKALLER= # Path (in container) to the syzkaller
KERNEL=    # Path (in container) to the kernel
IMAGE=     # Path (in container) to the system image
LOGS=(
    # Path (in container) to log files
)
MOUNTS= # Mount flags

# Optional args
TASKS=4     # Number of parallel tasks
CPUSET=8-15 # CPU cores to use

# Function to generate repro config
gen_repro_config() {
    cat <<EOF
        {
            "target": "linux/amd64",
            "http": "127.0.0.1:56741",
            "workdir": "$WORKDIR",
            "kernel_obj": "$KERNEL",
            "image": "$IMAGE/bullseye.img",
            "sshkey": "$IMAGE/bullseye.id_rsa",
            "syzkaller": "$SYZKALLER",
            "procs": 8,
            "type": "qemu",
            "reproduce": false,
            "vm": {
                "count": 1,
                "kernel": "$KERNEL/arch/x86/boot/bzImage",
                "cpu": 2,
                "mem": 2048
            }
        }
EOF
}

# Reproduce bugs in parallel
for LOG in "${LOGS[@]}"; do

    repro_num=$(docker ps -a --filter "name=repro-*" -q | wc -l)
    while [ $repro_num -ge 4 ]; do
        sleep 1m
        repro_num=$(docker ps -a --filter "name=repro-*" -q | wc -l)
    done

    log_name=$(basename $LOG)
    log_dir=$(dirname $LOG)
    suffix=$(basename $log_dir)-$log_name

    WORKDIR=$(dirname $(dirname $log_dir))/repro/out-$suffix
    repro_cfg=$(gen_repro_config)
    echo $repro_cfg >/tmp/repro-$suffix.cfg
    docker run -d --rm \
        $MOUNTS \
        -v /tmp/repro-$suffix.cfg:/tmp/repro-$suffix.cfg \
        -v /etc/timezone:/etc/timezone:ro \
        -v /etc/localtime:/etc/localtime:ro \
        --name repro-$suffix \
        --network host \
        --cpuset-cpus=$CPUSET \
        --cpus=2 \
        --privileged \
        syzmeta:latest \
        bash -c "
            mkdir -p $WORKDIR && \
            cp /tmp/repro-$suffix.cfg $WORKDIR/repro.cfg && \
            $SYZKALLER/bin/syz-repro --config=$WORKDIR/repro.cfg --output=$WORKDIR/repro.syz --crepro=$WORKDIR/repro.c $LOG > $WORKDIR/repro.log 2>&1
        "

done
