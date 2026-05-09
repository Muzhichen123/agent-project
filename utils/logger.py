import logging
from utils.path_tool import get_abs_path
import os
from datetime import datetime
# 日志保存的根目录
LOG_ROOT = get_abs_path('logs')

# 确保日志的目录存在
os.makedirs(LOG_ROOT, exist_ok=True)

# 日志的格式配置
DEFAULT_LOG_FORMAT = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s') 
# 获取日志记录器的函数
def get_logger(name:str="agent", log_file:str=None, console_level=logging.INFO,file_level:int = logging.DEBUG)->logging.Logger:
    logger = logging.getLogger(name)#获取指定名称的日志记录器
    logger.setLevel(logging.DEBUG)#设置日志记录器的最低日志级别为DEBUG，这样所有级别的日志都会被记录下来，具体输出到控制台和文件的级别由各自的Handler控制
    
    #避免重复添加Handler
    if logger.handlers:
        return logger
    
    #控制台日志处理器
    console_handler = logging.StreamHandler()#创建一个控制台日志处理器
    console_handler.setLevel(console_level)#设置控制台日志处理器的日志级别，默认为INFO，这样只有INFO及以上级别的日志会输出到控制台
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)#   设置控制台日志处理器的日志格式
    
    # 将控制台处理器添加到logger
    logger.addHandler(console_handler)
    
    # 文件Handler
    if not log_file:
        log_file = os.path.join(LOG_ROOT, f"{name}_{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')#创建一个文件日志处理器，日志文件的路径由参数log_file指定，如果没有提供，则默认使用logs目录下以日志记录器名称和当前日期命名的日志文件
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)
    # 将文件处理器添加到logger
    logger.addHandler(file_handler)
    return logger

#快捷获取默认日志记录器
logger = get_logger()

if __name__ == "__main__":
    logger.debug("这是一个调试日志")
    logger.info("这是一个信息日志")
    logger.warning("这是一个警告日志")
    logger.error("这是一个错误日志")
    logger.critical("这是一个严重错误日志")
