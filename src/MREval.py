"""
Author       : Radon
Date         : 2025-07-22 16:25:40
LastEditors  : Radon
LastEditTime : 2025-08-07 09:27:07
Description  : Evaluate quality of encoded metamorphic relation
"""

import argparse
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Tuple

from utils import *


def get_field_val(line: str, field: str) -> int:
    """Get the value of a specific field in a line.

    Parameters
    ----------
    line : str
        The line from the log of syzkaller(-based) fuzzer
    field : str
        Field name to extract the value from, e.g., "coverage", "exec total"

    Returns
    -------
    int
        The value of the field
    """
    lst = line.split(field + "=")
    if len(lst) < 2:
        FATAL(f"Field '{field}' not found in line: {line}")
    suffix = lst[1].strip()
    val = 0
    for ch in suffix:
        if ch.isdigit():
            val = val * 10 + int(ch)
        else:
            break
    return val


def dryrun(syzkaller: str, kernel_obj: str, image_obj: str, func: str) -> Tuple[int, int, int]:
    """Dry run the syzkaller to check whether the pseudo-syscall can cover kernel code, and
    whether encoded metamorphic relation is high-quality.

    Parameters
    ----------
    syzkaller : str
        Path to the syzkaller directory
    kernel_obj : str
        Path to the kernel object directory
    image_obj : str
        Path to the image object directory
    func : str
        Name of the pseudo-syscall

    Returns
    -------
    Tuple[int, int, int]
        coverage, total execs, mrvio execs

        Please note that, `mrvio execs` may more than `total execs` since we got the latter from
        the log of syzkaller, while the former is got from counting files under `out_dir/mrvio`,
        time difference may cause the inconsistency.

        TODO: We can modify syzkaller to output `mrvio execs` in the same way as `total execs`
    """
    id = uuid.uuid4().hex[:8]
    os.makedirs(os.path.join(syzkaller, "workdir"), exist_ok=True)
    shutil.rmtree(os.path.join(syzkaller, "workdir", f"out-{id}"), ignore_errors=True)

    imgpath = str()
    idrsapath = str()
    for file in os.listdir(image_obj):
        if file.endswith(".img"):
            imgpath = os.path.join(image_obj, file)
        elif file.endswith(".id_rsa"):
            idrsapath = os.path.join(image_obj, file)

    out_dir = os.path.join(syzkaller, "workdir", f"out-{id}")
    config_path = os.path.join(syzkaller, "workdir", f"config-{id}.json")
    fuzzing_config = {
        "target": "linux/amd64",
        "http": "127.0.0.1:56741",
        "workdir": out_dir,
        "kernel_obj": kernel_obj,
        "image": imgpath,
        "sshkey": idrsapath,
        "syzkaller": syzkaller,
        "procs": 8,
        "type": "qemu",
        "reproduce": False,
        "enable_syscalls": [func],  # Just enable the pseudo-syscall to evaluate its quality
        "vm": {"count": 1, "kernel": os.path.join(kernel_obj, "arch", "x86", "boot", "bzImage"), "cpu": 2, "mem": 2048},
    }
    Path(config_path).write_text(json.dumps(fuzzing_config, indent=4), encoding="utf-8")

    # Dry run
    dryrun_log = os.path.join(out_dir, "dryrun.log")
    try:
        subprocess.run(
            [
                f"{syzkaller}/bin/syz-manager",
                f"-config={config_path}",
            ],
            cwd=syzkaller,
            timeout=120,  # Dry run for 120 seconds
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired as e:  # This is expected
        Path(dryrun_log).write_text(e.stderr.decode("utf-8"), encoding="utf-8")  # type: ignore
    except Exception as e:
        FATAL(f"Failed to run syzkaller: {e}")

    # Return 0, 0, 0 if dryrun_log does not exist
    if not os.path.exists(dryrun_log):
        return 0, 0, 0

    # Get latest coverage, total execs, and mrvio execs
    lines = Path(dryrun_log).read_text(encoding="utf-8").splitlines()
    lines.reverse()
    last_line = str()
    for line in lines:
        if "coverage=" in line:
            last_line = line
            break

    # Check coverage, total execs, and mrvio execs
    coverage = get_field_val(last_line, "coverage")
    exec_total = get_field_val(last_line, "exec total")
    mrvio_execs = 0
    for _, _, files in os.walk(os.path.join(out_dir, "mrvio")):
        mrvio_execs += len(files)
    # shutil.rmtree(out_dir)  # Remove the output directory & config file after dry run
    # os.remove(config_path)

    return coverage, exec_total, mrvio_execs


def main(args):
    # Check whether syzkaller image directory, as well as csource, syzlang description, and patch file
    ACTF("Checking configs ...")
    syzkaller = args.syzkaller
    csource_path = args.csource
    syzlang_path = args.syzlang
    patch = args.patch
    if not os.path.exists(syzkaller):
        FATAL(f"{syzkaller} does not exist.")
    if not os.path.exists(csource_path):
        FATAL(f"{csource_path} does not exist.")
    if not os.path.exists(syzlang_path):
        FATAL(f"{syzlang_path} does not exist.")
    if not os.path.exists(patch):
        FATAL(f"{patch} does not exist.")
    csource = Path(csource_path).read_text(encoding="utf-8")
    syzlang = Path(syzlang_path).read_text(encoding="utf-8")
    syz_lines = syzlang.split("\n")
    for line in syz_lines:
        if not line.startswith("#") and not line.startswith("include"):
            func = line.split("(")[0]
            break

    # Check whether vmlinux exist under kernel_obj
    kernel_obj = args.kernel_obj
    vmlinux = os.path.join(kernel_obj, "vmlinux")
    if not os.path.exists(vmlinux):
        FATAL(f"{vmlinux} does not exist, please build first.")

    # Check whether *.img & *.id_rsa exist under image_obj
    image_obj = args.image_obj
    ext_set = set()
    for file in os.listdir(image_obj):
        if file.endswith(".img") or file.endswith(".id_rsa"):
            ext_set.add(file.split(".")[-1])
    if not len(ext_set) == 2:
        FATAL(f"Please ensure that {image_obj} contains both .img and .id_rsa files, but found {ext_set}.")

    # Check whether commit of syzkaller is 4b25d554
    commit = get_commit(syzkaller)[:8]
    if commit != "4b25d554":
        FATAL(f"Current commit of syzkaller is {commit}, but expected 4b25d554. Please checkout first.")
    OKF("Configs are valid!")

    # Patch syzkaller to support metamorphic testing
    ACTF("Patching syzkaller ...")
    clean_repo(syzkaller)
    patch_syzkaller(syzkaller, patch)

    # Add csource & syzlang desc to syzkaller, then build it
    ACTF("Add pseudo-syscall & build syzkaller ...")
    add_pseudo_syscall(syzkaller, csource, syzlang, func)
    retval, stderr, stdout = build_syzkaller(syzkaller)
    if retval != 0:
        FATAL(f"Failed to build syzkaller: {stderr}\n\n{stdout}")

    # Dryrun for fuzzing, check whether pseudo-syscall can cover kernel code,
    # and if many violations are reported, we should consider that the pseudo-syscall
    # is low-quality
    ACTF("Dry run syzkaller to evaluate the quality of pseudo-syscall ...")
    coverage, total_execs, mrvio_execs = dryrun(syzkaller, kernel_obj, image_obj, func)
    mark_root = os.path.dirname(os.path.abspath(csource_path))
    lqmk = os.path.join(mark_root, ".low_quality")  # Low-Quality MarK
    reason = list()
    if coverage == 0:
        reason.append("0 kernel coverage.")
    elif mrvio_execs / total_execs >= 0.9:
        reason.append(f"High MRVIO execs: {mrvio_execs} / {total_execs} >= 0.9")
    if len(reason) > 0:
        Path(lqmk).write_text("\n".join(reason), encoding="utf-8")
        WARNF(f"Pseudo-syscall is low-quality, please check {lqmk} for details.")
    evmk = os.path.join(mark_root, ".eval")  # EValuation MarK, indicating that the evaluation is done
    Path(evmk).write_text(f"coverage={coverage}, total_execs={total_execs}, mrvio_execs={mrvio_execs}", encoding="utf-8")
    OKF("We are done here!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate encoded metamorphic relation")
    parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory, must be commit 4b25d554")
    parser.add_argument("--csource", type=str, required=True, help="Path to the C source file of pseudo-syscall")
    parser.add_argument("--syzlang", type=str, required=True, help="Path to the syzlang description of pseudo-syscall")
    parser.add_argument("--kernel_obj", type=str, required=True, help="Path to the kernel object directory")
    parser.add_argument("--image_obj", type=str, required=True, help="Path to the image object directory")
    parser.add_argument("--patch", type=str, default=os.path.join(os.path.dirname(__file__), "..", "patch", "debug.patch"), help="Path to the patch file to apply to syzkaller")
    args = parser.parse_args()
    main(args)
