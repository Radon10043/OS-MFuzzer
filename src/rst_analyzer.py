import argparse
import os
import shutil
import uuid
from pathlib import Path

from docutils.core import publish_doctree
from docutils.nodes import block_quote, field, field_list, literal_block, table, footnote

from utils import *


def fieldlist2text(node: field_list) -> str:
    lst = list()
    for child in node.children:  # Each child should be a field node
        if not isinstance(child, field):
            FATAL(f"Expected a field node, but got {type(child)}")
        name = child.children[0].rawsource  # type: ignore
        body = child.children[1].rawsource  # type: ignore
        sep = ": \n" if "\n" in body.rstrip("\n") else ": "
        lst.append(name + sep + body)
    return child.child_text_separator.join(lst)  # type: ignore


def literal2text(node: literal_block) -> str:
    return f"```\n{node.astext()}\n```"


def blockquote2text(node: block_quote) -> str:
    """Convert a blockquote node to text."""
    return node.rawsource


def table2text(node: table) -> str:
    nrow = 0

    # Use dfs to get the number of columns in the table
    def dfs(o):
        nonlocal nrow
        if nrow > 0:
            return
        if o.tagname == "tbody":
            nrow = len(o.children)
            return
        for child in o.children:
            dfs(child)

    for child in node.children:
        dfs(child)
        if nrow > 0:
            break

    if nrow == 0:
        FATAL("No rows found in the table node.")

    tmp = node.astext().lstrip("\n")
    sep = node.child_text_separator
    lst = tmp.split(sep)
    ncol = len(lst) // nrow
    text = str()
    for i in range(len(lst)):
        if i % ncol == 0 and i > 0:
            text = text.rstrip(",") + "\n"
        text += lst[i].strip() + ","
    return text.rstrip(",")


def footnote2text(node: footnote) -> str:
    return ""


def main(args: argparse.Namespace):
    file = args.file
    outdir = args.outdir
    mxdepth = args.max_depth
    content = Path(file).read_text(encoding="utf-8")
    doctree = publish_doctree(content, source_path=file)

    # Use dfs to split documentation into sections (max depth is 3)
    def dfs(o, depth: int) -> str:
        text = str()
        for child in o.children:
            if child.tagname == "comment":
                continue
            if child.tagname == "section":
                text += dfs(child, depth + 1)
            elif child.tagname == "field_list":
                text += fieldlist2text(child) + o.child_text_separator
            elif child.tagname == "literal_block":
                text += literal2text(child) + o.child_text_separator
            elif child.tagname == "block_quote":
                text += blockquote2text(child) + o.child_text_separator
            elif child.tagname == "table":
                text += table2text(child) + o.child_text_separator
            else:
                text += child.astext() + o.child_text_separator
        if depth <= mxdepth:
            Path(os.path.join(outdir), "debug.txt").write_text(text, encoding="utf-8")
            return ""
        return text

    os.makedirs(outdir, exist_ok=True)
    dfs(doctree, 0)
    pass


def check_args(args: argparse.Namespace):
    """Check command line arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments.
    """
    if not os.path.exists(args.file):
        FATAL(f"{args.file} does not exist.")
    if args.remove_exist:
        shutil.rmtree(args.outdir, ignore_errors=True)
    if os.path.exists(args.outdir):
        FATAL(f"{args.outdir} already exists. Please remove it first.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RST file analyzer")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to the RST file")
    parser.add_argument("-o", "--outdir", type=str, required=True, help="Path to the output directory")
    parser.add_argument("-m", "--max-depth", type=int, default=3, help="Maximum depth of the documentation sections to analyze")
    parser.add_argument("--remove-exist", action="store_true", help="Remove existing output directory if it exists")
    args = parser.parse_args()
    check_args(args)
    main(args)
