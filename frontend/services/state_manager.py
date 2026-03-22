"""
应用状态管理
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import datetime

from infra.logs.logger_config import get_logger

# 使用统一的日志配置
logger = get_logger("frontend.services.state_manager")


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user" or "assistant"
    content: str | List[Dict]  # 支持结构化内容
    timestamp: str = ""
    is_structured: bool = False


class StateManager:
    """应用状态管理器"""
    
    def __init__(self):
        self.session_id: Optional[str] = None
        self.chat_history: List[ChatMessage] = []
        self.uploaded_files: List[Dict[str, Any]] = []
        self.is_connected: bool = False
    
    def add_message(self, role, content, is_structured=False):
        """添加聊天消息 - 绝对不做任何转换"""
        import datetime
        
        # 断言检查
        assert not isinstance(content, str) or not is_structured, "结构化消息不能是字符串"
        
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.datetime.now().strftime("%H:%M:%S"),
            is_structured=is_structured
        )
        self.chat_history.append(message)
        logger.info(f"添加消息: {role} - {'结构化' if is_structured else '文本'}")
    
    def get_chat_history_for_gradio(self):
        """获取Gradio格式的聊天历史"""
        history = []
        for msg in self.chat_history:
            # 标准Chatbot使用 (user, assistant) 格式
            if msg.role == "user":
                history.append([msg.content, None])
            elif msg.role == "assistant":
                if history and history[-1][1] is None:
                    history[-1][1] = msg.content
                else:
                    history.append([None, msg.content])
        return history
    
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
