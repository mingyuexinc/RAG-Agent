import os

from infra.config.app_config import AppConfig


class PromptManager:
    def __init__(self):
        self.base_dir = AppConfig.prompt.BASE_DIR

    def render(self, path: str, **kwargs) -> str:
        full_path = os.path.join(self.base_dir, path)
        with open(full_path, encoding="utf-8") as f:
            template = f.read()
        return template.format(**kwargs)
