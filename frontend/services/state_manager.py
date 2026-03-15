"""
应用状态管理
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from infra.logs.logger_config import setup_logger

# 使用统一的日志配置
logger = setup_logger("frontend.services.state_manager")


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""


class StateManager:
    """应用状态管理器"""
    
    def __init__(self):
        self.session_id: Optional[str] = None
        self.chat_history: List[ChatMessage] = []
        self.uploaded_files: List[Dict[str, Any]] = []
        self.is_connected: bool = False
    
    def add_message(self, role: str, content: str):
        """添加聊天消息"""
        import datetime
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.datetime.now().strftime("%H:%M:%S")
        )
        self.chat_history.append(message)
        logger.info(f"添加消息: {role} - {len(content)} 字符")
    
    def get_chat_history_for_gradio(self) -> List[Dict[str, str]]:
        """获取Gradio格式的聊天历史"""
        return [
            {"role": msg.role, "content": msg.content} 
            for msg in self.chat_history
        ]
    
    def set_session_id(self, session_id: str):
        """设置会话ID"""
        old_session_id = self.session_id
        self.session_id = session_id
        logger.info(f"会话ID更新: {old_session_id} -> {session_id}")
        
        if session_id:
            logger.info(f"当前会话状态: 已建立会话 ({session_id[:8]}...)")
        else:
            logger.info("当前会话状态: 无会话ID")
    
    def add_uploaded_file(self, file_info: Dict[str, Any]):
        """添加上传文件信息"""
        self.uploaded_files.append(file_info)
        logger.info(f"添加上传文件: {file_info.get('filename', 'unknown')}")
    
    def clear_chat_history(self):
        """清空聊天历史"""
        self.chat_history.clear()
        logger.info("清空聊天历史")
    
    def get_status_text(self) -> str:
        """获取状态文本"""
        if not self.is_connected:
            return "🔴 未连接到后端服务"
        elif self.session_id:
            return f"🟢 已连接 (会话: {self.session_id[:8]}...)"
        else:
            return "🟡 已连接，未建立会话"


# 全局状态管理器实例
state_manager = StateManager()
