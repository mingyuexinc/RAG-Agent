"""
聊天界面组件
"""
import gradio as gr
from typing import Tuple, Optional, List, Dict
from frontend.services import api_client, state_manager
from infra.logs.logger_config import setup_logger

# 使用统一的日志配置
logger = setup_logger("frontend.components.chat_interface")


class ChatInterface:
    """聊天界面组件"""
    
    def __init__(self):
        self.chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            type="messages",
        )
        
        self.msg = gr.Textbox(
            label="",
            placeholder="输入您的问题...",
            lines=2,
            max_lines=8,
            show_label=False,
        )
        
        self.submit_btn = gr.Button("发送", variant="primary")
        self.clear_btn = gr.Button("清空对话", variant="secondary")
        
        self.status = gr.Textbox(
            value=state_manager.get_status_text(),
            label="状态",
            interactive=False
        )
    
    def setup_events(self):
        """设置事件处理"""
        # 发送消息事件
        submit_events = [
            self.msg.submit(self._handle_message, [self.msg], [self.msg, self.chatbot]),
            self.submit_btn.click(self._handle_message, [self.msg], [self.msg, self.chatbot])
        ]
        
        # 清空对话事件
        self.clear_btn.click(
            self._clear_chat,
            outputs=[self.chatbot]
        )
        
        return submit_events
    
    def _handle_message(self, message: str) -> Tuple[str, List[Dict[str, str]]]:
        """处理用户消息"""
        if not message.strip():
            return "", state_manager.get_chat_history_for_gradio()
        
        # 记录当前session状态
        current_session_id = state_manager.session_id
        logger.info(f"处理消息前session_id: {current_session_id}")
        
        # 添加用户消息
        state_manager.add_message("user", message)
        
        # 显示用户消息
        chat_history = state_manager.get_chat_history_for_gradio()
        
        # 调用API获取回复
        try:
            current_session_id = state_manager.session_id
            logger.info(f"发送API请求，携带session_id: {current_session_id}")
            
            # 即使session_id为None也要发送，让后端创建新会话
            response = api_client.chat(
                query=message,
                session_id=current_session_id  # 可能为None，但需要发送
            )
            
            if "error" in response:
                assistant_reply = f"❌ 请求失败: {response['error']}"
            else:
                # 提取回复内容
                answer = response.get("answer", "抱歉，我无法回答这个问题。")
                assistant_reply = answer
                
                # 更新session_id
                if "session_id" in response:
                    new_session_id = response["session_id"]
                    logger.info(f"收到新的session_id: {new_session_id}")
                    state_manager.set_session_id(new_session_id)
                else:
                    logger.warning("响应中未包含session_id")
                
                # 显示任务类型信息
                task_type = response.get("task_type", "unknown")
                if task_type != "unknown":
                    assistant_reply += f"\n\n*(任务类型: {task_type})*"
            
            # 添加助手回复
            state_manager.add_message("assistant", assistant_reply)
            
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            error_reply = "❌ 服务暂时不可用，请稍后重试。"
            state_manager.add_message("assistant", error_reply)
        
        # 更新聊天历史
        chat_history = state_manager.get_chat_history_for_gradio()
        
        return "", chat_history
    
    def _clear_chat(self) -> List[Dict[str, str]]:
        """清空聊天历史"""
        state_manager.clear_chat_history()
        return state_manager.get_chat_history_for_gradio()
    
    def get_layout(self):
        """获取组件布局"""
        with gr.Column(elem_classes=["chat-container"]):
            gr.HTML("<div class='chat-header'>💬 RAG Agent 对话</div>")
            
            self.chatbot.render()
            
            with gr.Row(elem_classes=["input-container"]):
                with gr.Column(scale=4):
                    self.msg.render()
                with gr.Column(scale=1, min_width=100):
                    with gr.Row():
                        self.submit_btn.render()
                        self.clear_btn.render()
            
            self.status.render()
        
        return [self.chatbot, self.msg, self.submit_btn, self.clear_btn, self.status]
    
    def update_status(self):
        """更新状态显示"""
        return state_manager.get_status_text()
