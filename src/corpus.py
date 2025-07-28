import argparse
import email
import os
from pathlib import Path

from dotenv import load_dotenv
from git import Repo
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils import *


def get_email_body(s: str) -> str:
    """Extract the body of an email message from a string.

    Parameters
    ----------
    s : str
        The email message as a string.

    Returns
    -------
    str
        The body of the email message.
    """
    msg = email.message_from_string(s)
    body = msg.get_payload(decode=True).decode("utf-8")  # type: ignore
    return body


def get_kernel_cves(args: argparse.Namespace):
    """Get kernel CVEs from linux-cve-announce git repository.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments containing the git object directory.
    """
    # Get all kernel CVE announcements from git
    git_obj = args.git_obj
    repo = Repo(git_obj)
    commits = list(repo.iter_commits())

    # Traverse all CVE announcements, get reject CVEs, reject SHAs, and invalid SHAs first
    reject_shas, reject_cves = set(), set()
    invalid_shas = set()
    for commit in commits:
        subject = str(commit.message.strip())
        sha = commit.hexsha
        lst = subject.split(": ")
        cve = str()
        for elem in lst:
            if elem.startswith("CVE-"):
                cve = elem.strip()
        if len(cve) == 0:
            invalid_shas.add(sha)
            continue
        if "REJECTED" in subject:
            reject_shas.add(sha)
            reject_cves.add(cve)

    # We are now starting to get the accepted CVEs and SHAs.We get rejects and accepts respectively
    # to prevent rejects from being added to accepts by mistake.
    accept_shas, accept_cves = set(), set()
    for commit in commits:
        subject = str(commit.message.strip())
        sha = commit.hexsha
        lst = subject.split(": ")
        cve = str()
        for elem in lst:
            if elem.startswith("CVE-"):
                cve = elem.strip()
        if len(cve) == 0:
            continue
        if sha in reject_shas or cve in reject_cves:
            continue
        accept_shas.add(sha)
        accept_cves.add(cve)

    # Save to the local
    out_dir = args.outdir
    md_dir = os.path.join(out_dir, "md")
    os.makedirs(md_dir, exist_ok=True)
    cnt = len(commits)
    for sha in accept_shas:
        try:
            commit = repo.commit(sha)
            subject = str(commit.message.strip())
            blob = commit.tree.blobs[0]
            tmp = blob.data_stream.read().decode("utf-8")
            body = get_email_body(tmp)
            Path(os.path.join(md_dir, sha[:8] + ".md")).write_text(f"{subject}\n\n{body}")
        except Exception as e:
            WARNF(f"Failed to process commit {sha}: {e}")

    # Just in case, check it out
    for cve in accept_cves:
        if cve in reject_cves:
            FATAL("WTF?")

    OKF(f"{git_obj}: \n\t{cnt} commits, \n\t{len(accept_shas)} accepted SHAs.\n\t{len(accept_cves)} accepted CVEs.\n\t{len(reject_shas)} rejected SHAs.\n\t{len(reject_cves)} rejected CVEs\n\t{len(invalid_shas)} invalid commits.\n")


def create_ext_corpus(args: argparse.Namespace):
    """Create an external corpus from the kernel MR identification.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments containing the output directory.
    """
    # Load CVE announcements & split them
    out_dir = args.outdir
    md_dir = os.path.join(out_dir, "md")
    loader = DirectoryLoader(md_dir, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, add_start_index=True)
    docs = splitter.split_documents(documents)

    # Create local chroma db for persist storage
    embeddings = OpenAIEmbeddings(model=args.embeddings)
    chroma_dir = os.path.join(out_dir, "chroma")
    os.makedirs(chroma_dir, exist_ok=True)
    Chroma.from_documents(docs, embeddings, persist_directory=chroma_dir)
    OKF("Done! Corpus created in " + chroma_dir)


def main(args: argparse.Namespace):
    get_kernel_cves(args)
    create_ext_corpus(args)


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Corpus construction script")
    parser.add_argument("--git_obj", type=str, required=True, help="Path to the git object directory (e.g. linux-cve-announce/git/0.git)")
    parser.add_argument("--outdir", type=str, required=True, help="Output directory for the corpus")
    parser.add_argument("--embeddings", type=str, required=True, help="Model name for embeddings (e.g. 'text-embedding-3-large')")
    args = parser.parse_args()
    main(args)
