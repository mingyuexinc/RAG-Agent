import datetime
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from infra.logs.logger_config import get_logger
from rag.ingestion.document_manager import DocumentManager
from rag.ingestion.loaders.base_loader import BaseLoader
from rag.ingestion.loaders.loader_factory import get_loader
from rag.ingestion.loaders.pdf_loader import PDFLoader
from rag.ingestion.preprocessors.base_preprocessor import BasePreprocessor, MetadataPreprocessor
from rag.ingestion.preprocessors.metadata_extractor import DocumentMetadata, MetadataExtractor
from rag.ingestion.splitters.base_splitter import BaseSplitter, TextSplitter
from tools.langchain.document_parser import build_document_parser_tool, build_structured_chunks

logger = get_logger("rag.ingestion.pipeline")


class DocumentIngestionPipeline:
    """Document ingestion pipeline for RAG indexing."""

    def __init__(
        self,
        loader: Optional[BaseLoader] = None,
        splitter: Optional[BaseSplitter] = None,
        preprocessor: Optional[BasePreprocessor] = None,
        document_manager: Optional[DocumentManager] = None,
        enable_vector_store: bool = True,
    ):
        self.loader = loader or PDFLoader()
        self.splitter = splitter or TextSplitter()
        self.preprocessor = preprocessor or MetadataPreprocessor()
        self.document_manager = document_manager or DocumentManager()
        self.enable_vector_store = enable_vector_store
        self.metadata_extractor = MetadataExtractor()

        logger.info("Document ingestion pipeline initialized")

    def process_document(
        self,
        file_path: str,
        file_id: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Optional[DocumentMetadata]:
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            if file_id is None:
                file_id = str(uuid.uuid4())

            if filename is None:
                filename = Path(file_path).name

            logger.info(f"Processing document: {filename} (ID: {file_id})")

            if self.document_manager.document_exists(file_id):
                logger.info(f"Document {file_id} already exists")
                return None

            parsed_document = self._parse_document_with_mcp(file_path, filename)
            if parsed_document:
                logger.info("MCP document parser succeeded; building structured chunks")
                processed_chunks = build_structured_chunks(parsed_document, filename)
                chunks = [chunk["text"] for chunk in processed_chunks]
            else:
                logger.info(f"Loading document with legacy loader: {filename}")
                loader = get_loader(file_path, filename)
                text = loader.load(file_path)

                logger.info("Splitting document into chunks")
                chunks = self.splitter.split(text)
                logger.info(f"Document split into {len(chunks)} chunks")

                logger.info("Preprocessing chunks with metadata")
                processed_chunks = self.preprocessor.process(chunks, filename)

            logger.info("Saving document metadata")
            file_hash = self.document_manager._calculate_file_hash(file_path)

            existing_doc = self.document_manager.get_document_by_hash(file_hash)
            if existing_doc:
                logger.info(f"Document {filename} already exists with ID {existing_doc.file_id}")
                return None

            self._enrich_chunk_metadata(
                processed_chunks=processed_chunks,
                parsed_document=parsed_document,
                filename=filename,
                file_id=file_id,
                file_hash=file_hash,
            )

            metadata = DocumentMetadata(
                file_id=file_id,
                filename=filename,
                file_hash=file_hash,
                chunk_count=len(chunks),
                upload_time=datetime.datetime.now().isoformat(),
                chunks=chunks,
            )

            self.document_manager.documents[file_id] = metadata
            self.document_manager._save_metadata()

            if self.enable_vector_store:
                logger.info("Adding document to vector store")
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
                logger.info("Document added to vector store")

            logger.info(f"Successfully processed document: {filename}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to process document {filename}: {e}", exc_info=True)
            raise

    def _parse_document_with_mcp(self, file_path: str, filename: str) -> Optional[Dict[str, Any]]:
        from infra.config.app_config import AppConfig

        if not AppConfig.mcp.DOCUMENT_PARSER_ENABLED:
            logger.info("MCP document parser disabled; using legacy loader")
            return None

        try:
            parser_tool = build_document_parser_tool()
            result = parser_tool.invoke(
                {
                    "file_path": file_path,
                    "filename": filename,
                    "parse_mode": "auto",
                }
            )
            if result.get("success"):
                return result.get("data", {})

            logger.warning(
                f"MCP document parser failed; falling back to legacy loader: {result.get('error')}"
            )
            return None
        except Exception as exc:
            logger.warning(
                f"MCP document parser unavailable; falling back to legacy loader: {exc}",
                exc_info=True,
            )
            return None

    def _enrich_chunk_metadata(
        self,
        processed_chunks: List[Dict[str, Any]],
        parsed_document: Optional[Dict[str, Any]],
        filename: str,
        file_id: str,
        file_hash: str,
    ) -> None:
        doc_type, _ = self.metadata_extractor.extract_semantic_prefix(filename)
        title = parsed_document.get("title") if parsed_document else filename

        for idx, chunk in enumerate(processed_chunks):
            metadata = chunk.setdefault("metadata", {})
            metadata.setdefault("source", filename)
            metadata.setdefault("title", title)
            metadata.setdefault("heading", metadata.get("title"))
            metadata.setdefault("section_path", metadata.get("heading"))
            metadata.setdefault("page_number", None)
            metadata.setdefault("block_type", "chunk")
            metadata.setdefault("document_type", doc_type)
            metadata["file_id"] = file_id
            metadata["file_hash"] = file_hash
            metadata["chunk_index"] = idx
            metadata["total_chunks"] = len(processed_chunks)

    def process_documents_batch(
        self,
        file_paths: List[str],
        file_ids: Optional[List[str]] = None,
        filenames: Optional[List[str]] = None,
    ) -> List[DocumentMetadata]:
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
                    filename=filenames[i],
                )
                if metadata:
                    results.append(metadata)
            except Exception as e:
                logger.error(f"Failed to process document {file_path}: {e}")
                continue

        logger.info(
            f"Batch processing completed: {len(results)}/{len(file_paths)} documents processed successfully"
        )
        return results

    def get_document_chunks(self, file_id: str) -> List[Dict[str, Any]]:
        return self.document_manager.get_document_chunks_with_metadata(file_id)

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        return self.document_manager.get_all_chunks_with_metadata()

    def remove_document(self, file_id: str) -> bool:
        return self.document_manager.remove_document(file_id)

    def list_documents(self) -> List[str]:
        return list(self.document_manager.documents.keys())


def create_default_pipeline(enable_vector_store: bool = True) -> DocumentIngestionPipeline:
    return DocumentIngestionPipeline(enable_vector_store=enable_vector_store)


def process_single_document(
    file_path: str,
    file_id: Optional[str] = None,
    filename: Optional[str] = None,
    enable_vector_store: bool = True,
) -> Optional[DocumentMetadata]:
    pipeline = create_default_pipeline(enable_vector_store)
    return pipeline.process_document(file_path, file_id, filename)


def process_document_directory(
    directory_path: str,
    enable_vector_store: bool = True,
) -> List[DocumentMetadata]:
    directory = Path(directory_path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    supported_extensions = {".pdf", ".txt", ".md", ".docx"}

    file_paths = []
    for ext in supported_extensions:
        file_paths.extend(directory.glob(f"*{ext}"))
        file_paths.extend(directory.glob(f"*{ext.upper()}"))

    if not file_paths:
        logger.warning(f"No supported files found in directory: {directory_path}")
        return []

    pipeline = create_default_pipeline(enable_vector_store)
    return pipeline.process_documents_batch([str(path) for path in file_paths])
