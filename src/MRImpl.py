"""
Author       : Radon
Date         : 2025-02-12 21:30:59
LastEditors  : Radon
LastEditTime : 2025-08-01 10:16:18
Description  : 提示LLM用C语言实现指定的MR
"""

import argparse
import json
import os
import shutil
import subprocess

from clang.cindex import Config, CursorKind, Index

from utils import *
from wrappers.anthropic import Anthropic
from wrappers.googleai import GoogleAI
from wrappers.openai import OpenAI


def check_args(args: argparse.Namespace):
    """Check validity of command line arguments

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    """
    # Check if config file exists
    if not os.path.exists(args.config):
        FATAL(f"File not found: {args.config}")

    # Read config file
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    # Check if config file contains required keys
    if not os.path.exists(config["mr_desc"]):
        FATAL(f"File not found: {config['mr_desc']}")

    # Check if compiler exists
    compiler = config["compiler"]
    res = subprocess.run([compiler, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        FATAL(f"Compiler not found: {compiler}")

    # Check if output directory exists, if it does, prompt user to remove it
    out_dir = config["output"]
    shutil.rmtree(out_dir, ignore_errors=True)  # NOTE: Just for testing ...
    if os.path.exists(out_dir):
        FATAL(f"Output directory already exists: {out_dir}, please remove it first.")

    # Check if syzkaller directory exists
    syzkaller = config["syzkaller"]
    if not os.path.exists(syzkaller):
        FATAL(f"Syzkaller directory not found: {syzkaller}")

    # Copy config file to output directory
    # TODO: This may leak sensitive information, should be removed in the future
    shutil.copy(args.config, os.path.join(out_dir, "config.json"))


def setup_openai(config: dict) -> OpenAI:
    """初始化以OpenAI为框架的聊天对象, 主要是GPT, DeepSeek等模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    OpenAI
        封装的以OpenAI为框架的聊天对象
    """
    # 初始化OpenAI聊天对象
    openai_obj = OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
        stream=config["stream"],
    )

    # 返回初始化后的OpenAI对象
    return openai_obj


def setup_anthropic(config: dict) -> Anthropic:
    """初始化以Anthropic为框架的聊天对象, 主要是Claude等系列模型

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    Anthropic
        封装的以Anthropic为框架的聊天对象
    """
    # 初始化Anthropic聊天对象
    anthropic_obj = Anthropic(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
        stream=config["stream"],
    )

    # 返回初始化后的Anthropic对象
    return anthropic_obj


def setup_googleai(config: dict) -> GoogleAI:
    """初始化以GooelAI为框架的聊天对象, 主要是Gemini等模型
    官方库的名称是google.genai

    Parameters
    ----------
    config : dict
        用户输入的配置信息

    Returns
    -------
    GoogleAI
        Gemini模型
    """
    # 初始化Gemini模型
    googleai_obj = GoogleAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=config["temperature"],
        stream=config["stream"],
    )

    # 返回初始化后的GoogleAI对象
    return googleai_obj


def get_params(input: str, func: str, input_file: bool = True) -> list:
    """从C代码中提取指定函数的形参列表, 仅包含形参名称

    Parameters
    ----------
    input : str
        C代码或C代码文件路径
    func : str
        _description_
    input_file : bool, optional
        True表示input是文件路径, 否则表示代码内容, by default True

    Returns
    -------
    list
        形参名称列表
    """
    params = list()  # 函数的形参列表

    # 加载libclang.so
    if not Config.loaded:
        libclang_path = subprocess.run("llvm-config --libdir", shell=True, stdout=subprocess.PIPE).stdout.decode().strip()
        Config.set_library_path(libclang_path)

    # 分析获得C代码的AST
    index = Index.create()
    tu = None
    if input_file:
        tu = index.parse(input)
    else:
        tu = index.parse("fake.c", unsaved_files=[("fake.c", input)])
    cursor = tu.cursor

    # 遍历AST, 获得参数列表
    for child in cursor.get_children():
        if child.location.is_in_system_header:  # 跳过系统头文件
            continue
        if child.kind == CursorKind.FUNCTION_DECL and child.spelling == func:
            # 遍历函数参数
            for param in child.get_arguments():
                params.append(f"{param.spelling}")
            break

    return params


def generate_c(c_pgmr: OpenAI | Anthropic | GoogleAI, mr_desc: str, config: dict) -> Tuple[bool, str, int]:
    # Get user prompts
    c_prompts = list()
    for fn in config["c"]["prompts"]["user"]:
        c_prompts.append(Path(fn).read_text(encoding="utf-8"))

    # Chating iteratively, until stop condition is satisfied
    gen_succ = False
    cm = config["c"]["model"]  # C code generation model
    err_msgs = str()  # Errors reported by compiler
    iter = 0
    mr_code = str()
    while not gen_succ and iter < config["max_iter"]:
        # Prompt C programmer to generate C code implementation of MR
        cp = c_prompts[min(iter, len(c_prompts) - 1)]  # C code generation prompt
        cp = cp.replace("[MR rendered in markdown]", mr_desc)
        cp = cp.replace("[Errors reported by syzkaller]", err_msgs)
        ACTF(f"Iter {iter + 1}: Prompting {cm} to generate C code implementation of MR ...")
        response = c_pgmr.chat(cp)
        mr_code = get_first_code_block(response, {"c"})
        mr_code = mr_code.lstrip("`c\n").rstrip("`\n")

        # In some cases, llm may failed to generate code
        if len(mr_code) == 0:
            FATAL(f"{cm} generated empty C code implementation of MR.")

        # We first use a fake desc to verify whether the generated C code is valid
        ACTF("Integrating pseudo-syscall into syzkaller ...")
        func = "syz_mr"
        params = get_params(mr_code, func, input_file=False)
        fake_desc = func + "(" + ", ".join([f"{param} int32" for param in params]) + ")"
        syzkaller = config["syzkaller"]
        clean_syzkaller(syzkaller)
        add_pseudo_syscall(syzkaller, mr_code, fake_desc, func)
        ret_code, stderr, stdout = build_syzkaller(syzkaller)
        if ret_code == 0:
            gen_succ = True
            break

        # Update error messages and retry
        err_msgs = stderr + "\n\n" + stdout
        WARNF(f"Oops, some errors occured during C program building, try to prompt {cm} to regenerate.")
        iter += 1

    return gen_succ, mr_code, iter + 1


def generate_syz(syz_pgmr: OpenAI | Anthropic | GoogleAI, csource: str, config: dict) -> Tuple[bool, str, int]:
    syz_prompts = list()  # Syzlang description generation prompts
    for fn in config["syzlang"]["prompts"]["user"]:
        syz_prompts.append(Path(fn).read_text(encoding="utf-8"))

    # Preprocessing
    gen_succ = False
    iter = 0
    syz_desc = str()
    sm = config["syzlang"]["model"]
    err_msgs = str()

    # Chating iteratively, until stop condition is satisfied
    while not gen_succ and iter < config["max_iter"]:
        # Prompt Syzlang programmer to generate Syzlang description
        ACTF(f"Iter {iter + 1}: Prompting {sm} to generate Syzlang description ...")
        sp = syz_prompts[min(iter, len(syz_prompts) - 1)]  # Syzlang description prompt
        sp = sp.replace("[MR code]", csource)
        sp = sp.replace("[Errors reported by syzkaller]", err_msgs)
        response = syz_pgmr.chat(sp)
        syz_desc = get_first_code_block(response, {"syzlang", "syz"})
        syz_desc = syz_desc.removeprefix("```syz\n").rstrip("\n`")

        # In some cases, llm may failed to generate description
        if len(syz_desc) == 0:
            FATAL(f"{sm} generated empty Syzlang description.")

        # Integrated to syzkaller to verify
        ACTF("Integrating pseudo-syscall into syzkaller ...")
        func = "syz_mr"
        syzkaller = config["syzkaller"]
        clean_syzkaller(syzkaller)
        add_pseudo_syscall(syzkaller, csource, syz_desc, func)
        ret_code, stderr, stdout = build_syzkaller(syzkaller)

        if ret_code == 0:
            gen_succ = True
            break

        # Update error messages and retry
        err_msgs = stderr + "\n\n" + stdout
        WARNF(f"Oops, some errors occured during C program building, try to prompt {sm} to regenerate.")
        iter += 1

    return gen_succ, syz_desc, iter + 1


def generate(c_pgmr: OpenAI | Anthropic | GoogleAI, syz_pgmr: OpenAI | Anthropic | GoogleAI, config: dict):
    """Prompt programmer to generate C code implementation of MR, as well as
    the corresponding syzlang description.

    Parameters
    ----------
    c_pgmr : OpenAI | Anthropic | GoogleAI
        llm wrapper object, for c code generation
    syz_pgmr : OpenAI | Anthropic | GoogleAI
        llm wrapper object, for syzlang description generation
    config : dict
        Configuration
    """
    # Set system prompt for llms
    fn = config["c"]["prompts"]["system"]
    sys_prompt = Path(fn).read_text(encoding="utf-8")
    c_pgmr.set_sys_prompt(sys_prompt)
    fn = config["syzlang"]["prompts"]["system"]
    sys_prompt = Path(fn).read_text(encoding="utf-8")
    syz_pgmr.set_sys_prompt(sys_prompt)

    # Read MR description
    md_text = Path(config["mr_desc"]).read_text(encoding="utf-8")
    mr_desc = get_first_code_block(md_text, {"markdown", "md"})

    syzlang_prompts = list()  # Syzlang description generation prompts
    for fn in config["syzlang"]["prompts"]["user"]:
        syzlang_prompts.append(Path(fn).read_text(encoding="utf-8"))

    # Extract identifier and calibrator model names from markdown text, default to unknown if not found
    identifier, calibrator, iden_iter = "unknown", "unknown", "unknown"
    for line in md_text.split("\n"):
        content = line.upper()
        if content.startswith("IDENTIFIER: "):
            identifier = content.split(": ")[1].strip().lower()
        elif content.startswith("CALIBRATOR: "):
            calibrator = content.split(": ")[1].strip().lower()
        elif content.startswith("ITERATIONS: "):
            iden_iter = content.split(": ")[1].strip()

    # Generate C code & save chat messages
    # TODO: May be we should set max_iter for C code generation & syzlang description generation respectively
    os.makedirs(config["output"])
    gen_succ, mr_code, c_iter = generate_c(c_pgmr, mr_desc, config)
    c_pgmr.save_messages(os.path.join(config["output"], "c_messages.json"))
    c_pgmr.save_messages(os.path.join(config["output"], "c_messages.md"))
    if not gen_succ:
        FATAL(f"Failed to generate C code implementation of MR after {config['max_iter']} iterations.")
    OKF(f"Successfully generated C code implementation of MR after {c_iter} iteration.")

    # Chating iteratively to generate syzlang description
    gen_succ, syz_desc, syz_iter = generate_syz(syz_pgmr, mr_code, config)
    syz_pgmr.save_messages(os.path.join(config["output"], "syzlang_messages.json"))
    syz_pgmr.save_messages(os.path.join(config["output"], "syzlang_messages.md"))
    if not gen_succ:
        FATAL(f"Failed to generate syzlang description of MR after {config['max_iter']} iterations.")
    OKF(f"Successfully generated syzlang description of MR after {syz_iter} iterations.")

    # Save C code implementation & syzlang description
    cm = config["c"]["model"]
    sm = config["c"]["model"]
    c_comments = mr_desc
    c_comments = c_comments.lstrip("`markdown\n").rstrip("`\n")
    c_comments = "// " + c_comments.replace("\n", "\n// ") + "\n\n"
    c_comments = f"// MR identified by {identifier} and calibrated by {calibrator} after {iden_iter} iterations\n" + c_comments
    c_comments = f"// Code generated by {cm} after {c_iter} iterations\n" + c_comments
    Path(os.path.join(config["output"], "mr.h")).write_text(c_comments + "\n" + mr_code, encoding="utf-8")
    syz_comments = f"# Syzlang description generated by {sm} after {syz_iter} iterations\n"
    Path(os.path.join(config["output"], "syzlang.txt")).write_text(syz_comments + syz_desc, encoding="utf-8")
    OKF("We're done here!")


def main(config: dict):
    """Main function, initialize c programmer & syzlang programmer, prompt
    them to generate encoded MR and corresponding syzlang description.

    Parameters
    ----------
    config : dict
        User-provided configuration information
    """
    # Preprocessing configs
    langs = ["c", "syzlang"]
    for lang in langs:
        if not lang in config.keys():
            FATAL(f'Key "{lang}" not found in config file!')
        if "temperature" not in config[lang].keys():
            WARNF(f'Key "temperature" not found in config of {lang}, using default value: 0.5')
            config[lang]["temperature"] = 0.5
        if "stream" not in config[lang].keys():
            WARNF(f'Key "stream" not found in config of {lang}, using default value: False')
            config[lang]["stream"] = False

    # Mapping setup functions for different frameworks
    setup_func_dict = {
        "openai": setup_openai,
        "anthropic": setup_anthropic,
        "googleai": setup_googleai,
    }

    # Initialize c programmer & syzlang programmer, the former is used to
    # generate C code implementation of MR, the latter is used to generate
    # corresponding syzlang description.
    ACTF("Initializing c programmer & syzlang programmer ...")
    framework = config["c"]["framework"].lower()
    if framework not in setup_func_dict:
        FATAL(f"Unsupported framework: {framework}, Supported frameworks: {setup_func_dict.keys()}")
    c_pgmr = setup_func_dict[framework](config["c"])
    framework = config["syzlang"]["framework"].lower()
    if framework not in setup_func_dict:
        FATAL(f"Unsupported framework: {framework}, Supported frameworks: {setup_func_dict.keys()}")
    syz_pgmr = setup_func_dict[framework](config["syzlang"])
    OKF(f"Programmer model ({config['syzlang']['model']}) successfully initialized!.")

    # Prompt llms to generate C code & syzlang description
    ACTF("Generating C code implementation of MR ...")
    generate(c_pgmr, syz_pgmr, config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration file")
    args = parser.parse_args()

    # Check whether argument is valid
    ACTF("Checking arguments ...")
    check_args(args)
    OKF("Arguments are valid.")

    # Read config file
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    main(config)
