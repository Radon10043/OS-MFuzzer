This file used to tell you how to install dependencies.

Dependencies:
- Python 3.12.3

Command for installing Python-3.12.3:
> [!Warning]
> It is recommended that do not to put python-3.12.3 in the project directory.
```sh
# Prepare the install environment
sudo apt update
sudo apt install build-essential libffi-dev

# Build the Python-3.12.3
cd /path/to/tools # e.g. ~/tools
wget https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tar.xz
tar -xvf Python-3.12.3.tar.xz && rm Python-3.12.3.tar.xz
pushd Python-3.12.3
./configure --disable-shared --enable-optimizations --prefix=$PWD
make && make install # If you wanna restore the Python-3.12.3 folder to the clean status, use "make distclean"
popd

# Create & activate the virual environment
cd /path/to/kernel-driver-MR-identify
/path/to/Python-3.12.3/bin/python3 -m venv .venv
. .venv/bin/activate
```