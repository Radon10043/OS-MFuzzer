#!/usr/bin/bash
# Note: you should run this script as root

SyzMetaBin=/path/to/SyzMeta/bin/syz-meta
ConfigFile=/path/to/SyzMeta/workdir/syz-meta/SyzMeta.cfg.json
NConfigFile=/path/to/SyzMeta/workdir/syz-meta/SyzMetaXXXXXX.cfg.json
for ((i=10; i<=10; i++)); do
    echo "Loop $i"
    path=$(cat $ConfigFile | jq '.out')
    npath=${path:1:-1}-$i
    cat $ConfigFile | jq ".out=\"$npath\"" > $NConfigFile
    $SyzMetaBin -config $NConfigFile
    if [ $? -ne 0 ]; then
        pkill -f qemu
    fi
done