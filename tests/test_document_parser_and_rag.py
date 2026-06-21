import unittest
from pathlib import Path

try:
    from langchain_core.documents import Document
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Project LangChain dependencies are not installed") from exc

from rag.ingestion.document_manager import DocumentManager
from rag.ingestion.pipeline import DocumentIngestionPipeline
from rag.ingestion.preprocessors.metadata_extractor import MetadataExtractor
from tools.langchain.document_parser.normalizer import (
    build_structured_chunks,
    normalize_parser_result,
)
from tools.langchain.knowledge.tool import KnowledgeSearchTool


class InMemoryDocumentManager(DocumentManager):
    def __init__(self):
        self.documents = {}
        self.metadata_extractor = MetadataExtractor()

    def _save_metadata(self):
        return None


class FakeVectorStore:
    def __init__(self):
        self.last_k = None
        self.last_query = None

    def similarity_search_with_score(self, query, k):
        self.last_query = query
        self.last_k = k
        docs = [
            Document(
                page_content="chapter one content",
                metadata={
                    "title": "Demo",
                    "section_path": "Demo > Chapter 1",
                    "heading": "Chapter 1",
                    "page_number": 1,
                    "block_type": "section",
                    "file_id": "file-1",
                },
            ),
            Document(
                page_content="chapter two content",
                metadata={
                    "title": "Demo",
                    "section_path": "Demo > Chapter 2",
                    "heading": "Chapter 2",
                    "page_number": 2,
                    "block_type": "section",
                    "file_id": "file-2",
                },
            ),
        ]
        return [(docs[0], 0.1), (docs[1], 0.2)]


class DocumentParserAndRagTests(unittest.TestCase):
    def test_normalize_markdown_result_extracts_structure(self):
        parsed = normalize_parser_result(
            {
                "markdown": "# Annual Report\n\nIntro paragraph.\n\n## Metrics\n\n| A | B |\n| - | - |\n| 1 | 2 |"
            },
            file_path="/tmp/report.pdf",
            filename="report.pdf",
        )

        self.assertEqual(parsed["title"], "Annual Report")
        self.assertEqual(parsed["sections"][0]["heading"], "Annual Report")
        self.assertEqual(parsed["sections"][1]["heading"], "Metrics")
        self.assertEqual(parsed["paragraphs"][0]["text"], "Intro paragraph.")
        self.assertGreaterEqual(len(parsed["tables"]), 1)

    def test_build_structured_chunks_preserves_rag_metadata(self):
        parsed = normalize_parser_result(
            {"markdown": "# Title\n\n## Section A\n\nBody text."},
            file_path="/tmp/demo.pdf",
            filename="demo.pdf",
        )

        chunks = build_structured_chunks(parsed, "demo.pdf")

        self.assertEqual(chunks[0]["metadata"]["title"], "Title")
        self.assertEqual(chunks[0]["metadata"]["heading"], "Section A")
        self.assertEqual(chunks[0]["metadata"]["section_path"], "Title > Section A")
        self.assertEqual(chunks[0]["metadata"]["block_type"], "section")

    def test_knowledge_search_supports_top_k_and_filters(self):
        fake_store = FakeVectorStore()
        tool = KnowledgeSearchTool(vector_store=fake_store)

        result = tool.execute(
            query="chapter",
            top_k=1,
            filters={"file_id": "file-1"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(fake_store.last_k, 20)
        documents = result["data"]["documents"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["metadata"]["file_id"], "file-1")
        self.assertEqual(documents[0]["metadata"]["block_type"], "section")

    def test_ingestion_uses_parser_metadata_when_available(self):
        parsed = normalize_parser_result(
            {"markdown": "# Parsed Title\n\n## Parsed Section\n\nParsed body."},
            file_path="/tmp/source.txt",
            filename="source.txt",
        )

        file_path = Path.cwd() / "data" / "test_source.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("fallback text", encoding="utf-8")

        pipeline = DocumentIngestionPipeline(
            document_manager=InMemoryDocumentManager(),
            enable_vector_store=False,
        )
        pipeline._parse_document_with_mcp = lambda _path, _filename: parsed

        metadata = pipeline.process_document(
            str(file_path),
            file_id="file-1",
            filename="source.txt",
        )

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.chunk_count, 1)
        stored_chunks = pipeline.get_document_chunks("file-1")
        self.assertEqual(stored_chunks[0]["metadata"]["file_id"], "file-1")


if __name__ == "__main__":
    unittest.main()
