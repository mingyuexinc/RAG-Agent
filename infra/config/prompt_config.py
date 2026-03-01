from pathlib import Path
from infra.config.base_config import BaseConfig


class PromptConfig(BaseConfig):
    # 基于配置文件位置动态计算项目根目录
    @classmethod
    def _get_project_root(cls) -> Path:
        """获取项目根目录"""
        return Path(__file__).resolve().parent.parent.parent

    @classmethod
    def _get_prompts_root(cls) -> Path:
        """获取提示词根目录"""
        return cls._get_project_root() / "agent" / "prompts"

    @property
    def TEMPLATES_DIR(self) -> str:
        """提示词模板目录"""
        templates_dir = self._get_prompts_root() / "templates"
        # 确保目录存在
        templates_dir.mkdir(parents=True, exist_ok=True)
        return str(templates_dir)

    @property
    def BASE_DIR(self) -> str:
        """提示词基础目录（用于PromptManager）"""
        return str(self._get_prompts_root())

    # 预定义的模板路径
    TEMPLATE_KNOWLEDGE_QA = "templates/knowledge_qa_template.txt"
    TEMPLATE_CONTEXT_ANALYSIS = "templates/context_analysis_template.txt"
    TEMPLATE_PLANNER = "templates/planner_template.txt"
    TEMPLATE_SUMMARIZER = "templates/summarizer_template.txt"
