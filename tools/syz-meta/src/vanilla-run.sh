KERNEL=/home/radon/Documents/kernel-fuzzing/linux-v6.2
IMAGE=/home/radon/Documents/kernel-fuzzing/Debian/bullseye.img
SSHKEY=/home/radon/Documents/kernel-fuzzing/Debian/bullseye.id_rsa

mkdir -p $PWD/../data/output/vanilla-out/csrc
mkdir -p $PWD/../data/output/vanilla-out/bin
mkdir -p $PWD/../data/output/vanilla-out/pc
mkdir -p $PWD/../data/output/vanilla-out/cov

cp $PWD/../data/fuzzing-out/linux-v6.2-1/out/corpus-c/prog* $PWD/../data/output/vanilla-out/csrc/

for f in $(ls $PWD/../data/output/vanilla-out/csrc); do
    clang -static -o $PWD/../data/output/vanilla-out/bin/$(basename $f .c) $PWD/../data/output/vanilla-out/csrc/$f
done

sudo nohup qemu-system-x86_64 \
	-m 2G \
	-smp 2 \
	-kernel $KERNEL/arch/x86/boot/bzImage \
	-append "console=ttyS0 root=/dev/sda earlyprintk=serial net.ifnames=0" \
	-drive file=$IMAGE,format=raw \
	-net user,host=10.0.2.10,hostfwd=tcp:127.0.0.1:10021-:22 \
	-net nic,model=e1000 \
	-enable-kvm \
	-nographic \
	-pidfile vm.pid \
	2>&1 | tee vm.log &
sleep 5s

for f in $(ls $PWD/../data/output/vanilla-out/bin); do
    sudo scp \
        -P 10021 \
        -F /dev/null \
        -o UserKnownHostsFile=/dev/null \
        -o IdentitiesOnly=yes \
        -o BatchMode=yes \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        -i $SSHKEY \
        $PWD/../data/output/vanilla-out/bin/$f localhost:~/$f
done

for f in $(ls $PWD/../data/output/vanilla-out/bin); do
    echo -e "Executing $f\n"
    timeout 5 ssh -p 10021 \
        -F /dev/null \
        -o UserKnownHostsFile=/dev/null \
        -o IdentitiesOnly=yes \
        -o BatchMode=yes \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        -i $SSHKEY \
        root@localhost \
        "/kcovtrace ~/$f 2>&1 | grep 0xff | sort | uniq" \
        > $PWD/../data/output/vanilla-out/pc/$f-pc
done

for f in $(ls $PWD/../data/output/vanilla-out/bin); do
    echo -e "Collecting cov of $f\n"
    cat $PWD/../data/output/vanilla-out/pc/$f-pc | llvm-addr2line -e $KERNEL/vmlinux | sort | uniq > $PWD/../data/output/vanilla-out/cov/$f-cov
done

touch $PWD/../data/output/vanilla-out/tmp
touch $PWD/../data/output/vanilla-out/globalCov
for f in $(ls $PWD/../data/output/vanilla-out/cov); do
    cat $PWD/../data/output/vanilla-out/cov/$f >> $PWD/../data/output/vanilla-out/tmp
done
cat $PWD/../data/output/vanilla-out/tmp | sort | uniq > $PWD/../data/output/vanilla-out/globalCov
rm $PWD/../data/output/vanilla-out/tmp

sudo pkill -f qemu