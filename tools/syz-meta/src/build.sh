#!/bin/bash

set -e

mkdir ~/build && pushd ~/build

apt update
apt install -y sudo wget curl git vim make gcc g++ flex bison libffi-dev libncurses-dev libelf-dev libssl-dev bc debootstrap qemu-system-x86 xz-utils

# Install golang-1.23.6
wget -nc https://go.dev/dl/go1.23.6.linux-amd64.tar.gz
tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz
rm go1.23.6.linux-amd64.tar.gz

# Install Python-3.12.3
wget -nc https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tar.xz
tar xvf Python-3.12.3.tar.xz
pushd Python-3.12.3
./configure --enable-optimizations
make -j
make install
popd
rm -rf Python-3.12.3 Python-3.12.3.tar.xz

# Install docker
curl -fsSL https://test.docker.com -o test-docker.sh
chmod +x test-docker.sh
./test-docker.sh
sed -i "s/-Hn/-n/g" /etc/init.d/docker
service docker start
rm test-docker.sh

# Pull syz-env docker image
docker pull gcr.io/syzkaller/env

# Update source variables
echo "export GOPATH=/usr/local/go/bin" >> ~/.bashrc
echo "export PATH=\$PATH:\$GOPATH" >> ~/.bashrc