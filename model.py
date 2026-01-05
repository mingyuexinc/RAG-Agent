import logging
import os
import time

from langchain_openai import ChatOpenAI

from config.app_config import AppConfig


class ModelManager:
    def __init__(self,timeout:int):
        self.timeout = timeout
        self._model_instance = None

    def create_model_instance(self) -> ChatOpenAI:
        if self._model_instance is None:
            self._model_instance = ChatOpenAI(
                api_key=os.getenv(AppConfig.model.DASHSCOPE_API_KEY),
                base_url=AppConfig.model.INFERENCE_MODEL_URL,
                model=AppConfig.model.INFERENCE_MODEL_NAME,
                timeout=self.timeout
            )
        return self._model_instance

    def invoke_with_timeout(self,prompt:str):
        start_time = time.time()
        try:
            model = self.create_model_instance()
            response = model.invoke(input=prompt)
            return response
        except Exception as e:
            elapsed_time = time.time() - start_time
            logging.error(f"Model call time out after {elapsed_time}s: {str(e)}")
            return self.fallback_response(prompt)


    def fallback_response(self,prompt:str):
        try:
            result = self._try_backup_model(prompt)
            return result
        except Exception as e:
            logging.error(f"Fallback model call failed: {str(e)}")
        return "系统暂时无法处理，请稍后重试"

    def _try_backup_model(self,prompt:str):
        try:
            backup_model = ChatOpenAI(
                api_key=os.getenv(AppConfig.model.DASHSCOPE_API_KEY),
                base_url=AppConfig.model.INFERENCE_MODEL_URL,
                model = AppConfig.model.DEGRADATION_MODEL_NAME,
                timeout=10
            )
            response = backup_model.invoke(input=prompt)
            return response
        except Exception as e:
            logging.error(f"Backup model call failed: {str(e)}")


