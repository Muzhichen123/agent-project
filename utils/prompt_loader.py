from utils.config_handler import prompts_config
from utils.path_tool import get_abs_path
from utils.logger import logger

# 通用加载函数
def load_prompt(prompt_config_key, logger_name):
    try:
        prompt_path = get_abs_path(prompts_config[prompt_config_key])
    except KeyError as e:
        logger.error(f"[{logger_name}] 在yaml配置项中没有{prompt_config_key}配置项")
        raise e

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"[{logger_name}] 解析提示词出错，{str(e)}")
        raise e

# 封装函数
def load_system_prompts():
    return load_prompt("main_prompt_path", "load_system_prompts")

def load_rag_prompts():
    return load_prompt("rag_summarize_prompt_path", "load_rag_prompts")

def load_report_prompts():
    return load_prompt("report_prompt_path", "load_report_prompts")


if __name__ == '__main__':
    print(load_report_prompts())