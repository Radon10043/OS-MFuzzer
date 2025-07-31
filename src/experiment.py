import argparse
import os
import random
import smtplib
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

import MREval
import MRIden
import MRImpl
from utils import *


def send_email(subject: str, body: str, receiver: str):
    """Send an email notification.

    Parameters
    ----------
    subject : str
        Subject of the email
    body : str
        Body content of the email
    receiver : str
        Email address to send the notification to
    """
    msg = MIMEMultipart()
    sender = os.getenv("EMAIL_SENDER")
    passwd = os.getenv("EMAIL_PASSWORD")
    host = os.getenv("EMAIL_HOST")
    port = os.getenv("EMAIL_PORT")
    if sender is None:
        FATAL("Email sender is not configured in .env file.")
    elif passwd is None:
        FATAL("Email password is not configured in .env file.")
    elif host is None:
        FATAL("Email host is not configured in .env file.")
    elif port is None:
        FATAL("Email port is not configured in .env file.")
    msg["From"] = sender  # type: ignore
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP(host, port)  # type: ignore
        server.starttls()
        server.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))  # type: ignore
        server.sendmail(msg["From"], msg["To"], msg.as_string())
        server.quit()
    except Exception as e:
        FATAL(f"Failed to send email: {e}")


def gen_iden_config(specdir: str, driver: str, spec: str, corpus: str) -> dict:
    """Generate configuration for MR identification.

    Parameters
    ----------
    specdir : str
        Path to the specification directory
    driver : str
        Driver name, e.g., "autofs"
    spec : str
        Abstract path to specification file
    corpus : str
        Abstract path to corpus directory

    Returns
    -------
    dict
        Configuration dictionary for MR identification
    """
    proj = str(os.getenv("PROJECT"))
    pmptdir = os.path.join(proj, "data", "prompts")
    lst = spec.split(os.path.sep)
    ver = os.path.basename(specdir)
    while lst[0] != driver:
        lst.pop(0)
    lst[-1] = lst[-1].replace(".txt", "")
    outdir = os.path.join(proj, "workdir", "MRs", ver, *lst, "iden")
    config = {
        "identifier": {
            "base_url": os.getenv("GOOGLE_OPENAI_API_BASE"),
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "framework": "openai",
            "model": "gemini-2.5-pro",
            "temperature": 0.5,
            "stream": False,
            "prompts": {
                "system": os.path.join(pmptdir, "identifier", "system.md"),
                "user": [
                    os.path.join(pmptdir, "identifier", "init.md"),
                    os.path.join(pmptdir, "identifier", "follow.md"),
                ],
            },
        },
        "calibrator": {
            "base_url": os.getenv("OPENAI_API_BASE"),
            "api_key": os.getenv("OPENAI_API_KEY"),
            "framework": "openai",
            "model": "o3",
            "temperature": 0.2,
            "stream": False,
            "prompts": {
                "system": os.path.join(pmptdir, "calibrator", "system.md"),
                "user": [os.path.join(pmptdir, "calibrator", "vanilla.md")],
            },
        },
        "corpus": corpus,
        "max_iter": 10,
        "output": outdir,
        "specification": spec,
        "driver_name": driver,
    }
    return config


def gen_impl_config(filepath: str, syzkaller: str) -> dict:
    """Generate configuration for MR implementation.

    Parameters
    ----------
    filepath : str
        Absolute path to the MR specification file, i.e., mr_final.md
    syzkaller : str
        Absolute path to the syzkaller directory

    Returns
    -------
    dict
        Configuration dictionary for MR implementation
    """
    from os.path import dirname, join

    proj = str(os.getenv("PROJECT"))
    pmptdir = join(proj, "data", "prompts")
    outdir = join(dirname(dirname(filepath)), "impl")
    config = {
        "c": {
            "base_url": os.getenv("GOOGLE_OPENAI_API_BASE"),
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "framework": "openai",
            "model": "gemini-2.5-pro",
            "temperature": 0.5,
            "stream": False,
            "prompts": {
                "system": join(pmptdir, "c-programmer", "system.md"),
                "user": [
                    join(pmptdir, "c-programmer", "init.md"),
                    join(pmptdir, "c-programmer", "follow.md"),
                ],
            },
        },
        "syzlang": {
            "base_url": os.getenv("GOOGLE_OPENAI_API_BASE"),
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "framework": "openai",
            "model": "gemini-2.5-pro",
            "temperature": 0.5,
            "stream": False,
            "prompts": {
                "system": join(pmptdir, "syzlang-programmer", "system.md"),
                "user": [
                    join(pmptdir, "syzlang-programmer", "init.md"),
                    join(pmptdir, "syzlang-programmer", "follow.md"),
                ],
            },
        },
        "mr_desc": filepath,
        "max_iter": 10,
        "output": outdir,
        "compiler": "gcc",
        "syzkaller": syzkaller,
    }
    return config


def perf_iden(cfg: dict):
    """Perform MR identification

    Parameters
    ----------
    cfg : dict
        Configuration dictionary for MR identification
    """
    retry = 3
    while retry > 0:
        try:
            MRIden.main(cfg)
            break
        except Exception as e:
            retry -= 1
            if retry == 0:
                FATAL(f"MR identification failed after {retry} attempts: {e}")
            t = random.randint(1, 60)
            WARNF(f"MR identification failed: {e}")
            WARNF(f"Have a break for {t} seconds ... ({retry} attempts left)")
            time.sleep(t)


def iden(args: argparse.Namespace):
    """Run MR identification experiment.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    # Traverse each file under specdir, get driver name, specification contents
    # Path structure is expected to be: {version}/{driver}/{doc}/{text file or subdir}
    # Here is an exmaple: v5.15.189/autofs/autofs/Catatonic-mode.txt
    specdir = os.path.abspath(args.specdir)
    corpus = os.path.abspath(args.corpus)
    if not os.path.basename(specdir).startswith("v"):
        FATAL("Use version directory as specdir is recommended, e.g. /path/to/v5.15.189")
    ACTF("Running MR identification ...")
    for driver in os.listdir(specdir):
        for root, _, files in os.walk(os.path.join(specdir, driver)):
            for file in files:
                if not file.endswith(".txt"):
                    continue
                SAYF(f"========== [driver: {driver} / spec: {file}]  ==========\n")
                cfg = gen_iden_config(specdir, driver, os.path.join(root, file), corpus)
                outdir = cfg["output"]
                # If the output directory already exists, skip it so we can resume the last run
                if os.path.exists(outdir):
                    WARNF(f"Output directory {outdir} already exists, skipping...")
                    continue
                perf_iden(cfg)
    if len(args.email) > 0:  # Send email notification if email is provided
        subject = "SyzMeta MR Identification Completed"
        body = "Hi,\n\n"
        body += "The MR identification experiment is completed.\n\n"
        body += "Best regards,\nSyzMeta Experiment Runner"
        send_email(subject, body, args.email)
        OKF("Successfully send email notification to " + args.email)
    OKF("We're done here!")


def perf_impl(cfg: dict):
    """Perform MR implementation

    Parameters
    ----------
    cfg : dict
        Configuration dictionary for MR implementation
    """
    retry = 3
    while retry > 0:
        try:
            MRImpl.main(cfg)
            break
        except Exception as e:
            retry -= 1
            if retry == 0:
                FATAL(f"MR implementation failed after {retry} attempts: {e}")
            t = random.randint(1, 60)
            WARNF(f"MR implementation failed: {e}")
            WARNF(f"Have a break for {t} seconds ... ({retry} attempts left)")


def impl(args: argparse.Namespace):
    """Run MR implementation experiment.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    # Traverse each file under args.path, read mr_final.md and generate code
    idendir = os.path.abspath(args.idendir)
    syzkaller = os.path.abspath(args.syzkaller)
    for root, _, files in os.walk(idendir):
        for file in files:
            if file != "mr_final.md":
                continue
            SAYF(f"========== [MR: {root} / syzkaller: {syzkaller}]  ==========\n")
            cfg = gen_impl_config(os.path.join(root, file), syzkaller)
            outdir = cfg["output"]
            # If the output directory already exists, skip it so we can resume the last run
            if os.path.exists(outdir):
                WARNF(f"Output directory {outdir} already exists, skipping...")
                continue
            perf_impl(cfg)
    if len(args.email) > 0:  # Send email notification if email is provided
        subject = "SyzMeta MR Implementation Completed"
        body = "Hi,\n\n"
        body += "The MR Implementation experiment is completed.\n\n"
        body += "Best regards,\nSyzMeta Experiment Runner"
        send_email(subject, body, args.email)
        OKF("Successfully send email notification to " + args.email)
    OKF("We're done here!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SyzMeta Experiment Runner")
    parser.add_argument("--email", type=str, default="", help="Email address to receive notifications")

    subparser = parser.add_subparsers(title="experiment", required=True)

    # Subparser for MR identification
    iden_parser = subparser.add_parser("iden", help="Run MR identification")
    iden_parser.add_argument("--specdir", type=str, required=True, help="Specification directory")
    iden_parser.add_argument("--corpus", type=str, required=True, help="Corpus directory")
    iden_parser.set_defaults(func=iden)

    # Subparser for MR implementation
    impl_parser = subparser.add_parser("impl", help="Run MR implementation")
    impl_parser.add_argument("--idendir", type=str, required=True, help="Root directory of identification result")
    impl_parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory")
    impl_parser.set_defaults(func=impl)

    load_dotenv()
    args = parser.parse_args()
    try:
        args.func(args)
    except BaseException as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
        error_message = "".join(tb)
        if len(args.email) > 0:  # Send email notification if email is provided
            subject = "SyzMeta Experiment Error"
            body = "Hi,\n\n"
            body += "An error occurred during the experiment:\n\n"
            body += error_message + "\n\n"
            body += "Program args: " + " ".join(sys.argv) + "\n\n"
            body += "Best regards,\nSyzMeta Experiment Runner"
            send_email(subject, body, args.email)
            OKF("Successfully send email notification to " + args.email)
        else:
            FATAL(f"An error occurred: {error_message}")
