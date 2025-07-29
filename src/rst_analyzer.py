import argparse
import os
from pathlib import Path

from docutils.core import publish_doctree

from utils import *


def main(args: argparse.Namespace):
    file = args.file
    content = Path(file).read_text(encoding="utf-8")
    doctree = publish_doctree(content, source_path=file)

    def dfs(o, level: int):
        for child in o.children:
            if hasattr(child, 'children') and child.children:
                dfs(child, level + 1)
            else:
                print(child.astext())

    dfs(doctree, 0)



def check_args(args: argparse.Namespace):
    """Check command line arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments.
    """
    if not os.path.exists(args.file):
        FATAL(f"{args.file} does not exist.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RST file analyzer")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to the RST file")
    args = parser.parse_args()
    main(args)
