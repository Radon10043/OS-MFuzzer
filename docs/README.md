# kernel-driver-MR-identify

Try to identify metamorphic relations via large languge models for drivers in linux kernels.

## Dependices

Python 3.12.3

## Install

```sh
pip install -r requirements.txt
```

## Run

> [!Note]
> If no extra instructions are provided, the execution directory is the root of repository.

Create a json file (e.g. `config.json`), write the following content:

```json
{
    "identifier": {
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-xxxxxx",
        "base_model": "deepseek",
        "model": "deepseek-chat",
        "temperature": 0.5,
        "prompts": {
            "system": [
                "data/prompts/identifier/system.md"
            ],
            "user": [
                "data/prompts/identifier/init.md",
                "data/prompts/identifier/follow.md"
            ]
        }
    },
    "calibrator": {
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-xxxxxx",
        "base_model": "deepseek",
        "model": "deepseek-chat",
        "temperature": 0.2,
        "prompts": {
            "system": [
                "data/prompts/calibrator/system.md"
            ],
            "user": [
                "data/prompts/calibrator/vanilla.md"
            ]
        }
    },
    "max_iter": 10,
    "output": "data/output",
    "specification": "data/specifications/autofs/example.md",
    "driver_name": "autofs"
}
```

Explanation of each parameters is as follows:

- identifier: store the settings of identifier model, specifically:
  - base_url: base URL for access model, such as DeepSeek.
  - api_key: your API key for accessing model, usally prefix with "sk-".
  - base_model: based on which series of models to query, such as DeepSeek, GPT (case insensitive).
  - temperature: the temperature wanna used, the lower temperature, the more stable and accurate the LLM's response.
  - prompts: prompts that will send to LLM, categorized into system prompt and user prompt. Each prompt is stored in a markdown file and its path is presented in the json file, the script will read and load each prompt's content.
- calibrator: store the settings of calibrator model, its content is same as identifier.
- max_iter: maximum iteration for discussing.
- output: output directory that stores query messages, discussion result, etc.
- specification: path of specification file that used in the LLM query.
- driver_name: Name of driver under test.