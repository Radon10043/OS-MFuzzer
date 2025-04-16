#!/bin/bash

set -e

mkdir ~/build && pushd ~/build

apt update
apt install -y sudo wget curl git vim make gcc g++ flex bison libffi-dev libncurses-dev libelf-dev libssl-dev bc debootstrap qemu-system-x86 xz-utils

# Download dependencies
wget -nc https://go.dev/dl/go1.23.6.linux-amd64.tar.gz
wget -nc https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tar.xz
curl -fsSL https://test.docker.com -o test-docker.sh
wget -nc https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-Linux-X64.tar.xz

# Install go-1.23.6
tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz
rm go1.23.6.linux-amd64.tar.gz

# Install Python-3.12.3
tar xvf Python-3.12.3.tar.xz
pushd Python-3.12.3
./configure --enable-optimizations
make -j
make install
popd
rm -rf Python-3.12.3 Python-3.12.3.tar.xz

# Install docker
chmod +x test-docker.sh
./test-docker.sh
sed -i "s/-Hn/-n/g" /etc/init.d/docker
service docker start
rm test-docker.sh

# Install LLVM-19.1.7
tar xvf LLVM-19.1.7-Linux-X64.tar.xz
rm LLVM-19.1.7-Linux-X64.tar.xz

# Pull syz-env docker image
docker pull gcr.io/syzkaller/env

# Update source variables
echo "export GOPATH=/usr/local/go/bin" >> ~/.bashrc
echo "export LLVM_HOME=~/build/LLVM-19.1.7-Linux-X64" >> ~/.bashrc
echo "export PATH=\$GOPATH:\$LLVM_HOME/bin:\$PATH" >> ~/.bashrc