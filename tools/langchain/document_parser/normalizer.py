import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def normalize_parser_result(raw_result: Any, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
    markdown = _extract_markdown(raw_result)
    if not markdown:
        markdown = _read_markdown_from_result(raw_result)

    title, sections, paragraphs, tables, images = _parse_markdown(markdown)
    resolved_filename = filename or Path(file_path).name

    if not title:
        title = Path(resolved_filename).stem

    return {
        "title": title,
        "sections": sections,
        "paragraphs": paragraphs,
        "tables": tables,
        "images": images,
        "markdown": markdown,
        "metadata": {
            "source": resolved_filename,
            "file_path": file_path,
            "parser": "mineru_mcp",
            "section_count": len(sections),
            "paragraph_count": len(paragraphs),
            "table_count": len(tables),
            "image_count": len(images),
        },
    }


def build_structured_chunks(parsed: Dict[str, Any], filename: str) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    title = parsed.get("title") or Path(filename).stem

    for section_index, section in enumerate(parsed.get("sections", [])):
        heading = section.get("heading") or title
        section_path = section.get("section_path") or [heading]
        content = section.get("content", "").strip()
        if not content:
            continue

        chunks.append(
            {
                "text": content,
                "metadata": {
                    "source": filename,
                    "title": title,
                    "heading": heading,
                    "section_path": " > ".join(section_path),
                    "section_index": section_index,
                    "page_number": section.get("page_number"),
                    "block_type": "section",
                    "parser": parsed.get("metadata", {}).get("parser", "mineru_mcp"),
                },
            }
        )

    if chunks:
        return chunks

    paragraphs = parsed.get("paragraphs", [])
    for paragraph_index, paragraph in enumerate(paragraphs):
        text = paragraph.get("text", "").strip()
        if not text:
            continue
        chunks.append(
            {
                "text": text,
                "metadata": {
                    "source": filename,
                    "title": title,
                    "heading": paragraph.get("heading") or title,
                    "section_path": paragraph.get("section_path") or title,
                    "section_index": paragraph.get("section_index", 0),
                    "paragraph_index": paragraph_index,
                    "page_number": paragraph.get("page_number"),
                    "block_type": "paragraph",
                    "parser": parsed.get("metadata", {}).get("parser", "mineru_mcp"),
                },
            }
        )

    return chunks


def _extract_markdown(raw_result: Any) -> str:
    if raw_result is None:
        return ""

    if isinstance(raw_result, str):
        return _extract_markdown_from_json_string(raw_result) or raw_result

    if isinstance(raw_result, list):
        parts = [_extract_markdown(item) for item in raw_result]
        return "\n\n".join(part for part in parts if part)

    if not isinstance(raw_result, dict):
        content = getattr(raw_result, "content", None)
        if content is not None:
            return _extract_markdown(content)
        return str(raw_result)

    for key in ("markdown", "md", "content", "text", "result"):
        value = raw_result.get(key)
        if value:
            return _extract_markdown(value)

    data = raw_result.get("data")
    if data:
        return _extract_markdown(data)

    return ""


def _extract_markdown_from_json_string(raw_text: str) -> str:
    stripped = raw_text.strip()
    if not stripped.startswith(("{", "[")):
        return ""

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return ""

    if isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
        parts = []
        for item in parsed["results"]:
            if isinstance(item, dict):
                content = item.get("content") or item.get("markdown") or item.get("text")
                if content:
                    parts.append(str(content))
        return "\n\n".join(parts)

    return _extract_markdown(parsed)


def _read_markdown_from_result(raw_result: Any) -> str:
    candidates: List[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                lowered = str(key).lower()
                if lowered in {"markdown_path", "md_path", "output_path", "path", "file"}:
                    if isinstance(nested, str):
                        candidates.append(nested)
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(raw_result)

    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and path.suffix.lower() in {".md", ".markdown", ".txt"}:
            return path.read_text(encoding="utf-8", errors="ignore")

    return ""


def _parse_markdown(markdown: str):
    title = ""
    sections: List[Dict[str, Any]] = []
    paragraphs: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []

    current_heading = ""
    heading_stack: List[str] = []
    current_lines: List[str] = []

    def flush_section() -> None:
        nonlocal current_lines
        content = "\n".join(current_lines).strip()
        if current_heading and content:
            sections.append(
                {
                    "heading": current_heading,
                    "section_path": heading_stack.copy(),
                    "content": content,
                    "page_number": None,
                }
            )
        current_lines = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush_section()
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            if not title:
                title = heading
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(heading)
            current_heading = heading
            continue

        if line.strip():
            for image_path in IMAGE_RE.findall(line):
                images.append(
                    {
                        "path": image_path,
                        "heading": current_heading,
                        "section_path": " > ".join(heading_stack),
                    }
                )

            if _looks_like_table_row(line):
                tables.append(
                    {
                        "text": line,
                        "heading": current_heading,
                        "section_path": " > ".join(heading_stack),
                    }
                )
            elif not line.lstrip().startswith("|"):
                paragraphs.append(
                    {
                        "text": line.strip(),
                        "heading": current_heading,
                        "section_path": " > ".join(heading_stack),
                        "section_index": len(sections),
                        "page_number": None,
                    }
                )

        current_lines.append(line)

    flush_section()
    return title, sections, paragraphs, tables, images


def _looks_like_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2
