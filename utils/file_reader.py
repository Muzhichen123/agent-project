# 文件处理工具 
import os
import hashlib
from langchain_community.document_loaders import PyPDFLoader, TextLoader  
from utils.logger import logger
def get_file_md5_hex(file_path:str):#获取文件的md5值
    if not os.path.exists(file_path):
        logger.error(f"[md5计算]文件不存在: {file_path}")
        return None

    if not os.path.isfile(file_path):
        logger.error(f"[md5计算]路径不是一个文件: {file_path}")
        return None
    md5_obj=hashlib.md5()
    chunk_size=8192
    try:
        with open(file_path,"rb") as f:
            while chunk:=f.read(chunk_size):
                md5_obj.update(chunk)
            """
            chunk=f.read(chunk_size)
            while chunk:
                md5_obj.update(chunk)
                chunk=f.read(chunk_size)
            等同于先拿到前面的chunk，然后在循环里更新md5，最后拿到新的chunk继续循环，直到chunk为空为止       
            """
            md5_hex=md5_obj.hexdigest()
            return md5_hex
    except Exception as e:
        logger.error(f"[md5计算]文件md5失败: {file_path}, 错误信息: {str(e)}")
        return None

def listdir_with_allowed_type(folder_path:str,allowed_types:tuple[str]):#返回文件夹内的指定类型的文件列表
    files=[]
    if not os.path.isdir(folder_path):
        logger.error(f"[文件列表]路径不是一个文件夹: {folder_path}")
        return files
    for f in os.listdir(folder_path):
        if f.endswith(allowed_types):
            files.append(os.path.join(folder_path,f))
    return tuple(files)
def pdf_loader(file_path:str,passwd=None):#加载pdf文件，返回文本内容
    return PyPDFLoader(file_path,passwd).load()
def txt_loader(file_path:str):#加载txt文件，返回文本内容
    return TextLoader(file_path,encoding='utf-8').load()