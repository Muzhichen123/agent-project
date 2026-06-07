"""
yaml
K:v
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.path_tool import get_abs_path
import yaml 
"""
配置文件管理模块
统一加载YAML配置文件
"""
def load_yaml_config(config_name: str, encoding: str = "utf-8") -> dict:
    """
    通用YAML配置加载函数
    Args:
        config_name: 配置文件名（不含.yml后缀）
        encoding: 文件编码，默认utf-8
    Returns:
        配置字典
    """
    config_path = get_abs_path(f"config/{config_name}.yml")
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

# 加载各配置
rag_config = load_yaml_config("rag")
chroma_config = load_yaml_config("chroma")
prompts_config = load_yaml_config("prompts")
agent_config = load_yaml_config("agent")
