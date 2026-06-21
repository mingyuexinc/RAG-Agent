import os
import sys
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

from infra.config.base_config import BaseConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class MCPConfig(BaseConfig):
    """Configuration for MCP-backed external tools."""

    @staticmethod
    def _truthy(value: str) -> bool:
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    @property
    def DOCUMENT_PARSER_ENABLED(self) -> bool:
        return self._truthy(os.getenv("MCP_DOCUMENT_PARSER_ENABLED", "true"))

    @property
    def MINERU_API_TOKEN(self) -> str:
        return os.getenv("MINERU_API_TOKEN") or os.getenv("MINERU_API_KEY", "")

    @property
    def MINERU_OUTPUT_DIR(self) -> str:
        default_dir = PROJECT_ROOT / "data" / "mineru"
        output_dir = Path(os.getenv("MINERU_OUTPUT_DIR", str(default_dir)))
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir)

    @property
    def MINERU_TRANSPORT(self) -> str:
        return os.getenv("MINERU_TRANSPORT", "stdio").strip().lower()

    @property
    def MINERU_HTTP_URL(self) -> str:
        return os.getenv("MINERU_HTTP_URL", "http://127.0.0.1:8001/mcp")

    @property
    def MINERU_COMMAND(self) -> str:
        configured = os.getenv("MINERU_COMMAND")
        if configured:
            return configured

        scripts_dir = Path(sys.executable).resolve().parent / "Scripts"
        uvx_path = scripts_dir / "uvx.exe"
        if uvx_path.exists():
            return str(uvx_path)

        uv_path = scripts_dir / "uv.exe"
        if uv_path.exists():
            return str(uv_path)

        return "uvx"

    @property
    def MINERU_ARGS(self) -> list[str]:
        default_args = "mineru-open-mcp"
        if Path(self.MINERU_COMMAND).name.lower() == "uv.exe":
            default_args = "tool run mineru-open-mcp"

        raw_args = os.getenv("MINERU_ARGS", default_args)
        return [arg for arg in raw_args.split() if arg]

    def mineru_connection(self) -> Dict[str, Any]:
        if self.MINERU_TRANSPORT in {"http", "streamable-http", "streamable_http"}:
            return {
                "transport": "streamable_http",
                "url": self.MINERU_HTTP_URL,
            }

        env = {"OUTPUT_DIR": self.MINERU_OUTPUT_DIR}
        if self.MINERU_API_TOKEN:
            env["MINERU_API_TOKEN"] = self.MINERU_API_TOKEN
            env["MINERU_API_KEY"] = self.MINERU_API_TOKEN

        return {
            "transport": "stdio",
            "command": self.MINERU_COMMAND,
            "args": self.MINERU_ARGS,
            "env": env,
        }
