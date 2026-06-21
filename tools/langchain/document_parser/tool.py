import asyncio
import threading
from typing import Any, Dict, Optional

from langchain_core.tools import StructuredTool

from infra.config.app_config import AppConfig
from ..base import BaseLangChainTool
from ..registry import ToolRegistry
from .input import DocumentParserInput
from .normalizer import normalize_parser_result


@ToolRegistry.register(
    name="document_parser",
    task_types=["document_ingestion"],
    description="Parse structured documents through MinerU MCP before RAG indexing",
)
class DocumentParserTool(BaseLangChainTool):
    name = "document_parser"
    description = "Parse structured documents through MinerU MCP before RAG indexing"
    task_types = ["document_ingestion"]
    dependencies = []
    metadata = {
        "output_key": "document_parser.result",
        "set_inputs_to_context": True,
        "input_keys": ["file_path", "filename"],
    }

    def execute(
        self,
        file_path: str,
        filename: Optional[str] = None,
        page_ranges: Optional[str] = None,
        ocr_language: Optional[str] = None,
        parse_mode: Optional[str] = "auto",
    ) -> Dict[str, Any]:
        try:
            if not AppConfig.mcp.DOCUMENT_PARSER_ENABLED:
                raise RuntimeError("MCP document parser is disabled")

            raw_result = _run_async(
                self._call_mineru(
                    file_path=file_path,
                    filename=filename,
                    page_ranges=page_ranges,
                    ocr_language=ocr_language,
                    parse_mode=parse_mode,
                )
            )
            normalized = normalize_parser_result(raw_result, file_path=file_path, filename=filename)
            return self.handle_success(normalized)
        except Exception as exc:
            return self.handle_error(exc)

    async def _call_mineru(
        self,
        file_path: str,
        filename: Optional[str],
        page_ranges: Optional[str],
        ocr_language: Optional[str],
        parse_mode: Optional[str],
    ) -> Any:
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError as exc:
            raise RuntimeError(
                "langchain-mcp-adapters is required for document_parser. "
                "Install project requirements before enabling MCP parsing."
            ) from exc

        client = MultiServerMCPClient({"mineru": AppConfig.mcp.mineru_connection()})
        tools = await client.get_tools()
        parser_tool = next((tool for tool in tools if tool.name == "parse_documents"), None)
        if parser_tool is None:
            available = ", ".join(tool.name for tool in tools)
            raise RuntimeError(f"MinerU MCP tool parse_documents not found. Available: {available}")

        payload = _build_mineru_payload(
            parser_tool=parser_tool,
            file_path=file_path,
            filename=filename,
            page_ranges=page_ranges,
            ocr_language=ocr_language,
            parse_mode=parse_mode,
        )
        return await parser_tool.ainvoke(payload)


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: Dict[str, Any] = {}

    def runner():
        try:
            result["value"] = asyncio.run(coro)
        except Exception as exc:
            result["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]
    return result.get("value")


def _build_mineru_payload(
    parser_tool: Any,
    file_path: str,
    filename: Optional[str],
    page_ranges: Optional[str],
    ocr_language: Optional[str],
    parse_mode: Optional[str],
) -> Dict[str, Any]:
    args = set((getattr(parser_tool, "args", None) or {}).keys())
    if not args:
        return {
            "file_path": file_path,
            "filename": filename,
            "page_ranges": page_ranges,
            "ocr_language": ocr_language,
            "parse_mode": parse_mode or "auto",
            "output_dir": AppConfig.mcp.MINERU_OUTPUT_DIR,
        }

    payload: Dict[str, Any] = {}

    if "file_sources" in args:
        if page_ranges:
            payload["file_sources"] = [{"source": file_path, "pages": page_ranges}]
        else:
            payload["file_sources"] = [file_path]

    for key in ("file_path", "path", "source", "url"):
        if key in args:
            payload[key] = file_path
            break

    for key in ("file_paths", "paths", "sources", "files"):
        if key in args:
            payload[key] = [file_path]
            break

    key_values = {
        "filename": filename,
        "pages": page_ranges,
        "page_ranges": page_ranges,
        "language": ocr_language,
        "ocr_language": ocr_language,
        "mode": parse_mode,
        "parse_mode": parse_mode,
        "output_dir": AppConfig.mcp.MINERU_OUTPUT_DIR,
    }
    for key, value in key_values.items():
        if key in args and value not in (None, ""):
            payload[key] = value

    return payload


def build_document_parser_tool() -> StructuredTool:
    tool = DocumentParserTool()
    return StructuredTool.from_function(
        func=tool.execute,
        name=tool.name,
        description=tool.description,
        args_schema=DocumentParserInput,
        metadata=tool.metadata,
    )
