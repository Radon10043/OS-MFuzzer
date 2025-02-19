# kernel-driver-MR-identify

Try to identify metamorphic relations via large languge models for drivers in linux kernels.

## Dependices

- Ubuntu 22.04
- Python 3.12.3

## Install

```sh
pip install -r requirements.txt
```

## Run

> [!Note]
> If no extra instructions are provided, the execution directory is the `src` folder of repository.

### MR Identification

Create a json file (e.g. `MRIden.cfg.json`), write the following content:

```json
{
    "identifier": {
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-xxx",
        "framework": "openai",
        "model": "deepseek-chat",
        "temperature": 0.5,
        "stream": true,
        "prompts": {
            "system": "/path/to/kernel-driver-MR-identify/data/prompts/identifier/system.md",
            "user": [
                "/path/to/kernel-driver-MR-identify/data/prompts/identifier/init.md",
                "/path/to/kernel-driver-MR-identify/data/prompts/identifier/follow.md"
            ]
        }
    },
    "calibrator": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-xxx",
        "framework": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "stream": true,
        "prompts": {
            "system": "/path/to/kernel-driver-MR-identify/data/prompts/calibrator/system.md",
            "user": [
                "/path/to/kernel-driver-MR-identify/data/prompts/calibrator/vanilla.md"
            ]
        }
    },
    "max_iter": 10,
    "output": "/path/to/kernel-driver-MR-identify/data/output",
    "specification": "/path/to/kernel-driver-MR-identify/data/specifications/linux-v6.2/autofs/sec1_purpose.md",
    "driver_name": "autofs"
}
```

MRIden.py is used to identify and calibrate MR via LLMs. Explanation of each parameters is as follows:

- identifier: store the settings of identifier model, specifically:
  - base_url: base URL for access model, such as DeepSeek.
  - api_key: your API key for accessing model, usally prefix with "sk-".
  - base_model: based on which series of models to query, such as DeepSeek, GPT (case insensitive).
  - temperature: the temperature wanna used, the lower temperature, the more stable and accurate the LLM's response.
  - stream: whether to enable streaming response. If enabled, the output of LLM will be printed in streaming mode.
  - prompts: prompts that will send to LLM, categorized into system prompt and user prompt. This project supports one system prompt and multi user prompts. Each prompt is stored in a markdown file and its path is presented in the json file, the script will read and load each prompt's content.
- calibrator: store the settings of calibrator model, its content is same as identifier.
- max_iter: maximum iteration for discussing.
- output: output directory that stores query messages, discussion result, etc.
- specification: path of specification file that used in the LLM query.
- driver_name: Name of driver under test.

### MR Implementation

Create a json file (e.g. `MRImpl.json`), write the following content:

```json
{
    "base_url": "https://api.deepseek.com",
    "api_key": "sk-xxx",
    "framework": "openai",
    "model": "deepseek-chat",
    "stream": true,
    "temperature": 0.5,
    "prompts": {
        "system": "/path/to/kernel-driver-MR-identify/data/prompts/programmer/system.md",
        "user": [
            "/path/to/kernel-driver-MR-identify/data/prompts/programmer/init.md",
            "/path/to/kernel-driver-MR-identify/data/prompts/programmer/follow.md"
        ]
    },
    "mrc_desc": "/path/to/kernel-driver-MR-identify/data/MRCs/mrc1.md",
    "max_iter": 10,
    "output": "/path/to/kernel-driver-MR-identify/data/output/MRImpl",
    "compiler": "gcc",
    "cflags": "-static"
}
```

MRImpl.py is used to generate C code of an MRC. Explanation of each parameters is as follows:

- Meaning of base_url, api_key, framework, temperature, prompts, stream, and max_iter are same as MR Identification.
- mrc_desc: path of markdown file that store the description of an MRC. Note the MRC should be placed in a markdown code block.
- compiler: specificed compiler that used to compile the generated C code, e.g. gcc.
- cflags: compile options.