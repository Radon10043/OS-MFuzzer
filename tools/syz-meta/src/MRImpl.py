"""
Author       : Radon
Date         : 2025-02-12 21:30:59
LastEditors  : Radon
LastEditTime : 2025-05-05 18:00:49
Description  : 提示LLM用C语言实现指定的MR
"""

import argparse
import os
import json
import shutil
import subprocess

from typing import Tuple
from clang.cindex import Config, CursorKind, Index
from utils import *
from wrappers.openai import OpenAI
from wrappers.anthropic import Anthropic
from wrappers.googleai import GoogleAI


def check_config(args: argparse.Namespace):
    """检查命令行参数是否合法, 并读取配置文件

    Parameters
    ----------
    args : argparse.Namespace
        命令行参数集
    """
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        FATAL(f"File not found: {args.config}")

    # 读取配置文件
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    # 检查存储MR描述的文件是否存在
    if not os.path.exists(config["mr_desc"]):
        FATAL(f"File not found: {config["mr_desc"]}")

    # 检查指定的编译器是否存在
    compiler = config["compiler"]
    res = subprocess.run([compiler, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        FATAL(f"Compiler not found: {compiler}")

    # 检查输出目录是否存在, 如果存在则报错, 提示用户需要先删掉该目录
    out_dir = config["output"]
    shutil.rmtree(out_dir, ignore_errors=True)  # NOTE: Just for testing ...
    if os.path.exists(out_dir):
        FATAL(f"Output directory already exists: {out_dir}, please remove it first.")
    os.makedirs(config["output"])

    # 将用户的输入配置文件复制到输出目录下
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


def loop(programmer: OpenAI | Anthropic | GoogleAI, config: dict):
    """迭代地让programmer生成用C语言实现的MR

    Parameters
    ----------
    programmer : OpenAI | Anthropic | GoogleAI
        programmer模型
    config : dict
        配置文件
    """
    gen_success = False  # 代码生成成功标志
    index = 0  # 提示词下标
    iterations = 0  # 迭代次数
    sys_prompt = str()  # 系统提示信息
    usr_prompts = list()  # 用户提示列表
    err_msgs = str()  # 编译器报告的错误信息
    mr_desc = str()  # MR的描述
    mr_code = str()  # 实现MR的C代码
    agent = "programmer"  # 代理名称
    model = config[agent]["model"]  # 模型名称
    syzkaller_dir = config["syzkaller"]  # syzkaller路径
    params = list()  # C代码中syz_mr的参数列表
    syzlang_desc = ""  # C代码对应的syzlang描述, 只是为了可以混过去
    func_name = "syz_mr"  # pseudo-syscall的函数名称
    identifier = "unknown"  # 识别MR的模型名称, 在mr_final.md中应该有记
    calibrator = "unknown"  # 校对MR的模型名称, 在mr_final.md中应该有记
    iden_iter = "unknown"  # 识别MR的迭代次数, 在mr_final.md中应该有记

    # 设置系统提示信息
    fn = config[agent]["prompts"]["system"]
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    programmer.set_sys_prompt(sys_prompt)

    # 读取包含MR自然语言描述的markdown文件
    md_text = str()
    with open(config["mr_desc"], "r", encoding="utf-8") as f:
        md_text = f.read()

    # 读取所有用户提示, 存入usr_prompts中
    for fn in config[agent]["prompts"]["user"]:
        with open(fn, "r", encoding="utf-8") as f:
            usr_prompts.append(f.read())

    # 从markdown文本中提取MR的描述, MR的描述需要放入markdown或md代码块中才能成功提取, 对应了前一步MR识别与校对的最终输出
    mr_desc = get_first_code_block(md_text, {"markdown", "md"})

    # 从markdown文本中提取identifier和calibrator的模型名称, 如果没有默认为unknown
    for line in md_text.split("\n"):
        content = line.upper()
        if content.startswith("IDENTIFIER: "):
            identifier = content.split(": ")[1].strip()
        elif content.startswith("CALIBRATOR: "):
            calibrator = content.split(": ")[1].strip()
        elif content.startswith("ITERATIONS: "):
            iden_iter = content.split(": ")[1].strip()

    # 如果没有找到MR描述, 报错退出
    if len(mr_desc) == 0:
        FATAL(f"No MR description found in the {config["mr_desc"]}!")

    # 进行多轮对话, 持续迭代, 直到MR对应的代码成功生成并编译不报错, 或者达到最大迭代次数
    while not gen_success and iterations < config["max_iter"]:
        prompt = usr_prompts[index]
        prompt = prompt.replace("[MR rendered in markdown]", mr_desc)
        prompt = prompt.replace("[Errors reported by syzkaller]", err_msgs)

        # 与programmer模型进行对话, 生成MR的C代码
        ACTF(f"Iter {iterations + 1}: Prompting {model} to generate C code implementation of MR ...")
        response = programmer.chat(prompt)
        mr_code = get_first_code_block(response, {"c"})
        mr_code = mr_code.lstrip("`c\n").rstrip("`\n")

        # 如果生成的C代码为空, 认为生成失败
        if len(mr_code) == 0:
            FATAL(f"{model} generated empty C code implementation of MR.")

        # 获取syz_mr的参数, 由于pseudo-syscall的返回类型固定是long且static, 参数类型固定都是violatile long,
        # 所以我们可以手动构造syzlang description
        params = get_params(mr_code, func_name, input_file=False)
        syzlang_desc = func_name + "(" + ", ".join([f"{param} int32" for param in params]) + ")"

        # 尝试将生成的C代码作为pseudo-syscall插入syzkaller中, 并构建syzkaller
        ACTF("Integrating pseudo-syscall into syzkaller ...")
        ret_code, stderr, stdout = add_pseudo_syscall(syzkaller_dir, mr_code, syzlang_desc, func_name)
        if ret_code == 0:  # 如果编译成功, 跳出循环
            gen_success = True
            break

        # 记录错误信息
        err_msgs = stderr + "\n\n" + stdout

        # 更新迭代次数和提示词下标
        WARNF(f"Oops, some errors occured during C program building, try to prompt {model} to fix it.")
        iterations += 1
        if index < len(usr_prompts) - 1:
            index += 1

    # 保存交互记录
    programmer.save_messages(os.path.join(config["output"], f"messages.json"))
    programmer.save_messages(os.path.join(config["output"], f"messages.md"))

    # 如果代码未生成成功, 报错
    if not gen_success:
        FATAL(f"Failed to generate C code implementation of MR after {iterations + 1} iterations.")

    # 将MR的描述(作为头部注释)和LLM生成的C代码写入文件
    with open(os.path.join(config["output"], "mr.h"), "w", encoding="utf-8") as f:
        header_comments = mr_desc
        header_comments = header_comments.lstrip("`markdown\n").rstrip("`\n")
        header_comments = header_comments.replace("\n", "\n// ")
        header_comments += f"// MR identified by {identifier} and calibrated by {calibrator} after {iden_iter} iterations\n" + header_comments
        header_comments = f"// Code generated by {model} after {iterations + 1} iterations\n// " + header_comments
        f.write(header_comments)
        f.write(mr_code)

    # 将syzlang描述写入文件
    with open(os.path.join(config["output"], "syzlang.txt"), "w", encoding="utf-8") as f:
        f.write(syzlang_desc)

    OKF(f"Successfully generated C code implementation & syzlang description of MR after {iterations + 1} iterations.")


def add_pseudo_syscall(syzkaller: str, csource: str, syzlang_desc: str, func: str) -> Tuple[int, str, str]:
    """尝试将pseudo-syscall集成到syzkaller中, 包括:
    - C代码实现插入syzkaller/executor/common_linux.h;
    - 在syzkaller/sys/linux下新建metamorphic.txt, 写入syzlang描述;
    - 修改syzkaller/pkg/vminfo/linux_syscalls.go, 添加对应的syscall.

    Parameters
    ----------
    syzkaller : str
        syzkaller的路径
    csource : str
        pseudo-syscall的C代码实现
    syzlang_desc : str
        pseudo-syscall对应的syzlang描述
    func : str
        pseudo-syscall的函数名称

    Returns
    -------
    Tuple[int, str, str]
        集成后的返回值, stderr和stdout
    """
    linux_syscall_file = os.path.join(syzkaller, "pkg", "vminfo", "linux_syscalls.go")  # linux_syscall.go的路径
    linux_syscall_content = str()  # linux_syscall.go的文件内容
    common_linux_file = os.path.join(syzkaller, "executor", "common_linux.h")  # common_linux.h的路径

    # 准备尝试集成到syzkaller, 首先删掉所有syzkaller的修改
    res = subprocess.run(
        "git checkout . && git clean -fd",
        cwd=syzkaller,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if res.returncode != 0:
        FATAL(f"Failed to clean syzkaller repository: {res.stderr.decode('utf-8')}")

    # 将C代码实现, syzlang描述加入syzkaller的指定文件中
    # 还需要在pkg/vminfo/linux_syscalls.go中添加对应的syscall
    syzlang_fn = os.path.join(syzkaller, "sys", "linux", "metamorphic.txt")
    with open(syzlang_fn, "w", encoding="utf-8") as f:
        f.write(syzlang_desc)
    with open(linux_syscall_file, "r", encoding="utf-8") as f:
        linux_syscall_content = f.readlines()
    with open(linux_syscall_file, "w", encoding="utf-8") as f:
        linux_syscall_content[104] += f'"{func}": alwaysSupported,'
        f.writelines(linux_syscall_content)
    with open(common_linux_file, "a", encoding="utf-8") as f:
        f.write("#if SYZ_EXECUTOR || __NR_syz_mr\n")
        f.write(csource)
        f.write("\n#endif\n")

    # 运行make generate -j
    res = subprocess.run(
        ["make", "generate", "-j"],
        cwd=syzkaller,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if res.returncode != 0:
        return res.returncode, res.stderr.decode("utf-8"), res.stdout.decode("utf-8")

    # 运行make clean all -j
    res = subprocess.run(
        ["make", "clean", "all", "-j"],
        cwd=syzkaller,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return res.returncode, res.stderr.decode("utf-8"), res.stdout.decode("utf-8")


def main(config: dict):
    """主函数, 初始化programmer, 迭代地让模型生成用C语言实现的蜕变关系,
    由于pseudo-syscall的返回类型和参数类型都比较固定, 所以基于规则生成对应的syzlang描述

    Parameters
    ----------
    config : dict
        用户输入的配置信息
    """
    agent = "programmer"  # 代理名称

    text = f"*   MR description: {config["mr_desc"]}   *"
    width = len(text)
    SAYF("*" * width + "\n" + "*  " + " " * (width - 6) + "  *\n" + text + "\n" + "*  " + " " * (width - 6) + "  *\n" + "*" * width + "\n")

    # 检查代理是否存在
    if agent not in config.keys():
        FATAL(f'Key "{agent}" not found in config file!')

    # 检查配置文件中是否包含temperature字段, 如果没有则使用默认值0.5
    if "temperature" not in config[agent].keys():
        WARNF(f'Key "temperature" not found in config of {agent}, using default value: 0.5')
        config["temperature"] = 0.5

    # 检查配置文件中是否包含stream字段, 如果没有则使用默认值False
    if "stream" not in config[agent].keys():
        WARNF(f'Key "stream" not found in config of {agent}, using default value: False')
        config["stream"] = False

    # 根据配置文件中的framework字段的值选择对应的框架初始化函数
    setup_func_dict = {
        "openai": setup_openai,
        "anthropic": setup_anthropic,
        "googleai": setup_googleai,
    }

    # 初始化programmer, 该模型用于将MR的自然语言描述转换为C语言实现
    ACTF("Initializing programmer ...")
    framework = config[agent]["framework"].lower()
    if framework not in setup_func_dict:
        FATAL(f"Unsupported framework: {framework}, Supported frameworks: {setup_func_dict.keys()}")
    programmer = setup_func_dict[framework](config[agent])
    OKF(f"Programmer model ({config[agent]["model"]}) successfully initialized!.")

    # 让programmer模型迭代地生成用C语言实现的MR
    ACTF("Generating C code implementation of MR ...")
    loop(programmer, config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration file")
    args = parser.parse_args()

    # 检查配置是否合法
    ACTF("Checking arguments ...")
    check_config(args)
    OKF("Arguments are valid.")

    # 读取配置文件, 创建输出文件夹
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    main(config)
