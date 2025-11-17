# OS-MFuzzer

OS-MFuzzer is an issue-driven, LLM-enabled metamorphic fuzzing framework for operating system kernels, built upon [syzkaller](https://github.com/google/syzkaller).

This document details the setup process for OS-MFuzzer and provides instructions for its use in metamorphic fuzzing.

## Prerequisites

We recommend using Docker for a streamlined setup.

First, build the Docker image for OS-MFuzzer:
```bash
mkdir volume && cd volume
mkdir docker
git clone --recurse-submodules https://github.com/XXX/XXX OS-MFuzzer
wget -P volume/OS-MFuzzer/docker https://go.dev/dl/go1.23.6.linux-amd64.tar.gz
wget -P volume/OS-MFuzzer/docker https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-Linux-X64.tar.xz
wget -P volume/OS-MFuzzer/docker https://github.com/google/flatbuffers/archive/refs/tags/v2.0.8.tar.gz
docker build -t os-mfuzzer:latest -f volume/OS-MFuzzer/docker/Dockerfile.myfuzz volume/OS-MFuzzer/docker
```

Next, start a container with a mounted volume to ensure data persistence.

Command:
```bash
docker run -d -v ./volume:/vol --cpus 16 --privileged --name os-mfuzzer-container os-mfuzzer:latest tail -f /dev/null
docker exec -it os-mfuzzer-container bash
```

Inside the container, let's begin by building the Linux kernel. We will use v6.12.40 as an example.

Command:
```bash
cd /vol
mkdir linux && cd linux
git clone https://github.com/gregkh/linux stable
cp -r stable v6.12.40
git -C v6.12.40 checkout v6.12.40
```

Now, build the Linux kernel using syzbot's configuration. You can find the necessary config files in the OS-MFuzzer repository.

Command:
```bash
cd v6.12.40
cp $OSMFuzzer/configs/kernel/linux.v6.12.40.config .config
make CC=clang olddefconfig
make CC=clang -j16
```

We also need to create an image to run the kernel.

Command:
```bash
cd /vol
mkdir -p images/Debian
cd images/Debian
cp $OSMFUZZER/scripts/create-image.sh .
./create-image.sh
```

## Run (Simplified)

To begin metamorphic fuzzing, we need to build OS-MFuzzer and integrate the generated Encoded Kernel Metamorphic Relations (EKMRs). You can integrate them using the patches we provide. The following command integrates EKMRs that were generated from the Linux v6.12.40 documentation. For additional patches, please refer to our [Patch Documentation](/docs/patch.md).

Command:
```bash
cd $OSMFUZZER
make restore patch PATCH=patch/pseudo-syscall/linux.v6.12.40.patch
make -C syzkaller clean generate all -j16
```

With the EKMRs for Linux v6.12.40 now integrated into OS-MFuzzer/syzkaller, you can run it just like a standard syzkaller instance.

```bash
mkdir workdir
export WORKDIR=/vol/OS-MFuzzer/workdir
export KERNEL=/vol/linux/v6.12.40
export IMAGE=/vol/images/Debian
export SYZKALLER=/vol/OS-MFuzzer/syzkaller
export VMCOUNT=4
cat configs/fuzz/linux.cfg | envsubst > workdir/test.cfg
$OSMFUZZER/syzkaller/bin/syz-manager -config=workdir/test.cfg
```

For instructions on installing baseline fuzzers, please see the [Fuzzer Documentation](/docs/fuzzers/README.md).

## Advanced Usage

This section provides a comprehensive guide to synthesizing, encoding, integrating, and metamorphic fuzzing with Kernel Metamorphic Relations (KMRs) using OS-MFuzzer.

### Kernel MR Synthesis

#### External Corpus Construction

Extract all CVE announcements from the linux-cve-announcement and create a ChromaDB database.

```bash
git clone --mirror https://lore.kernel.org/linux-cve-announce/0 linux-cve-announce/git/0.git
python3 src/corpus.py get_kernel_cves --git_obj linux-cve-announce/git/0.git --outdir workdir/external-corpus
python3 src/corpus.py create_chroma_db --input workdir/external-corpus
```

#### Kernel Documentation Processing

Split the kernel documentation into smaller, more manageable chunks for a targeted analysis. For example, to process `Documentation/virt/kvm/api.rst`:

Command:
```bash
python3 src/rst_analyzer.py \
        --file /vol/linux/v6.12.40/Documentation/virt/kvm/api.rst \
        --outdir workdir/kernel-docs/v6.12.40/kvm/api
```
This will create a directory for each document chunk, containing a `content.txt` file with the section's content.

#### Batch Synthesize Kernel MRs

You can run `src/experiment.py` to synthesize Kernel MRs in batches. The script will traverse all `content.txt` files to generate the MRs.

Command:
```bash
python3 $OSMFUZZER/src/experiment.py \
            iden \
            --specdir $OSMFUZZER/workdir/kernel-docs \
            --corpus $OSMFUZZER/workdir/external-corpus
```

#### Synthesize Kernel MRs Individually

Create a JSON configuration file (e.g., `MRSynt.cfg.json`) with the following content:

```json
{
    "identifier": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "YOUR_API_KEY",
        "framework": "openai",
        "model": "gemini-2.5-pro",
        "temperature": 0.5,
        "stream": true,
        "prompts": {
            "system": "/vol/OS-MFuzzer/data/prompts/identifier/system.md",
            "user": [
                "/vol/OS-MFuzzer/data/prompts/identifier/init.md",
                "/vol/OS-MFuzzer/data/prompts/identifier/follow.md"
            ]
        }
    },
    "calibrator": {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "api_key": "YOUR_API_KEY",
        "framework": "openai",
        "model": "o3",
        "temperature": 0.2,
        "stream": true,
        "prompts": {
            "system": "/vol/OS-MFuzzer/data/prompts/calibrator/system.md",
            "user": [
                "/vol/OS-MFuzzer/data/prompts/calibrator/vanilla.md"
            ]
        }
    },
    "max_iter": 10,
    "output": "/vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/1.-General-description/iden",
    "specification": "/vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/1.-General-description/content.txt",
    "driver_name": "kvm"
}
```

The `MRIden.py` script uses LLMs to identify and calibrate MRs. The parameters are explained below:

- `identifier`: Stores settings for the identifier model.
  - `base_url`: The base URL for accessing the model API.
  - `api_key`: Your API key for the service.
  - `framework`: The API framework to use (e.g., `openai`).
  - `model`: The specific model to query.
  - `temperature`: Controls the randomness of the output. Lower values result in more deterministic responses.
  - `stream`: Enables or disables streaming responses from the LLM.
  - `prompts`: Specifies the paths to system and user prompts. Multiple user prompts can be provided.
- `calibrator`: Stores settings for the calibrator model, with a structure identical to `identifier`.
- `max_iter`: The maximum number of iterations for the discussion phase.
- `output`: The directory where query messages and results will be stored.
- `specification`: The path to the specification file used for the LLM query.
- `driver_name`: The name of the corresponding driver or subsystem.

### Encode Kernel MRs

First, clone the appropriate version of Syzkaller.

Command:
```bash
cd /vol
git clone https://github.com/google/syzkaller
git -C syzkaller checkout 4b25d554
cd $OSMFUZZER
```

#### Batch Encoding

Use `src/experiment.py` to encode Kernel MRs in batches. The script will traverse each `iden` directory and create a corresponding `impl` directory.

Command:
```bash
python3 $OSMFUZZER/src/experiment.py \
            impl \
            --idendir $OSMFUZZER/workdir/kernel-docs \
            --syzkaller /vol/syzkaller
```

#### Individual Encoding

Create a JSON configuration file (e.g., `MREncode.json`) with the following content:

```json
{
    "c_programmer": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "YOUR_API_KEY",
        "framework": "openai",
        "model": "gemini-2.5-pro",
        "temperature": 0.5,
        "stream": true,
        "prompts": {
            "system": "/vol/OS-MFuzzer/data/prompts/c-programmer/system.md",
            "user": [
                "/vol/OS-MFuzzer/data/prompts/c-programmer/init.md",
                "/vol/OS-MFuzzer/data/prompts/c-programmer/follow.md"
            ]
        }
    },
    "syzlang_programmer": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "YOUR_API_KEY",
        "framework": "openai",
        "model": "gemini-2.5-pro",
        "temperature": 0.5,
        "stream": true,
        "prompts": {
            "system": "/vol/OS-MFuzzer/data/prompts/syzlang-programmer/system.md",
            "user": [
                "/vol/OS-MFuzzer/data/prompts/syzlang-programmer/init.md",
                "/vol/OS-MFuzzer/data/prompts/syzlang-programmer/follow.md"
            ]
        }
    },
    "mr_desc": "/vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/1.-General-description/iden/mr_final.md",
    "max_iter": 10,
    "output": "/vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/1.-General-description/impl",
    "compiler": "gcc",
    "syzkaller": "/vol/syzkaller"
}
```

The `MRImpl.py` script generates C code and the corresponding Syzlang description for an MR. Key parameters include:

- `mr_desc`: Path to the Markdown file containing the MR description.
- `compiler`: The compiler used to validate the generated C code (e.g., `gcc`).
- `syzkaller`: The path to the Syzkaller repository, used to verify the integration of the generated MR.

### Trial Run Encoded Kernel MRs

Use `src/experiment.py` for batch trial runs or `src/MREval.py` for individual trials.

Command:
```bash
python3 src/experiment.py \
            eval \
            --impldir workdir/kernel-docs \
            --syzkaller /vol/syzkaller \
            --kernel_obj /vol/linux/v6.12.40 \
            --image_obj /vol/images/Debian
```

### Integrate Encoded Kernel MRs

Use `src/experiment.py` for batch integration or `src/MRIntg.py` to specify which EKMRs to integrate. By default, only high-quality MRs are integrated. Use the `--allin` option to include all of them.

Command:
```bash
python3 src/experiment.py \
            integrate \
            --impl_root workdir/kernel-docs \
            --syzkaller $OSMFUZZER/syzkaller \
            --clean
```

Alternatively, use `src/MRIntg.py` for specific integrations:

Command:
```bash
python3 src/MRIntg.py \
            --syzkaller $OSMFUZZER/syzkaller \
            --impls /vol/OS-MFuzzer/workdir/kernel-docs/v6.12.40/kvm/api/1.-General-description/impl/mr.h \
            ...
```

Finally, build syzkaller with the newly integrated EKMRs.

Command:
```bash
make -C $OSMFUZZER/syzkaller clean generate all -j16
```

> [!NOTE]
> While we strive to eliminate them, collisions between encoded kernel MRs may still occur after integration. Some of these may require manual resolution based on the error messages.

### Metamorphic Fuzzing

As mentioned in the [Simplified Usage](#usage-simplified) section, you can now start fuzzing.

Command:
```bash
mkdir workdir
export WORKDIR=/vol/OS-MFuzzer/workdir
export KERNEL=/vol/linux/v6.12.40
export IMAGE=/vol/images/Debian
export SYZKALLER=/vol/OS-MFuzzer/syzkaller
export VMCOUNT=4
cat configs/fuzz/linux.cfg | envsubst > workdir/test.cfg
$OSMFUZZER/syzkaller/bin/syz-manager -config=workdir/test.cfg
```