import argparse
import os
import re
import shutil
from pathlib import Path
from typing import Any

from docutils.core import publish_doctree
from docutils.nodes import block_quote, field, field_list, footnote, literal_block, table, title
from docutils import nodes

from utils import *


def fieldlist2text(node: field_list) -> str:
    """Convert a field_list node to text.

    Parameters
    ----------
    node : field_list
        The field_list node to convert.

    Returns
    -------
    str
        The text representation of the field_list node.
    """
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
    """Convert a literal_block node to text.

    Parameters
    ----------
    node : literal_block
        The literal_block node to convert.

    Returns
    -------
    str
        The text representation of the literal_block node.
    """
    return f"```\n{node.astext()}\n```"


def blockquote2text(node: block_quote) -> str:
    """Convert a block_quote node to text.

    Parameters
    ----------
    node : block_quote
        The block_quote node to convert.

    Returns
    -------
    str
        The text representation of the block_quote node.
    """
    return node.rawsource


def table2text(node: table) -> str:
    """Convert a table node to text.

    Parameters
    ----------
    node : table
        The table node to convert.

    Returns
    -------
    str
        The text representation of the table node.
    """
    nrow = 0

    def dfs(o: Any):
        """Traverse the table node to find the number of rows.

        Parameters
        ----------
        o : Any
            The current node in the table to traverse.
        """
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

    # Get number of rows and columns, represent the table as a csv string
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


def title2text(node: title) -> str:
    """Convert a title node to text.

    Parameters
    ----------
    node : title
        The title node to convert.

    Returns
    -------
    str
        The text representation of the title node.
    """
    return node.astext().strip()


def footnote2text(node: footnote) -> str:
    """Convert a footnote node to text.

    Parameters
    ----------
    node : footnote
        The footnote node to convert.

    Returns
    -------
    str
        The text representation of the footnote node.
    """
    return node.rawsource.replace("\n", " ").rstrip()


def main(args: argparse.Namespace):
    """Main function to analyze RST files and extract sections.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments.
    """
    file = args.file
    outdir = args.outdir
    mxdepth = args.max_depth
    content = Path(file).read_text(encoding="utf-8")
    doctree = publish_doctree(content, source_path=file)

    # Use dfs to split documentation into sections (max depth is 3)
    def dfs(o: Any, depth: int) -> str:
        """Traverse the doctree and extract text from each section.
        Note that if the section is too short (<10 lines), it will not be saved.

        Parameters
        ----------
        o : Any
            The doctree node to traverse.
        depth : int
            The current depth in the document structure.

        Returns
        -------
        str
            The extracted text from the section.
        """
        text = str()
        title = str()
        for child in o.children:
            if isinstance(child, nodes.comment) or isinstance(child, nodes.system_message):
                continue
            if isinstance(child, nodes.section):
                text += dfs(child, depth + 1)
            elif isinstance(child, nodes.field_list):
                text += fieldlist2text(child) + o.child_text_separator
            elif isinstance(child, nodes.literal_block):
                text += literal2text(child) + o.child_text_separator
            elif isinstance(child, nodes.block_quote):
                text += blockquote2text(child) + o.child_text_separator
            elif isinstance(child, nodes.table):
                text += table2text(child) + o.child_text_separator
            elif isinstance(child, nodes.footnote):
                text += footnote2text(child) + o.child_text_separator
            elif isinstance(child, nodes.title):
                title = title2text(child)
                text += title + o.child_text_separator
            else:
                text += child.astext() + o.child_text_separator
        if depth <= mxdepth:
            dn = re.sub(r'[\\/:*?"<>|()$]', "", title)
            dn = dn.replace(" ", "-")
            dp = os.path.join(outdir, dn)
            fp = os.path.join(dp, "content.txt")
            if os.path.exists(fp):
                FATAL("Duplicate file name detected.")
            if len(text.splitlines()) < 10:
                WARNF(f"Section '{title}' is too short, skipping it.")
            else:
                os.makedirs(dp)
                Path(fp).write_text(text.rstrip("\n"), encoding="utf-8")
            return ""
        return text

    # Use dfs to traverse the doctree, extract text, and save to the local
    ACTF("Start to analyze RST file ...")
    os.makedirs(outdir, exist_ok=True)
    dfs(doctree, 0)
    OKF("RST file analysis completed.")


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
    elif os.path.exists(args.outdir):
        FATAL(f"{args.outdir} already exists. Please remove it first.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RST file analyzer")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to the RST file")
    parser.add_argument("-o", "--outdir", type=str, required=True, help="Path to the output directory")
    parser.add_argument("-m", "--max-depth", type=int, default=2, help="Maximum depth of the documentation sections to analyze")
    parser.add_argument("--remove-exist", action="store_true", help="Remove existing output directory if it exists")
    args = parser.parse_args()
    check_args(args)
    main(args)
