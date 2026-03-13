from infra.config.base_config import BaseConfig


class PineconeConfig(BaseConfig):
    """Pinecone向量库配置"""

    # Pinecone API 配置
    PINECONE_API_KEY = "PINECONE_API_KEY"
    ENVIRONMENT = "gcp-starter"  # 或根据实际区域调整

    # 索引配置
    INDEX_NAME = "rag-agent-index"
    DIMENSION = 1536  # DashScope text-embedding-v2 的输出维度
    METRIC = "cosine"  # 相似度度量方式：cosine, euclidean, dotproduct

    # Serverless 规格配置
    CLOUD_PROVIDER = "aws"
    REGION = "us-east-1"

    # 批处理配置
    BATCH_SIZE = 100  # 批量 upsert 的大小
    CHUNK_SIZE = 100  # 批量处理 chunks 的大小