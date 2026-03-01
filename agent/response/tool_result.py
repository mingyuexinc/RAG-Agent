from typing import Dict, Any, Optional


class ToolResult:
    def __init__(self,
                 success: bool,
                 data: Any = None,
                 error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }
