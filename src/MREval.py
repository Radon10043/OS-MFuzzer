"""
Author       : Radon
Date         : 2025-07-22 16:25:40
LastEditors  : Radon
LastEditTime : 2025-09-13 15:33:11
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

### GLOBAL VARIABLES ###
# Lunch targets for android generic system image (GSI), the former is for GSI < 15, and the latter is for GSI >= 15
TARGETS = ["aosp_cf_x86_64_phone-userdebug", "aosp_cf_x86_64_phone-trunk_staging-userdebug"]
CFHOME = "/tmp/syzeta-eval"
########################


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


def gen_fuzzing_config(args: argparse.Namespace, psyscall: str) -> dict:
    """Generate fuzzing config for syzkaller via kernel type

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    psyscall : str
        Name of the pseudo-syscall to enable

    Returns
    -------
    dict
        Fuzzing config
    """
    image_obj = args.image_obj

    # Generate a unique ID
    id = uuid.uuid4().hex[:8]

    # Get paths to .img and .id_rsa files under image_obj
    imgpath = str()
    idrsapath = str()
    for file in os.listdir(image_obj):
        if file.endswith(".img"):
            imgpath = os.path.join(image_obj, file)
        elif file.endswith(".id_rsa"):
            idrsapath = os.path.join(image_obj, file)

    # Generate fuzzing configs via kernel type
    syzkaller = args.syzkaller
    kernel_obj = args.kernel_obj
    kernel_typ = args.kernel_typ
    out_dir = os.path.join(syzkaller, "workdir", f"out")
    cfg = dict()
    if kernel_typ == "linux":
        cfg = {
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
            "enable_syscalls": [psyscall],  # Just enable the pseudo-syscall to evaluate its quality
            "vm": {"count": 1, "kernel": os.path.join(kernel_obj, "arch", "x86", "boot", "bzImage"), "cpu": 2, "mem": 2048},
        }
    elif kernel_typ == "android":
        cfg = {
            "target": "linux/amd64",
            "http": "127.0.0.1:56741",
            "workdir": out_dir,
            "kernel_obj": kernel_obj,
            "syzkaller": syzkaller,
            "cover": True,
            "type": "adb",
            "reproduce": False,
            "enable_syscalls": [psyscall],  # Just enable the pseudo-syscall to evaluate its quality
            "vm": {"devices": ["0.0.0.0:6520"], "battery_check": True},
        }

    return cfg


def check_image_obj(image_obj: str, kernel_typ: str):
    """Check validation of image_obj

    Parameters
    ----------
    image_obj : str
        Path to the image object
    kernel_typ : str
        Type of kernel under test
    """
    if kernel_typ == "linux":
        # For linux, if image_obj contains both .img and .id_rsa files, we consider it valid
        ext_set = set()
        for file in os.listdir(image_obj):
            if file.endswith(".img") or file.endswith(".id_rsa"):
                ext_set.add(file.split(".")[-1])
        if len(ext_set) != 2:
            FATAL(f"Please ensure that {image_obj} contains both .img and .id_rsa files, but found {ext_set}.")
    elif kernel_typ == "android":
        # For android, if "launch_cvd" exists under image_obj, we consider it valid
        launch_cvd = list((Path(image_obj) / "out" / "host").rglob("launch_cvd"))
        if len(launch_cvd) == 0:
            FATAL(f"launch_cvd is not found, please ensure that system image ({image_obj}) has been built.")
    else:
        FATAL(f"Unknown kernel type: {kernel_typ}")


def prepare(args: argparse.Namespace) -> None:
    """Do some preparations before dry run

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    kernel_typ = args.kernel_typ

    # For linux, we do not need to do anything
    if kernel_typ == "linux":
        return

    # For android, we need to boot system image first
    for target in TARGETS:
        image_obj = args.image_obj
        kernel_obj = args.kernel_obj
        bzImage = Path(kernel_obj) / "bzImage"
        initramfs = Path(kernel_obj) / "initramfs.img"
        # fmt:off
        cmd = (
            "source build/envsetup.sh && "
            f"lunch {target} && "
            f"rm -rf {CFHOME} && "
            f"mkdir -p {CFHOME} && "
            f"yes | launch_cvd -kernel_path={bzImage} -initramfs_path={initramfs} -daemon && "
            "adb connect 0.0.0.0:6520"
        )
        # fmt:on
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=image_obj,
            executable="/bin/bash",
            env={"HOME": CFHOME},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode == 0:  # Boot success
            break
        elif target == TARGETS[-1]:  # Last target, still failed
            FATAL(f"Failed to boot system image")


def wipe_butt(args: argparse.Namespace, out_dir: str) -> None:
    """Remove redundancy generated during the evaluation

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    out_dir : str
        Output directory
    """
    # Generic cleanup
    shutil.rmtree(out_dir, ignore_errors=True)
    clean_repo(args.syzkaller)

    # For linux, we do not need to do anything
    kernel_typ = args.kernel_typ
    if kernel_typ == "linux":
        return

    # For android, we need to stop launched emulator
    image_obj = args.image_obj
    for target in TARGETS:
        # fmt:off
        cmd = (
            "source build/envsetup.sh && "
            f"lunch {target} && "
            "stop_cvd"
        )
        # fmt:on
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=image_obj,
            executable="/bin/bash",
            env={"HOME": CFHOME},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode == 0:  # Stop success
            break
        elif target == TARGETS[-1]:  # Last target, still failed
            FATAL(f"Failed to stop launched emulator")
    shutil.rmtree(CFHOME, ignore_errors=True)


def dryrun(args: argparse.Namespace, psyscall: str) -> Tuple[int, int, int]:
    """Dry run the syzkaller to check whether the pseudo-syscall can cover kernel code, and
    whether encoded metamorphic relation is high-quality.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    psyscall : str
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
    # Generate a unique ID for this dryrun
    id = uuid.uuid4().hex[:8]

    # Generate fuzzing config via kernel type, then make some preparations
    cfg = gen_fuzzing_config(args, psyscall)

    # Add unique ID as suffix
    out_dir = cfg["workdir"] = cfg["workdir"] + f"-{id}"
    cfg_path = Path(out_dir) / "config.json"
    shutil.rmtree(out_dir, ignore_errors=True)  # Create a fresh output directory
    os.makedirs(out_dir, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")  # Write config to file

    # Do some preparations
    prepare(args)

    # Dry run
    syzkaller = args.syzkaller
    timeout = args.timeout
    dryrun_log = os.path.join(out_dir, "dryrun.log")
    try:
        subprocess.run(
            [
                f"{syzkaller}/bin/syz-manager",
                f"-config={cfg_path}",
            ],
            cwd=syzkaller,
            timeout=timeout,  # Dry run for a certain seconds, default by 120s
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired as e:  # This is expected
        Path(dryrun_log).write_text(e.stderr.decode("utf-8"), encoding="utf-8")  # type: ignore
    except Exception as e:
        FATAL(f"Failed to run syzkaller: {e}")

    # Exit program if dryrun log does not exist, for this situation, we should evaluate whether
    # pseudo-syscall is low-quality manually.
    if not os.path.exists(dryrun_log):
        FATAL("Dry run log does not exist, please check manually.")

    # Get latest coverage, total execs, and mrvio execs
    lines = Path(dryrun_log).read_text(encoding="utf-8").splitlines()
    lines.reverse()
    last_line = str()
    for line in lines:
        if "coverage=" in line:
            last_line = line
            break

    # Check coverage, total execs, and mrvio execs
    coverage, exec_total = 0, 0
    try:
        coverage = get_field_val(last_line, "coverage")
        exec_total = get_field_val(last_line, "exec total")
    except BaseException as e:
        # No such field? Maybe syz_mr is running too slow, or other unexpected errors
        # This also requires us to evaluate pseudo-syscall manually
        FATAL(f"Failed to get coverage and exec total, error: {e}")
    mrvio_execs = 0
    for _, _, files in os.walk(os.path.join(out_dir, "mrvio")):
        mrvio_execs += len(files)

    # Wipe my butt :)
    wipe_butt(args, out_dir)

    return coverage, exec_total, mrvio_execs


def main(args: argparse.Namespace):
    """Evaluation quality of encoded metamorphic relation

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    # Check whether syzkaller directory exists, as well as csource, syzlang description, and patch file
    ACTF("Checking args ...")
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
    kernel_typ = args.kernel_typ
    check_image_obj(image_obj, kernel_typ)

    # Check whether commit of syzkaller is 4b25d554
    commit = get_commit(syzkaller)[:8]
    if commit != "4b25d554":
        FATAL(f"Current commit of syzkaller is {commit}, but expected 4b25d554. Please checkout first.")

    # Prompt user that timeout for android kernel should be longer.
    if kernel_typ == "android" and args.timeout < 300:
        WARNF("For android kernel, timeout should be longer (e.g., 300s), otherwise syz-manager may exit before any test cases are executed")
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
    coverage, total_execs, mrvio_execs = dryrun(args, func)
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
    parser.add_argument("--kernel_typ", type=str, required=True, choices=["linux", "android"], help="Type of kernel under test")
    parser.add_argument("--image_obj", type=str, required=True, help="Path to the image object directory")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for a single dry run (seconds)")
    parser.add_argument("--patch", type=str, default=Path(__file__).parent.parent / "patch" / "release.patch", help="Path to the patch file to apply to syzkaller")
    args = parser.parse_args()
    main(args)
