from langchain_community.embeddings import DashScopeEmbeddings
from infra.config.app_config import AppConfig


def build_embedding():
    # deploy embedding model
    embeddings = DashScopeEmbeddings(
        model=AppConfig.model.EMBEDDING_MODEL_NAME
    )
    return embeddings