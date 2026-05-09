"""
yaml
K:v
"""
from utils.path_tool import get_abs_path
import yaml 
#此处可以封装一个函数来加载yaml配置文件，返回一个字典对象
def load_rag_config(config_path:str=get_abs_path("config/rag.yml"),encoding:str="utf-8"):
    with open(config_path,"r",encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)
    
def load_chroma_config(config_path:str=get_abs_path("config/chroma.yml"),encoding:str="utf-8"):
    with open(config_path,"r",encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)
    
def load_prompts_config(config_path:str=get_abs_path("config/prompts.yml"),encoding:str="utf-8"):
    with open(config_path,"r",encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

def load_agent_config(config_path:str=get_abs_path("config/agent.yml"),encoding:str="utf-8"):
    with open(config_path,"r",encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

rag_config=load_rag_config()
chroma_config=load_chroma_config()
prompts_config=load_prompts_config()
agent_config=load_agent_config()

if __name__ == "__main__":
    print(rag_config["chat_model_name"])