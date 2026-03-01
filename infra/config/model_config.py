from infra.config.base_config import BaseConfig


class ModelConfig(BaseConfig):
    DASHSCOPE_API_KEY = "DASHSCOPE_API_KEY"

    OPENAI_API_KEY = "OPENAI_API_KEY"

    INFERENCE_MODEL_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    INFERENCE_MODEL_NAME = "qwen-plus"

    DEGRADATION_MODEL_NAME = "deepseek-v3.2"

    EMBEDDING_MODEL_NAME = "text-embedding-v2"