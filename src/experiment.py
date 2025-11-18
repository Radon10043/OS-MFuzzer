import argparse
import os
import random
import shutil
import smtplib
import sys
import traceback
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from git import Repo

import MREval
import MRIden
import MRImpl
import MRIntg
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


def gen_iden_config(driver: str, spec: str, corpus: str | None) -> dict:
    """Generate configuration for MR identification.

    Parameters
    ----------
    driver : str
        Driver name, e.g., "autofs"
    spec : str
        Absolute path to specification file
    corpus : str | None
        Absolute path to corpus directory

    Returns
    -------
    dict
        Configuration dictionary for MR identification
    """
    proj = str(os.getenv("PROJECT"))
    pmptdir = os.path.join(proj, "data", "prompts")
    outdir = os.path.join(os.path.dirname(spec), "iden")
    config = {
        "identifier": {
            "base_url": os.getenv("CA_OPENAI_API_BASE"),
            "api_key": os.getenv("CA_API_KEY"),
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
            "base_url": os.getenv("CA_OPENAI_API_BASE"),
            "api_key": os.getenv("CA_API_KEY"),
            "framework": "openai",
            "model": "o3",
            "temperature": 0.2,
            "stream": False,
            "prompts": {
                "system": os.path.join(pmptdir, "calibrator", "system.md"),
                "user": [os.path.join(pmptdir, "calibrator", "vanilla.md")],
            },
        },
        "max_iter": 10,
        "output": outdir,
        "specification": spec,
        "driver_name": driver,
    }
    if corpus is not None:
        config["corpus"] = corpus
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
            "base_url": os.getenv("CA_OPENAI_API_BASE"),
            "api_key": os.getenv("CA_API_KEY"),
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
            "base_url": os.getenv("CA_OPENAI_API_BASE"),
            "api_key": os.getenv("CA_API_KEY"),
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
    # Traverse each 'content.txt' under specdir, get driver name, specification contents
    specdir = os.path.abspath(args.specdir)
    corpus = os.path.abspath(args.corpus) if args.corpus is not None else None
    drivers = os.listdir(specdir)   # Not very robust
    OKF("Drivers: " + ", ".join(drivers))
    ACTF("Running MR identification ...")
    for driver in drivers:
        files = Path(os.path.join(specdir, driver)).rglob("content.txt")
        for file in files:
            filepath = str(file)
            SAYF(f"========== [driver: {driver} / spec: {filepath}]  ==========\n")
            cfg = gen_iden_config(driver, filepath, corpus)
            outdir = cfg["output"]
            # If the output directory already exists, skip it so we can resume the last run
            if os.path.exists(outdir):
                WARNF(f"Output directory {outdir} already exists, skipping...")
                continue
            perf_iden(cfg)
    if len(args.email) > 0:  # Send email notification if email is provided
        subject = "myfuzz MR Identification Completed"
        body = "Hi,\n\n"
        body += "The MR identification experiment is completed.\n\n"
        body += "Best regards,\nmyfuzz Experiment Runner"
        send_email(subject, body, args.email)
        OKF("Successfully send email notification to " + args.email)
    OKF("We're done here!")


def duplicate(src: str) -> str:
    """Duplicate a directory to /tmp with a random suffix.

    Returns
    -------
    str
        Path to the duplicated directory
    """
    basename = Path(src).name
    dst = Path("/tmp") / f"{basename}-{uuid.uuid4().hex[:8]}"
    shutil.copytree(src, dst, ignore=None)
    syzkaller = str(dst)
    return syzkaller


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
            time.sleep(t)


def impl(args: argparse.Namespace):
    """Run MR implementation experiment.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    # Traverse each file under args.path, read mr_final.md and generate code
    idendir = os.path.abspath(args.idendir)
    files = Path(idendir).rglob("mr_final.md")

    # We previously let users specify the path to syzkaller, but this was too
    # error-prone in concurrent scenarios. Therefore, we copied our syzkaller
    # repository to /tmp and added a unique suffix, which will be used for
    # implementation feedback.
    syzkaller = duplicate(args.syzkaller)

    for file in files:
        root = file.parent
        filepath = str(file)
        SAYF(f"========== [MR: {root} / syzkaller: {syzkaller}]  ==========\n")
        cfg = gen_impl_config(filepath, syzkaller)
        outdir = cfg["output"]
        # If the output directory already exists, skip it so we can resume the last run
        if os.path.exists(outdir):
            WARNF(f"Output directory {outdir} already exists, skipping...")
            continue
        perf_impl(cfg)
    if len(args.email) > 0:  # Send email notification if email is provided
        subject = "myfuzz MR Implementation Completed"
        body = "Hi,\n\n"
        body += "The MR Implementation experiment is completed.\n\n"
        body += "Best regards,\nmyfuzz Experiment Runner"
        send_email(subject, body, args.email)
        OKF("Successfully send email notification to " + args.email)
    shutil.rmtree(syzkaller)  # Remove the temporary syzkaller directory
    OKF("We're done here!")


def perf_eval(args: argparse.Namespace):
    """Perform MR evaluation.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    retry = 3
    while retry > 0:
        try:
            MREval.main(args)
            break
        except BaseException as e:
            retry -= 1
            if retry == 0:
                FATAL(f"MR evaluation failed after {retry} attempts: {e}")
            t = random.randint(30, 60)
            WARNF(f"MR evaluation failed: {e}")
            WARNF(f"Have a break for {t} seconds ... ({retry} attempts left)")
            time.sleep(t)


def eval(args: argparse.Namespace):
    """Run MR evaluation experiment.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    root_path = os.path.abspath(args.impldir)
    kernel_obj = os.path.abspath(args.kernel_obj)
    syzkaller = duplicate(args.syzkaller)
    image_obj = os.path.abspath(args.image_obj)
    timeout = args.timeout
    mrs = Path(root_path).rglob("mr.h")
    for mr in mrs:
        dp = mr.parent
        if (dp / ".eval").exists():
            WARNF(f"Evaluation mark file already exists in {dp}, skipping...")
            continue
        SAYF(f"========== [MR: {mr}] ==========\n")
        csource = dp / "mr.h"
        syzlang = dp / "syzlang.txt"
        subargs = argparse.Namespace(
            syzkaller=syzkaller,
            csource=csource,
            syzlang=syzlang,
            kernel_obj=kernel_obj,
            image_obj=image_obj,
            patch=str(Path(__file__).parent.parent / "patch" / "release.patch"),
            timeout=timeout,
        )
        perf_eval(subargs)
    if len(args.email) > 0:  # Send email notification if email is provided
        subject = "myfuzz MR Evaluation Completed"
        body = "Hi,\n\n"
        body += "The MR Evaluation experiment is completed.\n\n"
        body += "Best regards,\nmyfuzz Experiment Runner"
        send_email(subject, body, args.email)
        OKF("Successfully send email notification to " + args.email)
    shutil.rmtree(syzkaller)  # Remove the temporary syzkaller directory
    OKF("We're done here!")


def integrate(args: argparse.Namespace):
    """Integrate MRs to syzkaller

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    impl_root = os.path.abspath(args.impl_root)
    syzkaller = os.path.abspath(args.syzkaller)
    ACTF(f"Going to traverse the {impl_root} and integrate MRs into {syzkaller} ...")
    headers = list(Path(impl_root).glob("**/mr.h"))
    paths = [str(header.parent) for header in headers]

    # Make sure the syzkaller directory is clean and commit is 4b25d554
    if not os.path.exists(syzkaller):
        FATAL(f"Syzkaller directory {syzkaller} does not exist, please check the path.")
    if get_commit(syzkaller)[:8] != "4b25d554":
        FATAL(f"Current commit of syzkaller is {get_commit(syzkaller)[:8]}, but expected 4b25d554. Please checkout first.")
    repo = Repo(syzkaller)
    if repo.is_dirty(untracked_files=True):
        if args.clean:
            ACTF("Cleaning syzkaller directory ...")
            clean_repo(syzkaller)
        else:
            FATAL("Syzkaller directory is dirty, please clean it first or use --clean option.")

    # Filter low-quality implementations
    impls = list()
    for path in paths:
        evmk = os.path.join(path, ".eval")
        lqmk = os.path.join(path, ".low_quality")
        if not args.allin and (not os.path.exists(evmk) or os.path.exists(lqmk)):
                continue
        impls.append(path)

    # Integrate to syzkaller
    subargs = argparse.Namespace(
        syzkaller=syzkaller,
        impls=impls,
        patch=(Path(__file__).parent.parent / "patch" / "release.patch").as_posix(),
    )
    MRIntg.main(subargs)
    OKF("We're done here!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="myfuzz Experiment Runner")
    parser.add_argument("--email", type=str, default="", help="Email address to receive notifications")

    subparser = parser.add_subparsers(title="experiment", required=True)

    # Subparser for MR identification
    iden_parser = subparser.add_parser("iden", help="Run MR identification")
    iden_parser.add_argument("--specdir", type=str, required=True, help="Specification directory")
    iden_parser.add_argument("--corpus", type=str, default=None, help="Corpus directory")
    iden_parser.set_defaults(func=iden)

    # Subparser for MR implementation
    impl_parser = subparser.add_parser("impl", help="Run MR implementation")
    impl_parser.add_argument("--idendir", type=str, required=True, help="Root directory of identification result")
    impl_parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory")
    impl_parser.set_defaults(func=impl)

    # Subparer for MR evaluation
    linux_eval_parser = subparser.add_parser("eval", help="Run MR evaluation")
    linux_eval_parser.add_argument("--impldir", type=str, required=True, help="Path to the root directory of pseudo-syscall")
    linux_eval_parser.add_argument("--kernel_obj", type=str, required=True, help="Path to the kernel object directory")
    linux_eval_parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory, program will duplicate it so dont worry about concurrent issues.")
    linux_eval_parser.add_argument("--image_obj", type=str, required=True, help="Path to the image object directory")
    linux_eval_parser.add_argument("--timeout", type=int, default=120, help="Timeout for a single evaluation (seconds)")
    linux_eval_parser.set_defaults(func=eval)

    # Subparser for MR integration
    integrate_parser = subparser.add_parser("integrate", help="Integrate MR implementation into syzkaller")
    integrate_parser.add_argument("--syzkaller", type=str, required=True, help="Path to the syzkaller directory, program will duplicate it so dont worry about concurrent issues.")
    integrate_parser.add_argument("--impl_root", type=str, required=True, help="Path to the root directory of MR implementation")
    integrate_parser.add_argument("--clean", action="store_true", help="Whether to clean syzkaller directory")
    integrate_parser.add_argument("--allin", action="store_true", help="Whether to integrate all implementations, including low-quality ones")
    integrate_parser.set_defaults(func=integrate)

    load_dotenv()
    args = parser.parse_args()
    try:
        args.func(args)
    except BaseException as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
        error_message = "".join(tb)
        if len(args.email) > 0:  # Send email notification if email is provided
            subject = "myfuzz Experiment Error"
            body = "Hi,\n\n"
            body += "An error occurred during the experiment:\n\n"
            body += error_message + "\n\n"
            body += "Program args: " + " ".join(sys.argv) + "\n\n"
            body += "Best regards,\nmyfuzz Experiment Runner"
            send_email(subject, body, args.email)
            OKF("Successfully send email notification to " + args.email)
        else:
            FATAL(f"An error occurred: {error_message}")
