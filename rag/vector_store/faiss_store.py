import logging
import os

from typing import List, Dict, Any
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import FAISS

from infra.config.app_config import AppConfig
from infra.logs.logger_config import setup_logger
from rag.embeddings.embedding import build_embedding

# 使用项目统一的 logger 配置
logger = setup_logger("rag.vector_store")


def get_vector_database(chunks:List[str],embeddings:DashScopeEmbeddings, save_path:str = None)->FAISS:
    # create knowledge database
    knowledge_database = FAISS.from_texts(chunks, embeddings)
    logger.debug("create knowledge database from chunks...")

    if save_path:
        os.makedirs(save_path, exist_ok=True)
        knowledge_database.save_local(save_path)
        logger.debug(f"knowledge database saved to {save_path}...")

    return knowledge_database

def load_vector_database(load_path:str,embeddings = None) -> FAISS:
    """
    :param load_path:path for saving vector database
    :param embeddings:optional,if None,a new DashScope embedding instance will be created
    :return:storage objects based on FAISS
    """

    # load FAISS
    knowledge_database = FAISS.load_local(load_path, embeddings,allow_dangerous_deserialization=True)
    logger.debug(f"vector database loaded from {load_path}")

    return knowledge_database

def get_or_create_vector_database(chunks:List[str] = None) -> FAISS:
    save_dir = AppConfig.vector.VECTOR_DB_SAVE_PATH
    if os.path.exists(save_dir) and any(os.scandir(save_dir)):
        embeddings = build_embedding()
        return load_vector_database(save_dir,embeddings)
    else:
        embeddings = build_embedding()
        return get_vector_database(chunks,embeddings,save_dir)

def add_documents_to_vector_database(chunks:List[str]) -> FAISS:
    """
    向现有的向量数据库中添加新的文档chunks
    :param chunks: 新文档的文本chunks
    :return: 更新后的向量数据库
    """
    save_dir = AppConfig.vector.VECTOR_DB_SAVE_PATH

    # 如果向量数据库不存在，创建新的
    if not os.path.exists(save_dir) or not any(os.scandir(save_dir)):
        embeddings = build_embedding()
        vector_database = get_vector_database(chunks, embeddings, save_dir)
    else:
        # 加载现有数据库并添加新文档
        embeddings = build_embedding()
        vector_database = load_vector_database(save_dir, embeddings)

        if chunks:
            # 添加新的文本chunks到向量数据库
            # 添加前检查
            logger.info(f"Before add: {vector_database.index.ntotal} vectors")

            vector_database.add_texts(texts=chunks, embedding=embeddings)

            # 添加后检查
            logger.info(f"After add: {vector_database.index.ntotal} vectors")
            logger.info(f"Added {len(chunks)} chunks")

            # 保存更新后的数据库
            vector_database.save_local(save_dir)
            logger.debug(f"Added {len(chunks)} new chunks to vector database")

    return vector_database


def add_documents_to_vector_database_with_metadata(
    texts: List[str], 
    metadatas: List[Dict[str, Any]]
) -> FAISS:
    """
    向现有的向量数据库中添加新的文档chunks（带 metadata）
    :param texts: 文本 chunks 列表
    :param metadatas: 对应的 metadata 列表
    :return: 更新后的向量数据库
    """
    save_dir = AppConfig.vector.VECTOR_DB_SAVE_PATH

    # 如果向量数据库不存在，创建新的
    if not os.path.exists(save_dir) or not any(os.scandir(save_dir)):
        embeddings = build_embedding()
        # 使用 from_texts 创建，同时传入 metadata
        vector_database = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
        vector_database.save_local(save_dir)
        logger.info(f"Created new vector database with {len(texts)} chunks and metadata")
    else:
        # 加载现有数据库并添加新文档
        embeddings = build_embedding()
        vector_database = load_vector_database(save_dir, embeddings)

        if texts:
            # 添加前检查
            logger.info(f"Before add: {vector_database.index.ntotal} vectors")
            
            # 添加新的文本 chunks 到向量数据库（带 metadata）
            vector_database.add_texts(texts=texts, metadatas=metadatas)

            # 添加后检查
            logger.info(f"After add: {vector_database.index.ntotal} vectors")
            logger.info(f"Added {len(texts)} chunks with metadata")
            
            # 保存更新后的数据库
            vector_database.save_local(save_dir)
            logger.info(f"Saved vector database with {vector_database.index.ntotal} total vectors")

    return vector_database


def process_new_documents(chunks: List[str]) -> FAISS:
    """
    处理新增文档的统一入口函数
    支持单篇或多篇文档的处理
    :param chunks: 文档chunks 列表
    :return: 更新后的向量数据库
    """
    if not chunks:
        raise ValueError("No chunks provided for processing")

    # 使用新增文档处理函数
    vector_database = add_documents_to_vector_database(chunks)
    logger.info(f"Successfully processed {len(chunks)} document chunks")
    return vector_database




# if __name__ == "__main__":
#     create_vector_database()
