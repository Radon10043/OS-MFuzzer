"""
Author       : Radon
Date         : 2025-04-16 05:32:03
LastEditors  : Radon
LastEditTime : 2025-08-07 10:21:22
Description  : Integrate MRs to syzkaller
"""

import argparse
import os
import subprocess
import uuid

from clang.cindex import Config, Cursor, CursorKind, Index, TokenKind, TranslationUnit

from utils import *

########## GLOBAL VARIABLES ##########
# Token to skip
BLACK_LIST = {
    CursorKind.STRUCT_DECL: {
        "kvm_ppc_mmuv3_cfg",
        "kvm_create_spapr_tce",
        "kvm_arm_copy_mte_tags",
        "kvm_rtas_token_args",
        "kvm_xen_vcpu_attr",
        "kvm_allocate_rma",
        "kvm_create_spapr_tce_64",
        "kvm_get_htab_fd",
        "kvm_ppc_cpu_char",
        "kvm_ppc_rmmu_info",
    },
    CursorKind.MACRO_DEFINITION: {
        "KVM_XEN_VCPU_GET_ATTR",
    },
    CursorKind.FUNCTION_DECL: {
        "failmsg",
    },
}
######################################


def update_csource(path: str, uuid: str) -> str:
    """Update C source code

    Parameters
    ----------
    path : str
        Path to the C source file
    uuid : str
        uuid, for token suffix

    Returns
    -------
    str
        Updated C source code
    """
    # Load libclang.so
    if not Config.loaded:
        libclang_path = subprocess.run("llvm-config --libdir", shell=True, stdout=subprocess.PIPE).stdout.decode().strip()
        Config.set_library_path(libclang_path)

    # Get content of the C source code
    csource_lines = list()
    with open(path, mode="r", encoding="utf-8") as f:
        csource_lines = f.readlines()

    # Get the AST of the C implementation
    index = Index.create()
    tu = index.parse(path, options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    cursor: Cursor = tu.cursor

    # To prevent conflicts between multiple source files, we need to rename
    # potentially conflicting content.
    # This includes:
    # - Function names
    # - Global variable names
    # - Struct names
    # - Macro definitions
    # We will build a mapping of old names to new names, where the key is the
    # old name and the value is the corresponding new name.
    rename_dict = dict()
    concern_cursor_kinds = {
        CursorKind.FUNCTION_DECL,
        CursorKind.VAR_DECL,
        CursorKind.STRUCT_DECL,
        CursorKind.MACRO_DEFINITION,
    }
    for node in cursor.get_children():
        if node.location.is_in_system_header:  # Skip system headers
            continue
        if node.location.file == None or node.location.file.name != path:  # Skip nodes not belonging to the current file
            continue
        if node.kind in BLACK_LIST.keys() and node.spelling in BLACK_LIST[node.kind]:  # Skip blacklisted nodes
            # TODO: This method is not general enough, is there a better way?
            continue
        if node.kind in concern_cursor_kinds:
            name = node.spelling
            n_name = name + "_" + uuid
            rename_dict[name] = n_name

    # Traverse tokens to rename variables and functions
    # Initially, we used cursor.walk_preorder() to traverse, but the content inside
    # if statements seems to be unparseable. We temporarily replaced it with cursor.get_tokens()
    # TODO: Intuitively, this may be less accurate than traversing the AST, but we
    # haven't found a better solution yet.

    # key: row number, value: number of modifications in this row.
    # If a row has multiple modifications, we need to calculate the column offset.
    mod_times = dict()
    for token in cursor.get_tokens():
        # If the token is not an identifier or its name is not in the rename dictionary, skip it
        if not token.kind == TokenKind.IDENTIFIER or not token.spelling in rename_dict.keys():
            continue

        # Modify token names via mod_times
        # Be careful! This modification may break the code
        name = token.spelling
        row, col = token.location.line, token.location.column

        # Calculate the column offset if the row has been modified before
        offset = 0
        if row in mod_times.keys():
            offset = mod_times[row] * (len(uuid) + 1)
        col += offset

        # Modify token's name
        length = len(name)
        code = csource_lines[row - 1]
        to_replace = code[col - 1 : col + length - 1]
        if to_replace != name:
            FATAL("Damn, C source code might broken. I should not modify it anymore.")
        n_code = code[: col - 1] + rename_dict[name] + code[col + length - 1 :]
        csource_lines[row - 1] = n_code

        # Update mod_times
        if row in mod_times.keys():
            mod_times[row] += 1
        else:
            mod_times[row] = 1

    # Add source location to the header comment
    csource_lines.insert(0, f"// Code from {path}\n")

    return "".join(csource_lines)


def update_syzlang(path: str, uuid: str) -> str:
    """Update syzlang description

    Parameters
    ----------
    path : str
        Path to the syzlang description file
    uuid : str
        uuid, for token suffix

    Returns
    -------
    str
        Updated syzlang description
    """
    desc = str()
    with open(path, mode="r", encoding="utf-8") as f:
        desc = f.read()
    desc = desc.replace("syz_mr", "syz_mr_" + uuid)
    return desc


def integrate(syzkaller: str, csource: str, syzlang: str, func: str):
    """Integrate C source code and syzlang description into syzkaller

    Parameters
    ----------
    syzkaller : str
        Path to the syzkaller directory
    csource : str
        Content of C source code
    syzlang : str
        Content of syzlang description
    func : str
        Function name to be used in syzkaller, usually "syz_mr_<uuid>"
    """
    # Write C source code to syzkaller/executor/MRs/[func].h
    # and format it using syzkaller's clang-format
    os.makedirs(os.path.join(syzkaller, "executor", "MRs"), exist_ok=True)
    fn = os.path.join(syzkaller, "executor", "MRs", func + ".h")
    with open(fn, mode="w", encoding="utf-8") as f:
        f.write(csource)
    res = subprocess.run(["clang-format", "-i", f"--style=file:{syzkaller}/.clang-format", fn])
    if res.returncode != 0:  # unlikely
        FATAL("clang-format failed! Please check the file %s." % fn)

    # Add `#if SYZ_EXECUTOR || __NR_[func]和#include "MRs/[func].h"` to the
    # end of syzkaller/executor/common_linux.h
    common_linux_h = os.path.join(syzkaller, "executor", "common_linux.h")
    with open(common_linux_h, mode="a", encoding="utf-8") as f:
        f.write("\n#if SYZ_EXECUTOR || __NR_" + func + "\n")
        f.write('#include "MRs/%s.h"\n' % func)
        f.write("\n#endif\n")

    # Add syzlang description to syzkaller/sys/linux/metamorphic.txt
    metamorphic_txt = os.path.join(syzkaller, "sys", "linux", "metamorphic.txt")
    with open(metamorphic_txt, mode="a", encoding="utf-8") as f:
        f.write("\n" + syzlang + "\n")

    # Add the function name to linuxSyscallCheck in syzkaller/pkg/vminfo/syscalls.go
    linux_syscalls_go = os.path.join(syzkaller, "pkg", "vminfo", "linux_syscalls.go")
    lines = list()
    with open(linux_syscalls_go, mode="r", encoding="utf-8") as f:
        lines = f.readlines()
    if not lines[104].startswith('\t"syz_create_resource"'):
        FATAL("Damn, the syscall list has been modified. I should not modify it anymore.")
    lines[104] += '"%s":alwaysSupported,\n' % func
    with open(linux_syscalls_go, mode="w", encoding="utf-8") as f:
        f.writelines(lines)


def main(args: argparse.Namespace):
    syzkaller_dir = args.syzkaller
    impls = args.impls
    patch = args.patch
    for impl in impls:
        # Traverse the implementation directory, update C source code and
        # syzlang description
        uuid4 = uuid.uuid4().hex[:8]

        # Update C source code
        csource_path = os.path.join(impl, "mr.h")
        csource = update_csource(csource_path, uuid4)

        # Update syzlang description
        syzlang_path = os.path.join(impl, "syzlang.txt")
        syzlang_desc = update_syzlang(syzlang_path, uuid4)

        # Integrate into syzkaller
        func = "syz_mr_" + uuid4
        integrate(syzkaller_dir, csource, syzlang_desc, func)
        OKF("%s is integrated into syzkaller!" % impl)
    patch_syzkaller(syzkaller_dir, patch)

    WARNF("Integration is complete! Now you can run `make generate -j && make clean all -j` to build syzkaller.")
    SAYF("    Note that errors may occur during the building, please correct them manually.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Integrate MR implementation into syzkaller")
    parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory")
    parser.add_argument("--impls", type=str, required=True, nargs="+", help="Path to the MR implementation directory")
    parser.add_argument("--patch", type=str, default=os.path.join(os.path.dirname(__file__), "..", "patch", "release.patch"), help="Patch for the syzkaller")
    args = parser.parse_args()
    main(args)
