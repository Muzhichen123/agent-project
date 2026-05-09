import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from re import split
from typing import Any
from utils.logger import logger
from langchain_chroma import Chroma
from utils.config_handler import chroma_config
from model.factory import embedding_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_reader import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
# 必须导入 Document
from langchain_core.documents import Document

class VectorStoreService:
    """向量数据库服务类"""
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_config["collection_name"],
            embedding_function=embedding_model,
            persist_directory=chroma_config["persist_directory"]
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_config["chunk_size"],
            chunk_overlap=chroma_config["chunk_overlap"],
            separators=chroma_config["separator"],
            length_function=len,
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_config["k"]})
    
    def load_documents(self):
        def check_md5_hex(md5_for_check: str):
            md5_file = get_abs_path(chroma_config["md5_hex_store"])
            if not os.path.exists(md5_file):
                open(md5_file, "w", encoding="utf-8").close()
                return False
            with open(md5_file, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    if line.strip() == md5_for_check:
                        return True
            return False

        def save_md5_hex(md5_for_check):
            md5_file = get_abs_path(chroma_config["md5_hex_store"])
            with open(md5_file, "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        
        def get_file_documents(file_path: str) -> list[Document]:
            if file_path.endswith(".pdf"):
                return pdf_loader(file_path)
            elif file_path.endswith(".txt"):
                return txt_loader(file_path)
            else:
                return []

        allowed_file_path = listdir_with_allowed_type(
            chroma_config["data_path"],
            tuple(chroma_config["allow_knowledge_file_type"])
        )

        for read_path in allowed_file_path:
            md5_hex = get_file_md5_hex(read_path)
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{read_path} 已存在，跳过")
                continue

            try:
                documents = get_file_documents(read_path)
                if not documents:
                    logger.warning(f"[加载知识库]{read_path} 为空，跳过")
                    continue

                split_documents = self.splitter.split_documents(documents)
                if not split_documents:
                    logger.warning(f"[加载知识库]{read_path} 分割后为空，跳过")
                    continue

                self.vector_store.add_documents(split_documents)
                save_md5_hex(md5_hex)
                logger.info(f"[加载知识库]{read_path} 加载完成")

            except Exception as e:
                logger.error(f"[加载知识库]{read_path} 加载失败：{str(e)}", exc_info=True)

if __name__ == "__main__":
    vector_store_service = VectorStoreService()
    vector_store_service.load_documents()
    retriever = vector_store_service.get_retriever()
    res = retriever.invoke("机器人迷路")
    for i in res:
        print(i.page_content)
        print("=" * 20)