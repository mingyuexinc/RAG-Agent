import datetime
import os
import uuid

from typing import List, Dict, Any, Optional
from pathlib import Path

from infra.logs.logger_config import setup_logger
from rag.ingestion.loaders.base_loader import BaseLoader
from rag.ingestion.loaders.pdf_loader import PDFLoader
from rag.ingestion.preprocessors.base_preprocessor import BasePreprocessor, MetadataPreprocessor
from rag.ingestion.splitters.base_splitter import BaseSplitter, TextSplitter

from rag.ingestion.preprocessors.metadata_extractor import DocumentMetadata
from rag.ingestion.document_manager import DocumentManager

logger = setup_logger("rag.ingestion.pipeline")

class DocumentIngestionPipeline:
    """文档摄入流水线"""

    def __init__(self,
                 loader: Optional[BaseLoader] = None,
                 splitter: Optional[BaseSplitter] = None,
                 preprocessor: Optional[BasePreprocessor] = None,
                 document_manager: Optional[DocumentManager] = None,
                 enable_vector_store: bool = True):
        """
        初始化文档摄入流水线

        Args:
            loader: 文档加载器
            splitter: 文档切片器
            preprocessor: 预处理器
            document_manager: 文档管理器
            enable_vector_store: 是否启用向量存储
        """
        self.loader = loader or PDFLoader()
        self.splitter = splitter or TextSplitter()
        self.preprocessor = preprocessor or MetadataPreprocessor()
        self.document_manager = document_manager or DocumentManager()
        self.enable_vector_store = enable_vector_store

        logger.info("Document ingestion pipeline initialized")

    def process_document(self,
                         file_path: str,
                         file_id: Optional[str] = None,
                         filename: Optional[str] = None) -> Optional[DocumentMetadata]:
        """
        处理单个文档的完整流程

        Args:
            file_path: 文件路径
            file_id: 文件ID，如果为None则自动生成
            filename: 文件名，如果为None则从路径提取

        Returns:
            DocumentMetadata对象，如果文档已存在则返回None
        """
        try:
            # 参数处理
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            if file_id is None:
                file_id = str(uuid.uuid4())

            if filename is None:
                filename = Path(file_path).name

            logger.info(f"Processing document: {filename} (ID: {file_id})")

            # 检查文档是否已存在
            if self.document_manager.document_exists(file_id):
                logger.info(f"Document {file_id} already exists")
                return None

            # 步骤1: 加载文档
            logger.info(f"Loading document: {filename}")
            text = self.loader.load(file_path)

            # 步骤2: 切片文档
            logger.info(f"Splitting document into chunks")
            chunks = self.splitter.split(text)
            logger.info(f"Document split into {len(chunks)} chunks")

            # 步骤3: 预处理（添加元数据）
            logger.info(f"Preprocessing chunks with metadata")
            processed_chunks = self.preprocessor.process(chunks, filename)

            # 步骤4: 保存到文档管理器
            logger.info(f"Saving document metadata")
            file_hash = self.document_manager._calculate_file_hash(file_path)

            # 检查重复文档
            existing_doc = self.document_manager.get_document_by_hash(file_hash)
            if existing_doc:
                logger.info(f"Document {filename} already exists with ID {existing_doc.file_id}")
                return None

            # 创建文档元数据
            metadata = DocumentMetadata(
                file_id=file_id,
                filename=filename,
                file_hash=file_hash,
                chunk_count=len(chunks),
                upload_time=datetime.datetime.now().isoformat(),
                chunks=chunks  # 保存原始chunks
            )

            # 保存到文档管理器
            self.document_manager.documents[file_id] = metadata
            self.document_manager._save_metadata()

            # 步骤5: 添加到向量存储（如果启用），按配置使用 Pinecone 或 FAISS
            if self.enable_vector_store:
                logger.info(f"Adding document to vector store")
                texts = [chunk["text"] for chunk in processed_chunks]
                metadatas = [chunk["metadata"] for chunk in processed_chunks]

                from infra.container import AppContainer
                if AppContainer.USE_PINECONE:
                    from rag.vector_store.pinecone_store import get_pinecone_store
                    store = get_pinecone_store()
                    store.add_texts_with_metadata(texts, metadatas)
                else:
                    from rag.vector_store.faiss_store import add_documents_to_vector_database_with_metadata
                    add_documents_to_vector_database_with_metadata(texts, metadatas)
                logger.info(f"Document added to vector store")

            logger.info(f"Successfully processed document: {filename}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to process document {filename}: {e}", exc_info=True)
            raise

    def process_documents_batch(self,
                                file_paths: List[str],
                                file_ids: Optional[List[str]] = None,
                                filenames: Optional[List[str]] = None) -> List[DocumentMetadata]:
        """
        批量处理文档

        Args:
            file_paths: 文件路径列表
            file_ids: 文件ID列表，如果为None则自动生成
            filenames: 文件名列表，如果为None则从路径提取

        Returns:
            成功处理的DocumentMetadata列表
        """
        if file_ids is None:
            file_ids = [None] * len(file_paths)

        if filenames is None:
            filenames = [None] * len(file_paths)

        if len(file_paths) != len(file_ids) or len(file_paths) != len(filenames):
            raise ValueError("file_paths, file_ids, and filenames must have the same length")

        results = []
        for i, file_path in enumerate(file_paths):
            try:
                metadata = self.process_document(
                    file_path=file_path,
                    file_id=file_ids[i],
                    filename=filenames[i]
                )
                if metadata:
                    results.append(metadata)
            except Exception as e:
                logger.error(f"Failed to process document {file_path}: {e}")
                continue

        logger.info(f"Batch processing completed: {len(results)}/{len(file_paths)} documents processed successfully")
        return results

    def get_document_chunks(self, file_id: str) -> List[Dict[str, Any]]:
        """获取文档的chunks（带元数据）"""
        return self.document_manager.get_document_chunks_with_metadata(file_id)

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """获取所有文档的chunks（带元数据）"""
        return self.document_manager.get_all_chunks_with_metadata()

    def remove_document(self, file_id: str) -> bool:
        """删除文档"""
        return self.document_manager.remove_document(file_id)

    def list_documents(self) -> List[str]:
        """列出所有文档ID"""
        return list(self.document_manager.documents.keys())


# 便利函数
def create_default_pipeline(enable_vector_store: bool = True) -> DocumentIngestionPipeline:
    """创建默认的文档摄入流水线"""
    return DocumentIngestionPipeline(enable_vector_store=enable_vector_store)


def process_single_document(file_path: str,
                            file_id: Optional[str] = None,
                            filename: Optional[str] = None,
                            enable_vector_store: bool = True) -> Optional[DocumentMetadata]:
    """
    处理单个文档的便利函数

    Args:
        file_path: 文件路径
        file_id: 文件ID
        filename: 文件名
        enable_vector_store: 是否启用向量存储

    Returns:
        DocumentMetadata对象
    """
    pipeline = create_default_pipeline(enable_vector_store)
    return pipeline.process_document(file_path, file_id, filename)


def process_document_directory(directory_path: str,
                               enable_vector_store: bool = True) -> List[DocumentMetadata]:
    """
    处理目录下所有文档的便利函数

    Args:
        directory_path: 目录路径
        enable_vector_store: 是否启用向量存储

    Returns:
        成功处理的DocumentMetadata列表
    """
    directory = Path(directory_path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    # 支持的文件扩展名
    supported_extensions = {'.pdf', '.txt', '.md', '.docx'}

    # 查找所有支持的文件
    file_paths = []
    for ext in supported_extensions:
        file_paths.extend(directory.glob(f'*{ext}'))
        file_paths.extend(directory.glob(f'*{ext.upper()}'))

    if not file_paths:
        logger.warning(f"No supported files found in directory: {directory_path}")
        return []

    # 转换为字符串路径
    file_paths = [str(path) for path in file_paths]

    # 批量处理
    pipeline = create_default_pipeline(enable_vector_store)
    return pipeline.process_documents_batch(file_paths)