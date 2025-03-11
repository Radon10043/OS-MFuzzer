import os
import json

from utils import *
from wrappers.wrapper import Wrapper

from anthropic import Anthropic as OfficalAnthropic


class Anthropic(Wrapper):
    """Anthropic Client"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.5,
        stream: bool = False,
    ):
        """构造函数, 初始化Anthropic对象

        Parameters
        ----------
        base_url : str
            API的基础URL
        api_key : str
            Anthropic API Key
        model : str
            要调用的模型
        temperature : float, optional
            温度参数, by default 0.5
        stream : bool, optional
            是否启用流式响应, by default False
        """
        self.model = model  # 设置要调用的模型
        self.base_url = base_url  # 设置API的基础URL
        self.api_key = api_key  # 设置Anthropic API Key
        self.client = OfficalAnthropic(api_key=api_key, base_url=base_url)  # 初始化Anthropic客户端
        self.sys_prompts = str()  # Anthropic的系统提示发送和OpenAI的存在不同, 需要单独建一个存系统提示的变量
        self.messages = list()  # 初始化消息列表, 用户提示专用
        self.temperature = temperature  # 设置温度参数
        self.stream = stream  # 设置是否启用流式响应

        # 查看用户指定的模型是否可用
        if self.model not in self.avaliable_models():
            FATAL(f"Model not avaliable: {self.model}\n\nAvaliable models: {self.avaliable_models()}")

        # Anthropic框架暂时没调整好流式回应
        if self.stream:
            WARNF("Stream mode are not supported by Anthropic framework.")

    def set_sys_prompt(self, sys_prompt: str):
        """设置系统提示信息, 感觉大部分情况下系统提示一条就够了...?

        Parameters
        ----------
        sys_prompt : str
            系统提示信息
        """
        self.sys_prompts = sys_prompt

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
        response = self.client.messages.create(
            max_tokens=1024,  # 沿用anthropic的api docs中的数值, REF: https://docs.anthropic.com/en/api/messages
            model=self.model,
            system=self.sys_prompts,
            messages=self.messages,
            temperature=self.temperature,
            stream=False,
        )
        content = response.content[0].text

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
