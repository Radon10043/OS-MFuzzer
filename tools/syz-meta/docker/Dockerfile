FROM ubuntu:22.04

WORKDIR /home
SHELL [ "/bin/bash", "-c" ]

# Copy linux kernel build scripts to the container
COPY linux /home/linux
RUN chmod +x linux/*.sh

# Download following files to the tools/syz-meta/docker and build the image by COPY command will save time:
# go1.23.6.linux-amd64.tar.gz, Python-3.12.3.tar.xz, LLVM-19.1.7-Linux-X64.tar.xz
COPY go1.23.6.linux-amd64.tar.gz Python-3.12.3.tar.xz LLVM-19.1.7-Linux-X64.tar.xz /home/
RUN apt update && \
    apt install -y sudo wget curl git vim openssh-server make gcc flex bison libncurses-dev libelf-dev libssl-dev bc debootstrap qemu-system-x86 && \
    # Update listening port of openssh & Update PermitRootLogin to yes
    sed -i "s/#Port 22/Port 50000/g" /etc/ssh/sshd_config && \
    sed -i "s/#PermitRootLogin prohibit-password/PermitRootLogin yes/g" /etc/ssh/sshd_config && \
    # Download syzkaller
    git clone https://github.com/google/syzkaller && \
    pushd syzkaller && \
    git checkout 4b25d55 && \
    popd && \
    # Create image folder
    mkdir Debian && \
    pushd Debian && \
    cp /home/syzkaller/tools/create-image.sh . && \
    chmod +x ./create-image.sh && \
    popd && \
    # Install docker
    curl -fsSL https://test.docker.com -o test-docker.sh && \
    chmod +x test-docker.sh && \
    ./test-docker.sh && \
    sed -i "s/-Hn/-n/g" /etc/init.d/docker && \
    rm test-docker.sh && \
    # Install golang-1.23.6
    wget -nc https://go.dev/dl/go1.23.6.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz && \
    rm go1.23.6.linux-amd64.tar.gz && \
    # Install Python-3.12.3
    wget -nc https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tar.xz && \
    tar xvf Python-3.12.3.tar.xz && \
    pushd Python-3.12.3 && \
    ./configure --enable-optimizations && \
    make -j && \
    make install && \
    popd && \
    rm -rf Python-3.12.3 Python-3.12.3.tar.xz && \
    # Install LLVM-19.1.7
    wget -nc https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-Linux-X64.tar.xz && \
    tar xvf LLVM-19.1.7-Linux-X64.tar.xz && \
    rm LLVM-19.1.7-Linux-X64.tar.xz

ENV LLVM_HOME=/home/LLVM-19.1.7-Linux-X64
ENV GOPATH=/usr/local/go/bin
ENV PATH=$PATH:$GOPATH:$LLVM_HOME/bin

# Please note:
# If you want to use docker in the container, you need run "docker run --privileged ..." to create the container.
# If host has proxy, you can run "docker run --network host" to make container use host's proxy.
# You need set password if you want to use ssh to connect the container. Run passwd in the container.
# After the images build success, you need run the folloing commands in the container:
# docker pull gcr.io/syzkaller/env
# pushd /home/Debian && ./create-images.sh && popd
# pushd /home/linux && make v6.2 && popd