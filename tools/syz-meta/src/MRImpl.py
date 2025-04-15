"""
Author       : Radon
Date         : 2025-02-12 21:30:59
LastEditors  : Radon
LastEditTime : 2025-04-15 07:25:15
Description  : 提示LLM用C语言实现指定的MR
"""

import argparse
import os
import json
import shutil
import subprocess

from typing import Tuple
from clang.cindex import Config, Cursor, CursorKind, StorageClass, Index
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

    # 检查存储MRC(MR候选)描述的文件是否存在
    if not os.path.exists(config["mrc_desc"]):
        FATAL(f"File not found: {config["mrc_desc"]}")

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


def build_c_program(code: str, compiler: str) -> Tuple[int, str]:
    """编译构建C代码

    Parameters
    ----------
    code : str
        C代码
    compiler : str
        编译器
    cflags : str
        编译选项

    Returns
    -------
    Tuple[int, str]
        返回值和错误信息
    """
    # 将C代码写入临时文件并进行编译, 返回编译结果和错误信息
    sfn = "/tmp/GQuuuuuuX.c"
    binary = "/tmp/GQuuuuuuX"
    cflags = [  # 基本沿用syzkaller的编译选项, 但为了实现方便, 添加了-Wno-unused-function, 不对未使用的函数做警告
        "-pthread",
        "-Wall",
        "-Werror",
        "-Wparentheses",
        "-Wunused-const-variable",
        "-Wframe-larger-than=16384",
        "-Wno-stringop-overflow",
        "-Wno-array-bounds",
        "-Wno-format-overflow",
        "-Wno-unused-but-set-variable",
        "-Wno-unused-command-line-argument",
        "-Wno-unused-function",
        "-static-pie",
    ]
    with open(sfn, mode="w", encoding="utf-8") as f:
        f.write(code)
    cmd = [compiler, sfn, "-o", binary] + cflags
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode, res.stderr.decode("utf-8")


def gen_csource(programmer: OpenAI | Anthropic | GoogleAI, config: dict):
    """迭代地让programmer生成用C语言实现的MRC

    Parameters
    ----------
    programmer : _type_
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
    mrc_desc = str()  # MRC的描述
    mrc_code = str()  # 实现MRC的C代码
    agent = "c_programmer"  # 代理名称
    model = config[agent]["model"]  # 模型名称

    # 设置系统提示信息
    fn = config[agent]["prompts"]["system"]
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    programmer.set_sys_prompt(sys_prompt)

    # 读取包含MRC自然语言描述的markdown文件
    md_text = str()
    with open(config["mrc_desc"], "r", encoding="utf-8") as f:
        md_text = f.read()

    # 读取所有用户提示, 存入usr_prompts中
    for fn in config[agent]["prompts"]["user"]:
        with open(fn, "r", encoding="utf-8") as f:
            usr_prompts.append(f.read())

    # 从markdown文本中提取MRC的描述, MRC的描述需要放入markdown或md代码块中才能成功提取, 对应了前一步MR识别与校对的最终输出
    mrc_desc = get_first_code_block(md_text, {"markdown", "md"})

    # 如果没有找到MRC描述, 报错退出
    if len(mrc_desc) == 0:
        FATAL(f"No MRC description found in the {config["mrc_desc"]}!")

    # 进行多轮对话, 持续迭代, 直到MRC对应的代码成功生成并编译不报错, 或者达到最大迭代次数
    while not gen_success and iterations < config["max_iter"]:
        prompt = usr_prompts[index]
        prompt = prompt.replace("[MR rendered in markdown]", mrc_desc)
        prompt = prompt.replace("[Errors reported by compiler]", err_msgs)

        # 与programmer模型进行对话, 生成MRC的C代码
        ACTF(f"Iter {iterations + 1}: Prompting {model} to generate C code implementation of MRC ...")
        response = programmer.chat(prompt)
        mrc_code = get_first_code_block(response, {"c"})
        mrc_code = mrc_code.lstrip("```c\n").rstrip("```\n")

        # 如果生成的C代码为空, 认为生成失败
        if len(mrc_code) == 0:
            FATAL(f"{model} generated empty C code implementation of MRC.")

        # 加一段main函数, 里面只有一句return 0, 主要目的是查看LLM生成的代码是否能编译通过
        # 编译构建C代码, 同时获取错误信息
        c_code = f"{mrc_code}\n\nint main() {{ return 0; }}"
        ret_code, err_msgs = build_c_program(c_code, config["compiler"])
        if ret_code == 0:  # 如果编译成功, 跳出循环
            gen_success = True
            break

        # 更新迭代次数和提示词下标
        WARNF(f"Oops, some errors occured during C program building, try to prompt {model} to fix it.")
        iterations += 1
        if index < len(usr_prompts) - 1:
            index += 1

    # 保存交互记录
    programmer.save_messages(os.path.join(config["output"], f"messages.{agent}.json"))
    programmer.save_messages(os.path.join(config["output"], f"messages.{agent}.md"))

    # 如果代码未生成成功, 报错
    if not gen_success:
        FATAL(f"Failed to generate C code implementation of MRC after {iterations} iterations.")

    # 将MRC的描述(作为头部注释)和LLM生成的C代码写入文件
    with open(os.path.join(config["output"], "mrc.h"), "w", encoding="utf-8") as f:
        header_comments = mrc_desc
        header_comments = header_comments.lstrip("```markdown\n").rstrip("```\n")
        header_comments = f"// Code generated by {model}\n// " + header_comments.replace("\n", "\n// ")
        f.write(header_comments)
        f.write(mrc_code)
    OKF(f"Successfully generated C code implementation of MRC after {iterations + 1} iterations.")


def add_pseudo_syscall(syzkaller: str, csource: str, syzlang_desc: str, func: str) -> Tuple[int, str, str]:
    """尝试将pseudo-syscall集成到syzkaller中, 包括:
        - C代码实现插入syzkaller/executor/common_linux.h
        - 在syzkaller/sys/linux下新建metamorphic.txt, 写入syzlang描述
        - 修改syzkaller/pkg/vminfo/linux_syscalls.go, 添加对应的syscall

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
    syz_env = os.path.join(syzkaller, "tools", "syz-env")  # syz-env脚本路径, 构建添加pseudo-syscall后的yzkaller用
    syz_env_content = list()  # syz-env脚本的内容

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

    # 修改syz-env:
    # - 注释掉docker pull (L66), 防止出现网络错误
    # - docker run时添加--network host
    with open(syz_env, mode="r", encoding="utf-8") as f:
        syz_env_content = f.readlines()
    with open(syz_env, mode="w", encoding="utf-8") as f:
        # TODO (radon): 直接通过行号修改也太糟糕了, 想想有什么别的办法吧, 包括下面修改linux_syscall.go也是
        syz_env_content[65] = "# " + syz_env_content[65] + 'DOCKERARGS+=" --network host"\n'
        f.writelines(syz_env_content)

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

    # 运行syz-env make generate -j
    res = subprocess.run(
        [syz_env, "make", "generate", "-j"],
        cwd=syzkaller,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if res.returncode != 0:
        return res.returncode, res.stderr.decode("utf-8"), res.stdout.decode("utf-8")

    # 运行syz-env make clean all -j
    res = subprocess.run(
        [syz_env, "make", "clean", "all", "-j"],
        cwd=syzkaller,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return res.returncode, res.stderr.decode("utf-8"), res.stdout.decode("utf-8")


def gen_syzlang(programmer: OpenAI | Anthropic | GoogleAI, config: dict):
    """生成pseudo-syscall的syzlang描述

    Parameters
    ----------
    programmer : OpenAI | Anthropic | GoogleAI
        生成syzlang描述的模型
    config : dict
        用户输入的配置信息
    """
    gen_success = False  # syzlang描述成功生成的标志
    index = 0  # 提示词下标
    iterations = 0  # 迭代次数
    sys_prompt = str()  # 系统提示信息
    usr_prompts = list()  # 用户提示列表
    err_msgs = str()  # 与syzkaller集成时报告的错误信息
    syzlang_desc = str()  # syzlang描述
    csource = str()  # C代码
    csource_path = os.path.join(config["output"], "mrc.h")  # C代码路径
    target_func = "syz_mr"  # 要获取声明的函数名称
    syzkaller_dir = config["syzkaller"]  # syzkaller的路径
    agent = "syzlang_programmer"  # 代理名称
    model = config[agent]["model"]  # 模型名称

    # 读取C代码
    with open(csource_path, "r", encoding="utf-8") as f:
        csource = f.read()

    # 清除syzkaller的修改, 切换到4b25d554版本
    res = subprocess.run(
        "git clean -fd && git checkout 4b25d554",
        cwd=syzkaller_dir,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if res.returncode != 0:
        FATAL(f"Failed to clean syzkaller repository: {res.stderr.decode('utf-8')}")

    # 设置系统提示信息
    fn = config[agent]["prompts"]["system"]
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    programmer.set_sys_prompt(sys_prompt)

    # 读取所有用户提示, 存入usr_prompts中
    for fn in config[agent]["prompts"]["user"]:
        with open(fn, "r", encoding="utf-8") as f:
            usr_prompts.append(f.read())

    # 进行多轮对话, 持续迭代,直到C代码和syzlang可集成到syzkaller
    while not gen_success and iterations < config["max_iter"]:
        prompt = usr_prompts[index]
        prompt = prompt.replace("[C source code]", csource)
        prompt = prompt.replace("[Errors reported by syzkaller]", err_msgs)

        # 与programmer模型进行对话, 生成syzlang描述
        ACTF(f"Iter {iterations + 1}: Prompting {model} to generate syzlang description of MRC ...")
        response = programmer.chat(prompt)
        syzlang_desc = get_first_code_block(response, {"syzlang"})
        syzlang_desc = syzlang_desc.lstrip("`syzlang").rstrip("`\n")

        # 与syzkaller集成
        ACTF("Try to integrated new pseudo-syscall into syzkaller ...")
        ret_code, stderr, stdout = add_pseudo_syscall(syzkaller_dir, csource, syzlang_desc, target_func)
        err_msgs = stderr + "\n\n" + stdout
        if ret_code == 0:  # 如果集成成功, 跳出循环
            gen_success = True
            break

        # 更新迭代次数和提示词下标
        WARNF(f"Oops, some errors occured during integration, try to prompt {model} to fix it.")
        iterations += 1
        if index < len(usr_prompts) - 1:
            index += 1

    # 保存交互记录
    programmer.save_messages(os.path.join(config["output"], "messages.syzlang.json"))
    programmer.save_messages(os.path.join(config["output"], "messages.syzlang.md"))

    # 如果syzlang描述未生成成功, 报错
    if not gen_success:
        FATAL(f"Failed to generate syzlang description of MRC after {iterations} iterations.")

    # 将LLM生成的syzlang描述写入文件
    syzlang_fn = os.path.join(config["output"], "syzlang.txt")
    with open(syzlang_fn, "w", encoding="utf-8") as f:
        header_comments = f"# Code generated by {model}\n"
        f.write(header_comments)
        f.write(syzlang_desc + "\n")
    OKF("Successfully generated syzlang description of MRC.")


def main(args: argparse.Namespace):
    """主函数, 初始化programmer, 迭代地让模型生成用C语言实现的蜕变关系

    Parameters
    ----------
    args : argparse.Namespace
        命令函参数集
    """
    ACTF("Checking arguments ...")
    check_config(args)
    ACTF("Arguments are valid.")

    # 读取配置文件, 创建输出文件夹
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    text = f"*** MR description: {config["mrc_desc"]} ***"
    width = len(text)
    print("*" * width + "\n" + text + "\n" + "*" * width)

    # 检查每个代理的配置
    agents = ["c_programmer", "syzlang_programmer"]
    for agent in agents:
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

    # 初始化c_programmer, 该模型用于将MRC的自然语言描述转换为C语言实现
    ACTF("Initializing c_programmer and syzlang_programmer ...")
    agent = "c_programmer"
    framework = config[agent]["framework"].lower()
    if framework not in setup_func_dict:
        FATAL(f"Unsupported framework: {framework}, Supported frameworks: {setup_func_dict.keys()}")
    c_programmer = setup_func_dict[framework](config[agent])

    # 初始化syzlang_programmer, 该模型用于将c_programmer生成的C语言转换为syzlang描述
    agent = "syzlang_programmer"
    framework = config[agent]["framework"].lower()
    if framework not in setup_func_dict:
        FATAL(f"Unsupported framework: {framework}, Supported frameworks: {setup_func_dict.keys()}")
    syzlang_programmer = setup_func_dict[framework](config[agent])
    OKF("C programmer & syzlang programmer models successfully initialized!.")

    # 让programmer模型迭代地生成用C语言实现的MRC
    ACTF("Generating C code implementation of MRC ...")
    gen_csource(c_programmer, config)

    # 新建另一个programmer, 生成对应的syzlang
    ACTF("Generating syzlang description of MRC ...")
    gen_syzlang(syzlang_programmer, config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration file")
    args = parser.parse_args()
    main(args)
