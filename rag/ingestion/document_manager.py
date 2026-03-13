import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from infra.config.app_config import AppConfig
from infra.logs.logger_config import setup_logger
from rag.ingestion.loaders.pdf_loader import data_loader_core
from rag.ingestion.preprocessors.metadata_extractor import DocumentMetadata, MetadataExtractor

# 使用项目统一的 logger 配置
logger = setup_logger("rag.data_loader")

class DocumentManager:
    """文档管理器，负责文档的元数据管理和去重"""

    def __init__(self):
        self.metadata_dir = Path(AppConfig.vector.FILE_LOAD_PATH) / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.metadata_dir / "documents.json"
        self.metadata_extractor = MetadataExtractor()
        self._load_metadata()

    def _load_metadata(self):
        """加载文档元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents = {doc_id: DocumentMetadata.from_dict(doc_data)
                                      for doc_id, doc_data in data.items()}
            except Exception as e:
                logging.error(f"Failed to load document metadata: {e}")
                self.documents = {}
        else:
            self.documents = {}

    def _save_metadata(self):
        """保存文档元数据"""
        try:
            data = {doc_id: doc_meta.to_dict()
                    for doc_id, doc_meta in self.documents.items()}
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to save document metadata: {e}")

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值用于去重"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def add_document(self, file_path: str, file_id: str, filename: str) -> Optional[DocumentMetadata]:
        """
        添加新文档，自动去重
        :param file_path: 文件路径
        :param file_id: 文件 ID
        :param filename: 文件名
        :return: DocumentMetadata 对象，如果文档已存在则返回 None
        """
        try:
            # 验证文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_path)
            
            # 检查是否已存在相同文档
            for existing_doc in self.documents.values():
                if existing_doc.file_hash == file_hash:
                    logger.info(f"Document {filename} already exists with ID {existing_doc.file_id}")
                    return None
            
            # 处理文档切块
            logger.info(f"Processing new document: {filename}")
            chunks = data_loader_core(file_path)
            
            # 创建元数据
            metadata = DocumentMetadata(
                file_id=file_id,
                filename=filename,
                file_hash=file_hash,
                chunk_count=len(chunks),
                upload_time=datetime.datetime.now().isoformat(),
                chunks=chunks
            )
            
            # 保存元数据
            self.documents[file_id] = metadata
            self._save_metadata()
            
            logger.info(f"Added new document: {filename} with {len(chunks)} chunks")
            return metadata
        except Exception as e:
            logger.error(f"Failed to add document: {e}", exc_info=True)
            raise
    
    def get_document_chunks_with_metadata(self, file_id: str) -> List[Dict[str, Any]]:
        """
        获取带 metadata 的 chunks 列表（带增强的文档语义前缀）
        :param file_id: 文档 ID
        :return: [{"text": "...", "metadata": {...}}, ...]
        """
        doc = self.documents.get(file_id)
        if not doc:
            return []
        
        # 提取文档类型和语义前缀
        doc_type, type_prefix = self.metadata_extractor.extract_semantic_prefix(doc.filename)
        
        # 生成引导文本
        guide_text = self.metadata_extractor.generate_guide_text(doc_type, doc.filename)
        
        return [
            {
                "text": f"{guide_text}{chunk}",
                "metadata": {
                    "source": doc.filename,
                    "file_id": doc.file_id,
                    "file_hash": doc.file_hash,
                    "chunk_index": idx,
                    "total_chunks": doc.chunk_count,
                    "document_type": doc_type
                }
            }
            for idx, chunk in enumerate(doc.chunks)
        ]
    
    def get_all_chunks_with_metadata(self) -> List[Dict[str, Any]]:
        """
        获取所有文档的带 metadata 的 chunks（带增强的文档语义前缀）
        :return: [{"text": "...", "metadata": {...}}, ...]
        """
        all_chunks = []
        for doc in self.documents.values():
            doc_type, type_prefix = self.metadata_extractor.extract_semantic_prefix(doc.filename)
            guide_text = self.metadata_extractor.generate_guide_text(doc_type, doc.filename)
            
            all_chunks.extend([
                {
                    "text": f"{guide_text}{chunk}",
                    "metadata": {
                        "source": doc.filename,
                        "file_id": doc.file_id,
                        "file_hash": doc.file_hash,
                        "chunk_index": idx,
                        "total_chunks": doc.chunk_count,
                        "document_type": doc_type
                    }
                }
                for idx, chunk in enumerate(doc.chunks)
            ])
        return all_chunks

    def get_all_chunks(self) -> List[str]:
        """获取所有文档的chunks"""
        all_chunks = []
        for doc in self.documents.values():
            all_chunks.extend(doc.chunks)
        return all_chunks

    def remove_document(self, file_id: str) -> bool:
        """删除文档"""
        if file_id in self.documents:
            del self.documents[file_id]
            self._save_metadata()
            logging.info(f"Removed document with ID: {file_id}")
            return True
        return False

    def document_exists(self, file_id: str) -> bool:
        """检查文档是否存在"""
        return file_id in self.documents

    def get_document_by_hash(self, file_hash: str) -> Optional[DocumentMetadata]:
        """根据文件哈希查找文档"""
        for doc in self.documents.values():
            if doc.file_hash == file_hash:
                return doc
        return None
