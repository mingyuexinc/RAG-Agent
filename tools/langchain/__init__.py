"""
LangChain工具模块
提供模块化的工具实现，使用装饰器自动注册

使用方式：
    from tools.langchain import ToolRegistry
    from tools.langchain.knowledge import KnowledgeSearchTool

自动注册机制：
    导入工具类时会自动触发@ToolRegistry.register装饰器，
    将工具注册到ToolRegistry中，无需手动维护工具列表。
"""
# 导入注册中心
from .registry import ToolRegistry

# 导入工具类以触发自动注册
# 注意：导入顺序很重要，必须先导入base，再导入具体工具
from .knowledge.tool import KnowledgeSearchTool
from .summarizer.tool import SummarizerTool
from .chart_gen.tool import ChartGenTool
from .document_parser.tool import DocumentParserTool

# 导入构建器函数（向后兼容）
from .knowledge import build_knowledge_search_tool, KnowledgeSearchInput
from .summarizer import build_summarizer_tool, SummarizerInput
from .chart_gen import build_chart_gen_tool, ChartGenInput
from .document_parser import build_document_parser_tool, DocumentParserInput

# 向后兼容：保留TOOL_BUILDERS，但使用动态构建
# 建议使用ToolRegistry.build_tool()替代
TOOL_BUILDERS = {
    "knowledge_search": build_knowledge_search_tool,
    "summarizer": build_summarizer_tool,
    "chart_gen": build_chart_gen_tool,
    "document_parser": build_document_parser_tool,
}

# 导出所有公共接口
__all__ = [
    # 注册中心
    "ToolRegistry",
    # 工具类
    "KnowledgeSearchTool",
    "SummarizerTool",
    "ChartGenTool",
    "DocumentParserTool",
    # 向后兼容：工具构建器
    "TOOL_BUILDERS",
    "build_knowledge_search_tool",
    "build_summarizer_tool",
    "build_chart_gen_tool",
    "build_document_parser_tool",
    # 输入模型
    "KnowledgeSearchInput",
    "SummarizerInput",
    "ChartGenInput",
    "DocumentParserInput",
]

