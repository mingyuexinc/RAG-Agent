from abc import ABC, abstractmethod
from typing import List, Dict, Any

from rag.ingestion.preprocessors.metadata_extractor import MetadataExtractor


class BasePreprocessor(ABC):
    """预处理器抽象基类"""

    @abstractmethod
    def process(self, chunks: List[str], filename: str) -> List[Dict[str, Any]]:
        """预处理文档块"""
        pass


class MetadataPreprocessor(BasePreprocessor):
    """元数据预处理器"""

    def __init__(self):
        self.metadata_extractor = MetadataExtractor()

    def process(self, chunks: List[str], filename: str) -> List[Dict[str, Any]]:
        """为chunks添加元数据"""
        doc_type, _ = self.metadata_extractor.extract_semantic_prefix(filename)
        guide_text = self.metadata_extractor.generate_guide_text(doc_type, filename)

        processed_chunks = []
        for idx, chunk in enumerate(chunks):
            processed_chunks.append({
                "text": f"{guide_text}{chunk}",
                "metadata": {
                    "source": filename,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "document_type": doc_type
                }
            })

        return processed_chunks