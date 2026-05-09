"""
智能工具模块
"""
import sys
from pathlib import Path
# 当前文件是 agent/tools/middleware.py
# 向上退 2 级就是项目根目录 agent_project
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))
from langchain_core.tools import tool
from Rag.rag_service import RagSummaryService
from utils.config_handler import agent_config
from utils.path_tool import get_abs_path
from utils.logger import logger
import random
import os
import requests
import pandas as pd

# 全局变量存储城市数据
city_df = None

def load_city_data():
    """加载城市编码数据"""
    global city_df
    if city_df is None:
        city_path = get_abs_path("data/external/city.csv")
        city_df = pd.read_csv(city_path, encoding="utf-8")

def get_city_code(city_name: str) -> int:
    """
    获取城市编码
    
    Args:
        city_name: 城市名称
        
    Returns:
        城市编码
    """
    load_city_data()
    
    # 优先匹配区县
    match = city_df[city_df['district'] == city_name]
    if not match.empty:
        return match.iloc[0]['areacode/城市ID']
    
    # 匹配城市
    match = city_df[city_df['city'] == city_name]
    if not match.empty:
        return match.iloc[0]['areacode/城市ID']
    
    # 模糊匹配城市
    match = city_df[city_df['city'].str.contains(city_name, na=False)]
    if not match.empty:
        return match.iloc[0]['areacode/城市ID']
    
    # 默认北京
    logger.warning(f"未找到城市 {city_name}，使用默认值北京")
    return 101010100
user_id=["1001","1002","1003","1004","1005","1006","1007","1008","1009"]
month_arr=["2025-01","2025-02","2025-03","2025-04","2025-05","2025-06","2025-07","2025-08","2025-09","2025-10","2025-11","2025-12"]
external_data={}
@tool(description="从向量存储中检索参考资料，总结回复")
def rag_summarize(query:str)->str:
   # 实例化 RAG 服务（关键代码）
    rag = RagSummaryService()
    return rag.rag_summary(query)

@tool(description="获取指定城市的天气，以消息字符串的信息格式返回")
def get_weather(city: str) -> str:
    """
    调用APISpace天气API获取真实天气数据
    
    Args:
        city: 城市名称（中文）
        
    Returns:
        格式化的天气信息字符串
    """
    url = "https://eolink.o.apispace.com/456456/weather/v001/now"
    city_code = get_city_code(city)
    
    payload = {"areacode": city_code}
    headers = {
        "X-APISpace-Token": "a9qtccd8584u63cgzoxxaveqt9m9g9qd"
    }
    
    try:
        response = requests.request("GET", url, params=payload, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('status') != 0:
            logger.error(f"天气API返回错误: {data.get('msg', '未知错误')}")
            return f"获取{city}天气失败"
        
        temp = data.get('result', {}).get('realtime', {}).get('temp', '未知')
        wd = data.get('result', {}).get('realtime', {}).get('text', '未知')
        
        return f"{city}天气:{wd}，温度:{temp}℃"
        
    except requests.exceptions.RequestException as e:
        logger.error(f"天气API请求失败: {e}")
        return f"获取{city}天气时网络出错"
    except Exception as e:
        logger.error(f"天气处理异常: {e}")
        return f"获取{city}天气时发生异常"

@tool(description="获取用户所在城市的名称，以纯字符串形式返回")
def get_user_location()->str:
    """获取用户位置"""
    return random.choice(["深圳","北京","上海","广州"])

@tool(description="获取用户id，以纯字符串形式返回")
def get_user_id()->str:
    return random.choice(user_id)

@tool(description="获取当前月份，以纯字符串形式返回")
def get_current_month()->str:
    return random.choice(month_arr)


def generate_external_data()->str:
    """
    {{
        "user_id":{
            "month":{"特征":xxx,"效率":xxx}
            "month":{"特征":xxx,"效率":xxx}
            "month":{"特征":xxx,"效率":xxx}

        },
        "user_id":{
            "month":{"特征":xxx,"效率":xxx}
            "month":{"特征":xxx,"效率":xxx}
            "month":{"特征":xxx,"效率":xxx}
        },
        "user_id":{
            "month":{"特征":xxx,"效率":xxx}
            "month":{"特征":xxx,"效率":xxx}
            "month":{"特征":xxx,"效率":xxx}
        }
    }}
    """
    if not external_data:
        external_data_path=get_abs_path(agent_config["external_data_path"])

        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件不存在：{external_data_path}")
        with open(external_data_path,"r",encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                arr:list[str]=line.strip().split(",")
                
                user_id:str =arr[0].replace('"',"")
                feature:str =arr[1].replace('"',"")
                efficiency:str =arr[2].replace('"',"")
                consumption:str =arr[3].replace('"',"")
                comparsion:str =arr[4].replace('"',"")
                time:str =arr[5].replace('"',"")
                if user_id not in external_data:
                    external_data[user_id]={}
                external_data[user_id][time]={
                        "特征":feature,
                        "效率":efficiency,
                        "消耗":consumption,
                        "对比":comparsion,
                        
                }

@tool(description="从外部系统获取指定用户在指定月份的使用记录，以消息字符串的信息格式返回，如果未找到使用记录，则返回空字符串")
def fetch_external_data(user_id:str,month:str)->str:
    generate_external_data()
    try:
        return external_data[user_id][month]
    except KeyError:
        logger.error(f"[fetch_external_data] 未找到用户 {user_id} 在月份 {month} 的使用记录")
        return ""

@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"