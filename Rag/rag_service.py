"""
RAG服务类 
用户提问，搜索参考资料，将提问和参考资料合并，并提交给模型，让模型总结回复
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from Rag.vector_store import VectorStoreService
from utils.logger import logger
from utils.prompt_loader import load_rag_prompts
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
def print_prompt(prompt):
    print("="*50)
    print(prompt.to_string())
    print("="*50)
    return prompt
class RagSummaryService(object):
    """RAG总结服务类"""
    def __init__(self):
        self.vector_store=VectorStoreService()
        self.retriever=self.vector_store.get_retriever()
        self.prompt_text=load_rag_prompts()
        self.prompt_template=PromptTemplate.from_template(self.prompt_text)
        self.model=chat_model
        self.chain=self.__init__chain()
    def __init__chain(self):
            chain=self.prompt_template | print_prompt| self.model | StrOutputParser()
            return chain
    def retriever_docs(self,query:str)->list[Document]:
            return self.retriever.invoke(query)
        
    def rag_summary(self,query:str)->str:
        context_docs=self.retriever_docs(query)
        context=""
        counter=0
        for i in context_docs:
            counter+=1
            context+=f"【参考资料{counter}】: 参考资料:{i.page_content}|参考元数据：{i.metadata}\n"
        return self.chain.invoke({

            "input":query,
            "context":context
        })
if __name__ == "__main__":
    rag_service=RagSummaryService()
    print(rag_service.rag_summary("小户型适合那种扫地机器人"))
            