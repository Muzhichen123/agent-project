"""
为整个工程统一的绝对路径工具
"""
import os
def get_project_root()->str:
    """
    获取项目根目录的绝对路径
    :return: 项目根目录的绝对路径
    """
    #获取当前文件的绝对路径
    current_file = os.path.abspath(__file__)
    # 获取工程的根目录，先获取文件所在文件夹的绝对路径
    current_dir = os.path.dirname(current_file)
    # 再获取上一级目录的绝对路径，即工程根目录
    project_root = os.path.dirname(current_dir)
    
    return project_root

# 获取相对于项目根目录的绝对路径
def get_abs_path(relative_path:str)->str:
    """
    获取相对于项目根目录的绝对路径
    :param relative_path: 相对于项目根目录的路径
    :return: 绝对路径
    """
    project_root = get_project_root()
    abs_path = os.path.join(project_root, relative_path)
    return abs_path
