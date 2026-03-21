import os
import time
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from pinecone import Pinecone, ServerlessSpec
from langchain_community.embeddings import DashScopeEmbeddings

from infra.config.app_config import AppConfig
from infra.logs.logger_config import get_logger

# 加载环境变量
load_dotenv()

logger = get_logger("rag.pinecone_store")


class PineconeStore:
    """Pinecone向量库存储和管理类"""

    def __init__(self, index_name: str = None):
        """
        初始化 Pinecone 连接

        :param index_name: 索引名称，默认使用配置中的名称
        """
        self.api_key = os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY not found in environment")

        # Pinecone 配置
        self.index_name = index_name or AppConfig.pinecone.INDEX_NAME
        self.dimension = AppConfig.pinecone.DIMENSION
        self.metric = AppConfig.pinecone.METRIC
        self.cloud = AppConfig.pinecone.CLOUD_PROVIDER
        self.region = AppConfig.pinecone.REGION

        # 初始化 Pinecone 客户端
        logger.info(f"Initializing Pinecone client...")
        self.pc = Pinecone(api_key=self.api_key)

        # 获取或创建索引
        self.index = self._get_or_create_index()

        logger.info(f"Pinecone store initialized with index: {self.index_name}")

    def _get_or_create_index(self):
        """获取或创建 Pinecone 索引"""
        try:
            # 检查索引是否存在
            existing_indexes = self.pc.list_indexes().names()

            if self.index_name in existing_indexes:
                logger.info(f"Index '{self.index_name}' already exists, connecting to it...")
                return self.pc.Index(self.index_name)
            else:
                logger.info(f"Creating new index: {self.index_name}")

                # 创建新索引
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    spec=ServerlessSpec(
                        cloud=self.cloud,
                        region=self.region
                    )
                )

                logger.info(f"Index creation request submitted, waiting for it to be ready...")

                # 等待索引就绪
                max_retries = 10
                for i in range(max_retries):
                    indexes = self.pc.list_indexes().names()
                    if self.index_name in indexes:
                        logger.info(f"Index is ready!")
                        return self.pc.Index(self.index_name)
                    time.sleep(2)

                raise TimeoutError(f"Index {self.index_name} creation timed out")

        except Exception as e:
            logger.error(f"Failed to get/create index: {e}", exc_info=True)
            raise

    def add_texts_with_metadata(
            self,
            texts: List[str],
            metadatas: Optional[List[Dict[str, Any]]] = None,
            ids: Optional[List[str]] = None,
            batch_size: int = None
    ):
        """
        向 Pinecone 索引中添加文本和 metadata

        :param texts: 文本列表
        :param metadatas: metadata 列表，每个元素是字典
        :param ids: 向量 ID 列表，如果不提供则自动生成
        :param batch_size: 批处理大小
        :return: 添加的向量数量
        """
        if not texts:
            logger.warning("No texts provided to add")
            return 0

        batch_size = batch_size or AppConfig.pinecone.BATCH_SIZE

        # 生成 embedding
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        embeddings_model = DashScopeEmbeddings(model="text-embedding-v2")

        # 批量生成 embeddings
        vectors = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = embeddings_model.embed_documents(batch_texts)

            for j, (text, embedding) in enumerate(zip(batch_texts, batch_embeddings)):
                # 生成唯一 ID
                vector_id = ids[i + j] if ids and i + j < len(ids) else f"vec_{i + j}_{int(time.time())}"

                # 准备 metadata
                metadata = metadatas[i + j] if metadatas and i + j < len(metadatas) else {}
                metadata['text'] = text  # 保存原始文本到 metadata

                vectors.append((vector_id, embedding, metadata))

            logger.info(f"Processed batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")

        # 批量 upsert 到 Pinecone
        logger.info(f"Upserting {len(vectors)} vectors to Pinecone...")

        for i in range(0, len(vectors), batch_size):
            batch_vectors = vectors[i:i + batch_size]

            try:
                self.index.upsert(vectors=batch_vectors)
                logger.info(f"Upserted batch {i // batch_size + 1}/{(len(vectors) - 1) // batch_size + 1}")
            except Exception as e:
                logger.error(f"Failed to upsert batch: {e}", exc_info=True)
                raise

        logger.info(f"Successfully added {len(vectors)} vectors to Pinecone")
        return len(vectors)

    def similarity_search(
            self,
            query: str,
            k: int = 5,
            filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        语义检索最相似的文档

        :param query: 查询文本
        :param k: 返回结果数量
        :param filter_metadata: metadata 过滤条件
        :return: [(vector_id, score, metadata), ...]
        """
        logger.debug(f"Searching for query: {query}, k={k}, filter={filter_metadata}")

        # 生成查询 embedding
        embeddings_model = DashScopeEmbeddings(model="text-embedding-v2")
        query_vector = embeddings_model.embed_query(query)

        # 构建 Pinecone 过滤条件
        pinecone_filter = self._build_pinecone_filter(filter_metadata) if filter_metadata else None

        # 执行检索 - 增加重试机制
        logger.debug(f"Pinecone filter: {pinecone_filter}")
        
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                results = self.index.query(
                    vector=query_vector,
                    top_k=k * 3,  # 先检索更多候选
                    filter=pinecone_filter,
                    include_metadata=True,
                    timeout=30  # 30秒超时
                )
                break  # 成功则跳出重试循环
            except Exception as e:
                logger.warning(f"Pinecone查询失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"Pinecone查询最终失败，返回空结果")
                    return []  # 返回空列表而不是抛出异常

        # 解析结果
        matches = []
        for match in results.matches:
            matches.append((
                match.id,
                match.score,
                match.metadata
            ))

        # 按分数排序并返回前 k 个
        matches.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Retrieved {len(matches)} documents, returning top {min(k, len(matches))}")

        return matches[:k]

    def _build_pinecone_filter(self, filter_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        将通用的 filter_metadata 转换为 Pinecone 过滤语法

        :param filter_metadata: {"file_id": "xxx", "document_type": "个人简历"}
        :return: {"file_id": {"$eq": "xxx"}, "document_type": {"$eq": "个人简历"}}
        """
        pinecone_filter = {}

        for key, value in filter_metadata.items():
            if isinstance(value, list):
                # 列表使用 $in
                pinecone_filter[key] = {"$in": value}
            elif isinstance(value, dict):
                # 如果已经是 Pinecone 格式，直接使用
                pinecone_filter[key] = value
            else:
                # 单个值使用 $eq
                pinecone_filter[key] = {"$eq": value}

        logger.debug(f"Built Pinecone filter: {pinecone_filter}")
        return pinecone_filter

    def delete_by_ids(self, ids: List[str]):
        """
        根据 ID 删除向量

        :param ids: 要删除的向量 ID 列表
        """
        if not ids:
            return

        logger.info(f"Deleting {len(ids)} vectors from Pinecone...")

        try:
            self.index.delete(ids=ids)
            logger.info(f"Successfully deleted {len(ids)} vectors")
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}", exc_info=True)
            raise

    def delete_by_filter(self, filter_metadata: Dict[str, Any]):
        """
        根据 metadata 过滤条件删除向量

        :param filter_metadata: 过滤条件
        """
        logger.info(f"Deleting vectors by filter: {filter_metadata}")

        try:
            pinecone_filter = self._build_pinecone_filter(filter_metadata)
            self.index.delete(filter=pinecone_filter)
            logger.info(f"Successfully deleted vectors matching filter")
        except Exception as e:
            logger.error(f"Failed to delete vectors by filter: {e}", exc_info=True)
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息

        :return: 统计信息字典
        """
        try:
            index_info = self.pc.describe_index(self.index_name)

            return {
                'name': index_info.name,
                'dimension': index_info.dimension,
                'metric': index_info.metric,
                'vector_count': index_info.vector_count,
                'status': 'Ready'
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {
                'name': self.index_name,
                'status': 'Error',
                'error': str(e)
            }

    def clear_index(self):
        """清空索引中的所有向量"""
        logger.info(f"Clearing all vectors from index: {self.index_name}")

        try:
            # Pinecone 不支持直接清空，需要删除所有向量
            # 这里通过删除整个索引并重新创建来实现
            self.pc.delete_index(self.index_name)
            logger.info(f"Index {self.index_name} deleted")

            # 重新创建索引
            self.index = self._get_or_create_index()
            logger.info(f"Index {self.index_name} recreated")

        except Exception as e:
            logger.error(f"Failed to clear index: {e}", exc_info=True)
            raise


# 全局单例
_pinecone_store_instance = None


def get_pinecone_store(index_name: str = None) -> PineconeStore:
    """
    获取 Pinecone Store 单例实例

    :param index_name: 索引名称
    :return: PineconeStore 实例
    """
    global _pinecone_store_instance

    if _pinecone_store_instance is None:
        _pinecone_store_instance = PineconeStore(index_name)

    return _pinecone_store_instance


def reload_pinecone_store(index_name: str = None):
    """
    重新加载 Pinecone Store（用于测试或重置）

    :param index_name: 索引名称
    :return: 新的 PineconeStore 实例
    """
    global _pinecone_store_instance
    _pinecone_store_instance = PineconeStore(index_name)
    return _pinecone_store_instance