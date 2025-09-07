import argparse
import email
import os
import shutil
import sys
from os.path import abspath, basename, dirname, join
from pathlib import Path

import pandas as pd
from git import Repo

sys.path.append(join(dirname(abspath(__file__)), ".."))
from utils import *


def filter_bugs(args: argparse.Namespace):
    """Filter specified bugs and copy them to a new directory

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    indir, hashes, outdir = args.input, set(args.hashes), args.output
    cnt = 0
    for root, dirs, _ in os.walk(indir):
        if basename(root) != "crashes":
            continue
        for dir in dirs:
            if dir not in hashes:
                continue
            src = join(root, dir)
            dst = join(outdir, src.removeprefix(indir).lstrip(os.sep))
            os.makedirs(dst, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            cnt += 1
    OKF(f"Copied {cnt} folder(s) from {indir} to {outdir}.")


def get_all_crash_info(path: str) -> list[tuple[str, str]]:
    """Get information of all crashes in the given directory

    Parameters
    ----------
    path : str
        Path to the directory containing crashes

    Returns
    -------
    list[tuple[str]]
        A list of tuples, each containing (crash description, hash)
    """
    crash_info = list()
    desc_paths = Path(path).rglob("description")
    for desc_path in desc_paths:
        desc = desc_path.read_text().strip()
        hash = desc_path.parent.name
        crash_info.append((desc, hash))
    return crash_info


def merge(args: argparse.Namespace):
    """合并syzkaller-based fuzzer保存的crashes

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数
    """
    fuzzers = args.fuzzers
    crash_dict = dict()  # { "kernel bug desc ...": { "hash": "123abc...", "fuzzers": { "fuzzer1", ... } } }
    for fuzzer in fuzzers:
        crash_info = get_all_crash_info(fuzzer)
        for desc, hash in crash_info:
            if desc not in crash_dict:
                crash_dict[desc] = dict()
                crash_dict[desc]["hash"] = hash
                crash_dict[desc]["fuzzers"] = set()
            crash_dict[desc]["fuzzers"].add(fuzzer)

    # 以CSV的形式打印合并结果
    print('Hash,Crash Description,"' + '","'.join(fuzzers) + '"')
    for desc, subdict in crash_dict.items():
        hash = subdict["hash"]
        exposed_fuzzers = subdict["fuzzers"]
        line = f'{hash},"{desc}",' + ",".join("TRUE" if fuzzer in exposed_fuzzers else "FALSE" for fuzzer in fuzzers)
        print(line)


def mergenew(args: argparse.Namespace):
    """合并新的crash信息

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数
    """
    # Read excel
    excel = args.excel
    df = pd.read_excel(excel, sheet_name="Bugs", header=2, engine="calamine")  # 读取存储bug信息的sheet
    new_bug_df = df[df["new"] == True]

    # Prepare table data
    vis = set()
    data_list = list()
    for _, row in new_bug_df.iterrows():
        # Prevent duplicate accessing
        desc = row["desc"]
        if desc in vis:
            continue
        vis.add(desc)

        # Collect kernel versions and syzkaller/SyzMeta exposure
        vers = new_bug_df[new_bug_df["desc"] == desc]["kernel version"].unique().tolist()
        syzmeta_vers = new_bug_df[(new_bug_df["desc"] == desc) & (new_bug_df["SyzMeta exposed"] == True)]["kernel version"].unique().tolist()
        syzkaller_vers = new_bug_df[(new_bug_df["desc"] == desc) & (new_bug_df["syzkaller exposed"] == True)]["kernel version"].unique().tolist()
        vers.sort()
        syzmeta_vers.sort()
        syzkaller_vers.sort()
        data_list.append(
            {
                "desc": desc,
                "kernel version": ", ".join(vers),
                "SyzMeta": ", ".join(syzmeta_vers),
                "syzkaller": ", ".join(syzkaller_vers),
            }
        )

    # Output as CSV
    data_df = pd.DataFrame(data_list)
    data_df.to_csv(sys.stdout, index=False)


def is_0day_bug(desc: str, lkml: str) -> bool:
    """Check if the given crash description corresponds to a possible 0-day bug

    Parameters
    ----------
    desc : str
        Crash description
    lkml : str
        Path to the mirror of Linux Kernel Mailing List

    Returns
    -------
    bool
        True if it is a possible 0-day bug, False otherwise
    """
    repo = Repo(lkml)
    commits = list(repo.iter_commits())
    for commit in commits:
        subject = str(commit.message.strip())
        blob = commit.tree.blobs[0]
        tmp = blob.data_stream.read().decode("utf-8")
        msg = email.message_from_string(tmp)
        body = msg.get_payload(decode=True).decode("utf-8")  # type: ignore
        if desc in subject or desc in body:
            return False
    return True


def print_possible_0day_bugs(crashdir: str, lkml: str):
    """Print possible 0-day bugs

    Parameters
    ----------
    crashdir : str
        Path to the directory of crashes generated by syzkaller-based fuzzer
    lkml : str
        Path to the mirror of Linux Kernel Mailing List
    """
    crash_info = get_all_crash_info(crashdir)
    have_0day = False
    for desc, hash in crash_info:
        if is_0day_bug(desc, lkml):
            have_0day = True
            print(f"{hash}: {desc}")
    if not have_0day:
        OKF("No possible 0-day bugs found.")
    else:
        WARNF("Note: The above bugs are only possible 0-day bugs. Manual verification is required.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process crashes generated by syzkaller-based fuzzer.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand for filtering specified bugs
    filter_parser = subparsers.add_parser("filter", help="Filter specified bugs and copy them to a new directory")
    filter_parser.add_argument("--input", type=str, required=True, help="Input directory containing crashes")
    filter_parser.add_argument("--hashes", nargs="+", type=str, required=True, help="List of hashes to filter")
    filter_parser.add_argument("--output", type=str, required=True, help="Output directory to save filtered crashes")
    filter_parser.set_defaults(func=filter_bugs)

    # Subcommand for merging
    merge_parser = subparsers.add_parser("merge", help="Merge crashes")
    merge_parser.add_argument("--fuzzers", nargs="+", type=str, required=True, help="List of fuzzers to merge crashes from")
    merge_parser.set_defaults(func=merge)

    # Subcommand for mergenew
    mergenew_parser = subparsers.add_parser("mergenew", help="Merge new crashes")
    mergenew_parser.add_argument("--excel", type=str, required=True, help="Path to the Excel file containing new crashes")
    mergenew_parser.set_defaults(func=mergenew)

    # Subcommand for print possible 0-day bug
    day0_parser = subparsers.add_parser("day0", help="Print possible 0-day bugs")
    day0_parser.add_argument("--crashdir", type=str, required=True, help="Path to the directory of crashes generated by syzkaller-based fuzzer")
    day0_parser.add_argument("--lkml", type=str, required=True, help="Path to the mirror of Linux Kernel Mailing List")
    day0_parser.set_defaults(func=lambda args: print_possible_0day_bugs(args.crashdir, args.lkml))

    # Parse the arguments
    args = parser.parse_args()
    args.func(args)
