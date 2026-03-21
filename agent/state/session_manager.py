import threading
from typing import Dict, Any, Optional
from datetime import datetime

from agent.orchestrator.executor import ExecutionContext
from infra.config.app_config import AppConfig
from infra.logs.logger_config import get_logger

# 添加会话管理日志
logger = get_logger("agent.session_manager")


class SessionManager:
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_lock = threading.Lock()
        self.session_timeout = session_timeout
        logger.info(f"SessionManager 初始化完成，超时时间: {session_timeout}秒")

    def create_session(self,session_id: str,user_id: str = None) -> str:
        logger.info(f"创建会话，session_id: {session_id}, user_id: {user_id}")
        
        with self.session_lock:
            self.sessions[session_id] = {
                "context": ExecutionContext(max_size=AppConfig.agent.MAX_CONTENT_SIZE),
                "created_at": datetime.now(),
                "last_access": datetime.now(),
                "user_id": user_id
            }
            logger.info(f"会话创建成功，当前会话数量: {len(self.sessions)}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        logger.info(f"获取会话，session_id: {session_id}")
        
        with self.session_lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"会话不存在，session_id: {session_id}")
                return None

            if self._is_session_expired(session):
                logger.info(f"会话已过期，删除会话，session_id: {session_id}")
                del self.sessions[session_id]
                return None
                
            session["last_access"] = datetime.now()
            logger.info(f"会话获取成功，session_id: {session_id}")
        return session

    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        now = datetime.now()
        last_access = session["last_access"]
        expired = (now - last_access).seconds > self.session_timeout
        if expired:
            logger.info(f"会话过期，最后访问: {last_access}, 当前: {now}, 超时: {self.session_timeout}秒")
        return expired