"""
Author       : Radon
Date         : 2025-02-12 20:23:29
LastEditors  : Radon
LastEditTime : 2025-08-10 12:04:00
Description  : Prompt iden llm & cali llm to identify and calibrate metamorphic relation.
"""

import argparse
import json
import os
import shutil

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from utils import *
from wrappers.anthropic import Anthropic
from wrappers.googleai import GoogleAI
from wrappers.openai import OpenAI


def check_config(args: argparse.Namespace):
    """Check the validity of the configuration file and prepare the output directory.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments containing the path of the configuration file.
    """
    if not os.path.exists(args.config):
        FATAL(f"File not found: {args.config}")
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    # If the key temperature is not exist, use default value 0.5
    if "temperature" not in config["identifier"].keys():
        WARNF('Key "temperature" not found in config file for "identifier", using default value: 0.5')
        config["identifier"]["temperature"] = 0.5
    if "temperature" not in config["calibrator"].keys():
        WARNF('Key "temperature" not found in config file for "calibrator", using default value: 0.5')
        config["calibrator"]["temperature"] = 0.5

    # If the key stream is not exist, use default value False
    if "stream" not in config["identifier"].keys():
        WARNF('Key "stream" not found in config file for "identifier", using default value: False')
        config["identifier"]["stream"] = False
    if "stream" not in config["calibrator"].keys():
        WARNF('Key "stream" not found in config file for "calibrator", using default value: False')
        config["calibrator"]["stream"] = False

    # Check the output directory
    out_dir = config["output"]
    if args.remove_exist_outdir:
        shutil.rmtree(out_dir, ignore_errors=True)
    elif os.path.exists(out_dir):
        FATAL(f"Output directory already exists: {out_dir}, please remove it first.")


def setup_openai(config: dict, role: str) -> OpenAI:
    """Initialize an OpenAI chat object

    Parameters
    ----------
    config : dict
        Configuration provided by user
    role : str
        Role of llm, which is identifier or calibrator

    Returns
    -------
    OpenAI
        OpenAI chat object
    """
    # Initialize OpenAI chat object
    openai_obj = OpenAI(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
        stream=config[role]["stream"],
    )

    driver_name = config["driver_name"]
    spec = read_file(config["specification"])   # Specification content

    # Set system prompt
    fn = config[role]["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    sys_prompt = sys_prompt.replace("[Driver name]", driver_name)
    sys_prompt = sys_prompt.replace("[Text from specification]", spec)
    openai_obj.set_sys_prompt(sys_prompt)

    return openai_obj


def setup_anthropic(config: dict, role: str) -> Anthropic:
    """Initialize an Anthropic chat object

    Parameters
    ----------
    config : dict
        Configuration provided by user
    role : str
        Role of llm, which is identifier or calibrator

    Returns
    -------
    Anthropic
        Anthropic chat object
    """
    # Initialize Anthropic chat object
    anthropic_obj = Anthropic(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
        stream=config[role]["stream"],
    )

    driver_name = config["driver_name"]
    spec = read_file(config["specification"])   # Specification content

    # Set system prompt
    fn = config[role]["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    sys_prompt = sys_prompt.replace("[Driver name]", driver_name)
    sys_prompt = sys_prompt.replace("[Text from specification]", spec)
    anthropic_obj.set_sys_prompt(sys_prompt)

    return anthropic_obj


def setup_googleai(config: dict, role: str) -> GoogleAI:
    """Initialize a GoogleAI chat object

    Parameters
    ----------
    config : dict
        Configuration provided by user
    role : str
        Role of llm, which is identifier or calibrator

    Returns
    -------
    GoogleAI
        GoogleAI chat object
    """
    # Initialize googleai chat model
    googleai_obj = GoogleAI(
        base_url=config[role]["base_url"],
        api_key=config[role]["api_key"],
        model=config[role]["model"],
        temperature=config[role]["temperature"],
        stream=config[role]["stream"],
    )

    driver_name = config["driver_name"]
    spec = read_file(config["specification"])  # Specification content

    # Set system prompt
    fn = config[role]["prompts"]["system"]
    sys_prompt = str()
    with open(fn, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    sys_prompt = sys_prompt.replace("[Driver name]", driver_name)
    sys_prompt = sys_prompt.replace("[Text from specification]", spec)
    googleai_obj.set_sys_prompt(sys_prompt)

    return googleai_obj


def loop(
    identifier: OpenAI | Anthropic | GoogleAI,
    calibrator: OpenAI | Anthropic | GoogleAI,
    config: dict,
    vector_db: Chroma | None,
):
    """Prompt identifier & calibrator to identify and calibrate metamorphic relations (MRs).

    Parameters
    ----------
    identifier : OpenAI | Anthropic | GoogleAI
        LLM used to identify metamorphic relations
    calibrator : OpenAI | Anthropic | GoogleAI
        LLM used to calibrate metamorphic relations
    config : dict
        Configuration provided by user
    """
    # Add user prompts to the list
    iden_prompts = list()  # Prompt list for identifier
    cali_prompts = list()  # Prompt list for calibrator
    for fn in config["identifier"]["prompts"]["user"]:
        iden_prompts.append(Path(fn).read_text(encoding="utf-8"))
    for fn in config["calibrator"]["prompts"]["user"]:
        cali_prompts.append(Path(fn).read_text(encoding="utf-8"))

    # Retrieve relevant documents from the external corpus if exists
    spec = Path(config["specification"]).read_text(encoding="utf-8")
    retrieved_prompt = str()
    if vector_db is not None:
        retrieved_docs = vector_db.similarity_search(query=spec)
        docs_content = "\n\n---\n\n".join(doc.page_content for doc in retrieved_docs)
        if len(docs_content) > 0:
            retrieved_prompt = f"You can also refer to the following documents:\n\n{docs_content}"

    # Prompt identifier and calibrator to identify and calibrate metamorphic relations iteratively
    prev_mr = str()  # Previous metamorphic relation content
    mr = str()  # Latest metamorphic relation
    gen_success = False  # Whether the MR generation is successful
    idx_iden_prompt = 0  # identifier prompt index
    idx_cali_prompt = 0  # calibrator prompt index
    iterations = 0
    dirver_name = config["driver_name"]  # Driver name
    while iterations < config["max_iter"]:
        ACTF(f"Iterations: {iterations + 1}")
        ACTF(f"Asking identifier ({config['identifier']['model']}) ...")
        iden_prompt = iden_prompts[idx_iden_prompt]
        iden_prompt = iden_prompt.replace("[Text from specification]", spec)
        iden_prompt = iden_prompt.replace("[MR generated by calibrator]", mr)
        iden_prompt = iden_prompt.replace("[Driver name]", dirver_name)

        # Add retrieved documents to the identifier prompt if exists
        if len(retrieved_prompt) > 0:
            iden_prompt += "\n\n" + retrieved_prompt

        # Prompt identifier to generate an metamorphic relation
        iden_response = identifier.chat(iden_prompt)

        # If identifier's output does not contain a code block, or not further improved
        # MR, break the loop
        prev_mr = mr
        mr = get_first_code_block(iden_response, {"markdown", "md"})
        if len(mr) == 0:
            break
        OKF(f"Got the MR generated by identifier!")

        ACTF(f"Asking calibrator ({config['calibrator']['model']}) ...")
        cali_prompt = cali_prompts[idx_cali_prompt]
        cali_prompt = cali_prompt.replace("[MR generated by identifier]", mr)
        cali_prompt = cali_prompt.replace("[Driver name]", dirver_name)
        cali_response = calibrator.chat(cali_prompt)

        # If calibrator's output does not contain a code block, or its output is "correct",
        # then we consider the MR is successfully generated
        prev_mr = mr
        mr = get_first_code_block(cali_response, {"markdown", "md"})
        if len(mr) == 0 or cali_response.lower() == "correct":
            gen_success = True
            break
        OKF("Got the MR generated by calibrator!")

        # Update prompt index of iden llm & cali llm for the next iteration
        if idx_iden_prompt < len(config["identifier"]["prompts"]["user"]) - 1:
            idx_iden_prompt += 1
        if idx_cali_prompt < len(config["calibrator"]["prompts"]["user"]) - 1:
            idx_cali_prompt += 1

        # Update iteration count
        iterations += 1

    # Save chat messages of iden llm & cali llm to the output directory
    # Save the final MR to the output directory
    outdir = config["output"]
    os.makedirs(outdir, exist_ok=True)
    identifier.save_messages(os.path.join(outdir, "iden_messages.md"))
    identifier.save_messages(os.path.join(outdir, "iden_messages.json"))
    calibrator.save_messages(os.path.join(outdir, "cali_messages.md"))
    calibrator.save_messages(os.path.join(outdir, "cali_messages.json"))
    if gen_success:
        with open(os.path.join(outdir, "mr_final.md"), "w") as f:
            f.write("### FINAL DISCUSSION RESULT\n\n")
            f.write(prev_mr + "\n\n")
            f.write(f"IDENTIFIER: {config['identifier']['model']}\n\n")
            f.write(f"CALIBRATOR: {config['calibrator']['model']}\n\n")
            f.write(f"ITERATIONS: {iterations + 1}\n\n")
        OKF(f"Discussion finished! Check the output directory {config['output']} for details.")
    else:
        WARNF(f"{identifier.model} (identifier) and {calibrator.model} (calibrator) did not reach the consistent!")


def main(config: dict):
    """Initialize the identifier and calibrator, then let the two models discuss to identify and calibrate metamorphic relations.

    Parameters
    ----------
    config : dict
        Configuration provided by user
    """
    # Dictionary to map framework names to setup functions
    setup_func_dict = {
        "openai": setup_openai,
        "anthropic": setup_anthropic,
        "googleai": setup_googleai,
    }

    # Initialize identification llm
    ACTF(f"Initializing identifier model ({config['identifier']['model']}) ...")
    framework = config["identifier"]["framework"].lower()
    if framework not in setup_func_dict.keys():
        FATAL(f"Unsupported model: {framework}\n\nSupported models: {setup_func_dict.keys()}")
    identifier = setup_func_dict[framework](config, "identifier")
    OKF("Identifier model successfully initialized!")

    # Initialize calibration llm
    ACTF(f"Initializing calibrator model ({config['calibrator']['model']}) ...")
    framework = config["calibrator"]["framework"].lower()
    if framework not in setup_func_dict.keys():
        FATAL(f"Unsupported model: {framework}\n\nSupported models: {setup_func_dict.keys()}")
    calibrator = setup_func_dict[framework](config, "calibrator")
    OKF("Calibrator model successfully initialized!")

    # Load the external corpus if exists
    vector_db = None
    embedding = config["embedding"]
    if "corpus" in config.keys():
        chroma_dir = os.path.join(config["corpus"], "chroma")
        embedding = OpenAIEmbeddings(model=embedding)
        vector_db = Chroma(persist_directory=chroma_dir, embedding_function=embedding)

    # Prompt iden llm & cali llm to identify and calibrate metamorphic relations
    ACTF("Let identifier and calibrator discuss ...")
    loop(identifier, calibrator, config, vector_db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path of configuration json file.")
    parser.add_argument("--remove-exist-outdir", action="store_true", help="Remove the output directory if it exists.")
    args = parser.parse_args()

    # Check validity of arguments
    ACTF("Checking arguments...")
    check_config(args)
    OKF("Arguments are valid.")

    # Read the configuration file
    config = dict()
    with open(args.config, "r") as f:
        config = json.load(f)

    main(config)
