import threading
from typing import Dict, Any, Optional
from datetime import datetime

from agent.orchestrator.executor import ExecutionContext
from infra.config.app_config import AppConfig


class SessionManager:
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_lock = threading.Lock()
        self.session_timeout = session_timeout

    def create_session(self,session_id: str,user_id: str = None) -> str:
        with self.session_lock:
            self.sessions[session_id] = {
                "context": ExecutionContext(max_size=AppConfig.agent.MAX_CONTENT_SIZE),
                "created_at": datetime.now(),
                "last_access": datetime.now(),
                "user_id": user_id
            }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.session_lock:
            session = self.sessions.get(session_id)
            if not session:
                return None

            if self._is_session_expired(session):
                del self.sessions[session_id]
                return None
            session["last_access"] = datetime.now()
        return session

    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        now = datetime.now()
        last_access = session["last_access"]
        return (now - last_access).seconds > self.session_timeout