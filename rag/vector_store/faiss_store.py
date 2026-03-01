import logging
import os

from typing import List
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import FAISS

from infra.config.app_config import AppConfig
from rag.embeddings.embedding import build_embedding


def get_vector_database(chunks:List[str],embeddings:DashScopeEmbeddings, save_path:str = None)->FAISS:
    # create knowledge database
    knowledge_database = FAISS.from_texts(chunks, embeddings)
    logging.debug("create knowledge database from chunks...")

    if save_path:
        os.makedirs(save_path, exist_ok=True)
        knowledge_database.save_local(save_path)
        logging.debug(f"knowledge database saved to {save_path}...")

    return knowledge_database

def load_vector_database(load_path:str,embeddings = None) -> FAISS:
    """
    :param load_path:path for saving vector database
    :param embeddings:optional,if None,a new DashScope embedding instance will be created
    :return:storage objects based on FAISS
    """

    # load FAISS
    knowledge_database = FAISS.load_local(load_path, embeddings,allow_dangerous_deserialization=True)
    logging.debug(f"vector database loaded from {load_path}")

    return knowledge_database

def get_or_create_vector_database(chunks:List[str] = None) -> FAISS:
    save_dir = AppConfig.vector.VECTOR_DB_SAVE_PATH
    if os.path.exists(save_dir) and any(os.scandir(save_dir)):
        embeddings = build_embedding()
        return load_vector_database(save_dir,embeddings)
    else:
        embeddings = build_embedding()
        return get_vector_database(chunks,embeddings,save_dir)

# def add_documents_to_vector_database(chunks:List[str],vector_database:FAISS) -> FAISS:
#     if chunks:
#         vector_database = get_or_create_vector_database()
#         embeddings = build_embedding()
#         vector_database.add_texts(texts= chunks, embeddings=embeddings)
#     return vector_database




# if __name__ == "__main__":
#     create_vector_database()
