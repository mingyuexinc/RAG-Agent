import os
from typing import Optional


class BaseConfig:
    def get_env_var(self,key:str,default:Optional[str] = None) -> str:
        return os.getenv(key,default)