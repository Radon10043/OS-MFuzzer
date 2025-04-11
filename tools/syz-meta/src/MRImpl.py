"""
Author       : Radon
Date         : 2025-02-12 21:30:59
LastEditors  : Radon
LastEditTime : 2025-04-11 12:59:45
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

    # 检查cflags是否合法
    cflags = config["cflags"]
    ret_code, _ = build_c_program("int main() { return 0; }", compiler, cflags)
    if ret_code != 0:
        FATAL(f"Invalid cflags: {cflags}")

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


def build_c_program(c_code: str, compiler: str, cflags: str) -> Tuple[int, str]:
    """编译构建C代码

    Parameters
    ----------
    c_code : str
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
    with open(sfn, mode="w", encoding="utf-8") as f:
        f.write(c_code)
    cmd = [compiler, sfn, "-o", binary] + cflags.split()
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode, res.stderr.decode("utf-8")


def get_func_decl(file: str, func: str) -> str:
    """从C代码中提取指定函数的声明

    Parameters
    ----------
    file : str
        保存C源码文件的路径
    func : str
        函数名称

    Returns
    -------
    str
        函数声明, 包括返回类型, 函数名称, 参数类型和名称
    """
    libclang_path = subprocess.run("llvm-config --libdir", shell=True, stdout=subprocess.PIPE).stdout.decode().strip()
    Config.set_library_path(libclang_path)
    index = Index.create()
    tu = index.parse(file)
    return traverse_ast(tu.cursor, func)


def traverse_ast(cursor: Cursor, func: str) -> str:
    """遍历AST, 查找指定函数的声明

    Parameters
    ----------
    cursor : Cursor
        当前节点
    func : str
        函数名称

    Returns
    -------
    str
        函数声明, 包括返回类型, 函数名称, 参数类型和名称
        如果存在多个同名函数, 返回第一个找到的函数声明
        如果没有找到函数声明, 返回空字符串
    """
    func_decl = str()
    for child in cursor.get_children():
        if child.location.is_in_system_header:  # 跳过系统头文件
            continue
        if child.kind == CursorKind.FUNCTION_DECL and child.spelling == func:
            # 遍历函数参数
            params = list()
            for param in child.get_arguments():
                params.append(f"{param.type.spelling} {param.spelling}")
            params_fmt = ", ".join(params)
            # 获取函数声明
            if child.storage_class == StorageClass.STATIC:
                func_decl = "static "
            func_decl += f"{child.result_type.spelling} {child.spelling}({params_fmt})"
            break
    return func_decl


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
    usr_prompts = list()  # 用户提示列表
    err_msgs = str()  # 编译器报告的错误信息
    mrc_code = str()  # 实现MRC的C代码

    # 设置系统提示信息
    fn = config["prompts"]["c"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    programmer.set_sys_prompt(sys_prompt)

    # 读取包含MRC自然语言描述的markdown文件
    md_text = str()
    with open(config["mrc_desc"], "r", encoding="utf-8") as f:
        md_text = f.read()

    # 读取所有用户提示, 存入usr_prompts中
    for fn in config["prompts"]["c"]["user"]:
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
        ACTF(f"Iter {iterations + 1}: Prompting {config["model"]} to generate C code implementation of MRC ...")
        response = programmer.chat(prompt)
        mrc_code = get_first_code_block(response, {"c"})
        mrc_code = mrc_code.lstrip("```c\n").rstrip("```\n")

        # 如果生成的C代码为空, 认为生成失败
        if len(mrc_code) == 0:
            FATAL(f"{config["model"]} generated empty C code implementation of MRC.")

        # 加一段main函数, 里面只有一句return 0, 主要目的是查看LLM生成的代码是否能编译通过
        # 编译构建C代码, 同时获取错误信息
        c_code = f"{mrc_code}\n\nint main() {{ return 0; }}"
        ret_code, err_msgs = build_c_program(c_code, config["compiler"], config["cflags"])
        if ret_code == 0:  # 如果编译成功, 跳出循环
            gen_success = True
            break

        # 更新迭代次数和提示词下标
        iterations += 1
        if index < len(usr_prompts) - 1:
            index += 1

    # 如果代码未生成成功, 报错
    if not gen_success:
        FATAL(f"Failed to generate C code implementation of MRC after {iterations} iterations.")

    # 保存交互记录
    programmer.save_messages(os.path.join(config["output"], "messages.c.json"))
    programmer.save_messages(os.path.join(config["output"], "messages.c.md"))

    # 将MRC的描述(作为头部注释)和LLM生成的C代码写入文件
    with open(os.path.join(config["output"], "mrc.h"), "w", encoding="utf-8") as f:
        header_comments = mrc_desc
        header_comments = header_comments.lstrip("```markdown\n").rstrip("```\n")
        header_comments = f"// Code generated by {config["model"]}\n// " + header_comments.replace("\n", "\n// ")
        f.write(header_comments)
        f.write(mrc_code)
    OKF(f"Successfully generated C code implementation of MRC after {iterations + 1} iterations.")


def add_pseudo_syscall(syzkaller: str, csource: str, syzlang_desc: str, func: str) -> Tuple[int, str, str]:
    """_summary_

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
    usr_prompts = list()  # 用户提示列表
    err_msgs = str()  # 与syzkaller集成时报告的错误信息
    syzlang_desc = str()  # syzlang描述
    csource = str()  # C代码
    csource_path = os.path.join(config["output"], "mrc.h")  # C代码路径
    target_func = "syz_mr"  # 要获取声明的函数名称
    func_decl = str()  # 目标函数的声明
    syzkaller_dir = config["syzkaller"]  # syzkaller的路径

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
    fn = config["prompts"]["syzlang"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    programmer.set_sys_prompt(sys_prompt)

    # 读取所有用户提示, 存入usr_prompts中
    for fn in config["prompts"]["syzlang"]["user"]:
        with open(fn, "r", encoding="utf-8") as f:
            usr_prompts.append(f.read())

    # 获取C代码内容以及目标函数的声明
    with open(csource_path, "r", encoding="utf-8") as f:
        csource = f.read()
    func_decl = get_func_decl(csource_path, target_func)

    # 如果函数声明为空, 报错退出
    if len(func_decl) == 0:
        FATAL(f"Function syz_mr cannot be found in {csource_path}")

    # 进行多轮对话, 持续迭代,直到C代码和syzlang可集成到syzkaller
    while not gen_success and iterations < config["max_iter"]:
        prompt = usr_prompts[index]
        prompt = prompt.replace("[Function declaration]", func_decl)
        prompt = prompt.replace("[Errors reported by syzkaller]", err_msgs)

        # 与programmer模型进行对话, 生成syzlang描述
        ACTF(f"Iter {iterations + 1}: Prompting {config["model"]} to generate syzlang description of MRC ...")
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
        WARNF(f"Oops, some errors occured during integration, try to prompt {config["model"]} to fix it.")
        iterations += 1
        if index < len(usr_prompts) - 1:
            index += 1

    # 如果syzlang描述未生成成功, 报错
    if not gen_success:
        FATAL(f"Failed to generate syzlang description of MRC after {iterations} iterations.")

    # 保存交互记录
    programmer.save_messages(os.path.join(config["output"], "messages.syzlang.json"))
    programmer.save_messages(os.path.join(config["output"], "messages.syzlang.md"))

    # 将LLM生成的syzlang描述写入文件
    syzlang_fn = os.path.join(config["output"], "syzlang.txt")
    with open(syzlang_fn, "w", encoding="utf-8") as f:
        header_comments = f"# Code generated by {config["model"]}\n"
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

    # 检查配置文件中是否包含temperature字段, 如果没有则使用默认值0.5
    if "temperature" not in config.keys():
        WARNF('Key "temperature" not found in config file, using default value: 0.5')
        config["temperature"] = 0.5

    # 检查配置文件中是否包含stream字段, 如果没有则使用默认值False
    if "stream" not in config.keys():
        WARNF('Key "stream" not found in config file, using default value: False')
        config["stream"] = False

    # 根据配置文件中的framework字段的值选择对应的框架初始化函数
    setup_func_dict = {
        "openai": setup_openai,
        "anthropic": setup_anthropic,
        "googleai": setup_googleai,
    }

    # 初始化programmer模型, 该模型用于将MRC的自然语言描述转换为C语言实现
    ACTF("Initializing programmer model ...")
    framework = config["framework"].lower()
    if framework not in setup_func_dict:
        FATAL(f"Unsupported model: {framework}, Supported models: {setup_func_dict.keys()}")
    programmer = setup_func_dict[framework](config)
    OKF("Programmer model successfully initialized!.")

    # TODO: 或许可以让LLM同时生成C和syzlang
    # 让programmer模型迭代地生成用C语言实现的MRC
    ACTF("Generating C code implementation of MRC ...")
    gen_csource(programmer, config)

    # 新建一个programmer, 生成对应的syzlang
    programmer = setup_func_dict[framework](config)
    ACTF("Generating syzlang description of MRC ...")
    gen_syzlang(programmer, config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration file")
    args = parser.parse_args()
    main(args)
