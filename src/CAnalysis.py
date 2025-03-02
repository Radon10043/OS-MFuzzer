import argparse
import subprocess

from clang.cindex import Config, Cursor, CursorKind, Index


def main(args: argparse.Namespace):
    """Main function of CAnalysis

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    Config.set_library_file("/usr/local/lib/libclang.so.19.1")
    index = Index.create()
    tu = index.parse("/home/radon/Documents/projects/kernel-driver-MR-identify/test.c")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, help="Path of .c file")
    args = parser.parse_args()
    main(args)
