import mlflow

from ..common.logger import get_logger

logger = get_logger(__name__)


def load_prompt_from_mlflow(prompt_name, version):
    prompt = mlflow.genai.load_prompt(  # type: ignore
        f"prompts:/{prompt_name}/{version}"
    ).to_single_brace_format()
    return prompt


def load_prompts(prompt_dics):
    prompts = {}
    for prompt_name, prompt_version in prompt_dics.items():
        logger.info(f"Loading prompt '{prompt_name}' version {prompt_version}")
        prompt = load_prompt_from_mlflow(prompt_name, prompt_version)
        # key = f"{prompt_name}_v{prompt_version}"
        key = prompt_name
        prompts[key] = prompt
    return prompts


import mlflow
from src.utils.file import save_dict_as_py

url = "http://192.168.0.100:30001"

mlflow.set_tracking_uri(url)

PROMPT_DIR = "./Sources/oneit_interview_ai_module/src/prompts"
# PROMPT_DIR = "./src/prompts"


question_generation_prompt_dics = {
    "interview_ext_human": 1,
    "interview_ext_system": 1,
    "interview_org_human": 1,
    "interview_org_system": 65,
    "interview_3rd_grade_org_human": 6,
    "interview_3rd_grade_org_system": 39,
    "interview_3rd_grade_text_org_human": 2,
    "interview_3rd_grade_text_org_system": 11,
    "interview_qgen_human": 4,
    "interview_qgen_system": 23,
    "interview_qgen_3rd_human": 2,
    "interview_qgen_3rd_system": 38,
    "interview_question_compensation_system": 3,
    "interview_question_compensation_human": 2,
}
additions_dics = {
    "interview_rephrasing_question": 1,
    "interview_follow_up_question_combined_human": 1,
    "interview_follow_up_question_combined_system": 9,
    "interview_answer_compensation": 3,
    "interview_answer_summary": 6,
}

if __name__ == "__main__":
    qgen_prompts = load_prompts(question_generation_prompt_dics)
    additions_prompts = load_prompts(additions_dics)

    save_dict_as_py(
        qgen_prompts, f"{PROMPT_DIR}/question_generation_prompts.py", overwrite=True
    )
    save_dict_as_py(
        additions_prompts, f"{PROMPT_DIR}/additions_prompts.py", overwrite=True
    )
