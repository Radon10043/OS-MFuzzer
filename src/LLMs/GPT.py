import os
import json

from openai import OpenAI
from utils import *
from LLMs.BaseLLM import BaseLLM


class GPT(BaseLLM):
    """GPT API Client"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.5,
        stream: bool = False,
    ):
        """构造函数, 初始化DeepSeek对象

        Parameters
        ----------
        base_url : str
            API的基础URL
        api_key : str
            OpenAI API Key
        model : str
            要调用的模型
        temperature : float, optional
            温度参数, by default 0.5
        stream : bool, optional
            是否使用流式响应, 开启流式相应会逐字词显示回复, by default False
        """
        self.model = model  # 设置要调用的模型
        self.base_url = base_url  # 设置API的基础URL
        self.api_key = api_key  # 设置OpenAI API Key
        self.client = OpenAI(api_key=api_key, base_url=base_url)  # 初始化OpenAI客户端
        self.messages = list()  # 初始化消息列表
        self.temperature = temperature  # 设置温度参数
        self.stream = stream  # 设置是否使用流式响应

        # 查看用户指定的模型是否可用
        if self.model not in self.avaliable_models():
            FATAL(f"Model not avaliable: {self.model}\n\nAvaliable models: {self.avaliable_models()}")

        # 如果设置了流式响应, 提示用户会逐字词显示回复
        if self.stream:
            WARNF("Stream mode is enabled, response will be displayed word by word.")

    def set_sys_prompt(self, sys_prompt: str):
        """设置系统提示信息, 通常只需要设置一次

        Parameters
        ----------
        sys_prompt : str
            系统提示信息
        """
        self.messages = [{"role": "system", "content": sys_prompt}]

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
        # 添加提示词至messages, 实现迭代对话
        self.messages.append({"role": "user", "content": user_prompt})

        # 调用对话模型, 获取回复信息
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=self.temperature,
            stream=self.stream,
        )

        # 处理回复信息
        content = str()
        if self.stream:
            SAYF(f"Response of {self.model}\n--------------------\n")
            for chunk in response:
                token = chunk.choices[0].delta.content
                if token is None: break
                content += token
                print(token, end="")
        else:
            content = response.choices[0].message.content

        # 添加回复信息至messages, 实现迭代对话
        self.messages.append({"role": "assistant", "content": content})

        # 返回本次对话回复的信息
        return content

    def avaliable_models(self) -> list:
        """列出所有可用的模型

        Returns
        -------
        list
            可用的模型列表
        """
        models = list()
        for val in self.client.models.list():
            models.append(val.id)
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

        # 保存为json文件
        if ext_name == ".json":
            with open(os.path.join(path), "w") as f:
                json.dump(self.messages, f, indent=4)

        # 保存为md文件
        elif ext_name == ".md" or ext_name == ".markdown":
            with open(os.path.join(path), "w") as f:
                for msg in self.messages:
                    f.write(f"### {msg["role"]}\n\n{msg["content"]}\n")
                    f.write("\n")

        # 不支持的文件后缀名
        else:
            FATAL(f"Unsupported file extension: {ext_name}")
