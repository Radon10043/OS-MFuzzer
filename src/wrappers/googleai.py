import os
import json

from google import genai
from google.genai import types
from utils import *
from wrappers.wrapper import Wrapper


class GoogleAI(Wrapper):
    """GoogleAI API Client"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.5,
        stream: bool = False,
    ):
        """构造函数, 初始化Gemini对象

        Parameters
        ----------
        base_url : str
            API的基础URL, 调用gemini的话其实用不到这个参数
        api_key : str
            Google genai API Key
        model : str
            要调用的模型
        temperature : float, optional
            温度参数, by default 0.5
        stream : bool, optional
            是否启用流式对话, by default False
        """
        self.model = model  # 设置要调用的模型
        self.base_url = base_url  # 设置API的基础URL
        self.api_key = api_key  # 设置OpenAI API Key
        self.client = genai.Client(api_key=api_key)  # 初始化Google genai客户端
        self.messages = list()  # 初始化消息列表
        self.temperature = temperature  # 设置温度参数
        self.stream = stream  # 设置是否启用流式对话

        # 查看用户指定的模型是否可用
        if self.model not in self.avaliable_models():
            FATAL(f"Model not avaliable: {self.model}\n\nAvaliable models: {self.avaliable_models()}")

        # 如果开启流式对话, 提示用户会逐字词返回回复
        if self.stream:
            WARNF("Stream mode enabled, response will be returned word by word.")

        self.inst = self.client.chats.create(model=self.model)  # 创建对话实例
        self.sys_prompt = "请你扮演猫娘."  # 系统提示信息, 这里随便写点东西占位置用, 在对话开始前调用set_sys_prompt()覆盖掉现在的内容

    def set_sys_prompt(self, sys_prompt: str):
        """设置系统提示信息, 通常只需要设置一次

        Parameters
        ----------
        sys_prompt : str
            系统提示信息
        """
        self.sys_prompt = sys_prompt

    def chat(self, user_prompt: str) -> str:
        """对话

        Parameters
        ----------
        user_prompt : str
            用户提示信息

        Returns
        -------
        str
            LLM回复的信息
        """
        content = str()  # LLM回复的信息

        # 获取LLM的回复, 如果启用流式对话的话就逐字词输出回复
        if self.stream:
            SAYF(f"Response from {self.model}\n--------------------\n")
            response = self.inst.send_message_stream(
                message=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.sys_prompt,
                    temperature=self.temperature,
                ),
            )
            for chunk in response:
                token = chunk.text
                content += token
                SAYF(token)
            SAYF("\n")
        else:
            response = self.inst.send_message(
                message=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.sys_prompt,
                    temperature=self.temperature,
                ),
            )
            content = response.text

        return content

    def avaliable_models(self) -> list:
        """列出所有可用的模型

        Returns
        -------
        list
            可用的模型列表
        """
        models = list()
        tmp = self.client.models.list()
        for model in tmp.page:
            models.append(model.name.lstrip("models/"))
        models.sort()
        return models

    def save_messages(self, path: str):
        """保存对话信息, 支持保存为json文件或md文件

        Parameters
        ----------
        path : str
            消息记录保存路径
        """
        # 检查获取要保存的文件的后缀名
        ext_name = os.path.splitext(path)[-1]

        # 将聊天记录转换为字典列表
        messages = [{"role": "system", "content": self.sys_prompt}]
        content = str()
        prev_role = "user"
        for msg in self.inst._curated_history:
            if msg.role == prev_role:
                content += msg.parts[0].text
            else:
                messages.append({"role": prev_role, "content": content})
                content = msg.parts[0].text
                prev_role = msg.role
        messages.append({"role": prev_role, "content": content})

        # 保存为json文件
        if ext_name == ".json":
            with open(os.path.join(path), "w") as f:
                json.dump(messages, f, indent=4)

        # 保存为md文件
        elif ext_name == ".md" or ext_name == ".markdown":
            with open(os.path.join(path), "w") as f:
                for msg in messages:
                    f.write(f"### {msg["role"]}\n\n{msg["content"]}\n")
                    f.write("\n")

        # 不支持的文件后缀名
        else:
            FATAL(f"Unsupported file extension: {ext_name}")

    def clear_messages(self):
        """清除聊天记录, 但不清除系统提示"""
        self.inst._curated_history.clear()