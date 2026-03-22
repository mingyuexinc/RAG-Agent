"""
聊天界面组件
"""
from typing import Tuple, List, Dict
import gradio as gr
from frontend.components.image_display import ImageDisplay
from frontend.services import api_client, state_manager
from infra.logs.logger_config import get_logger
# 使用统一的日志配置
logger = get_logger("frontend.components.chat_interface")

class ChatInterface:
    """聊天界面组件"""
    def __init__(self):
        """初始化聊天界面组件"""
        # 在创建组件前先更新连接状态
        try:
            is_connected = api_client.health_check()
            state_manager.is_connected = is_connected
            logger.info(f"组件初始化时连接状态: {is_connected}")
        except Exception as e:
            logger.error(f"初始化健康检查失败: {e}")
            state_manager.is_connected = False
        self.chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            sanitize_html=False,  # 允许HTML渲染
        )
        self.msg = gr.Textbox(
            label="请输入您的问题",
            placeholder="例如：请生成一个银行客户经理考核流程图",
            lines=2
        )
        self.submit_btn = gr.Button("发送", variant="primary")
        self.clear_btn = gr.Button("清空对话", variant="secondary")
        # 使用更新后的状态初始化
        current_status = state_manager.get_status_text()
        logger.info(f"状态组件初始值: {current_status}")
        self.status = gr.Textbox(
            value=current_status,
            label="状态",
            interactive=False
        )
        # 添加图片显示组件
        self.image_display = ImageDisplay()

    def setup_events(self):
        """设置事件处理"""
        # 发送消息事件
        submit_events = [
            self.msg.submit(self._handle_message, [self.msg], [self.msg, self.chatbot, self.status]),
            self.submit_btn.click(self._handle_message, [self.msg], [self.msg, self.chatbot, self.status])
        ]
        # 清空对话事件
        self.clear_btn.click(
            self._clear_chat,
            outputs=[self.chatbot]
        )
        return submit_events

    def _handle_message(self, message: str):
        if not message.strip():
            return "", state_manager.get_chat_history_for_gradio(), state_manager.get_status_text()

        state_manager.add_message("user", message)

        try:
            response = api_client.chat(
                query=message,
                session_id=state_manager.session_id
            )

            # ❗关键：先判断是不是异常响应
            if not isinstance(response, dict):
                raise ValueError("响应不是dict")

            if "error" in response:
                assistant_content = f"❌ 请求失败: {response['error']}"

            else:
                # ✅ 容错解析（核心）
                task_type = response.get("task_type", "unknown")
                answer = response.get("answer", "")
                payload = response.get("payload") or {}

                # -------- 流程图处理 --------
                if task_type == "flowchart_generation":

                    chart_url = payload.get("chart_url")
                    api_path = payload.get("api_path")

                    if api_path:
                        image_url = f"{api_client.base_url}{api_path}"

                        assistant_content = (
                            f"{answer}\n\n"
                            f"![流程图]({image_url})"
                        )
                    elif chart_url:
                        # fallback：直接用远程图
                        assistant_content = (
                            f"{answer}\n\n"
                            f"![流程图]({chart_url})"
                        )
                    else:
                        assistant_content = answer + "\n\n❌ 流程图生成失败"

                else:
                    assistant_content = answer

            # ✅ 更新 session_id
            if isinstance(response, dict) and "session_id" in response:
                state_manager.set_session_id(response["session_id"])

            state_manager.add_message("assistant", assistant_content)

        except Exception as e:
            logger.error(f"处理消息异常: {e}", exc_info=True)
            state_manager.add_message("assistant", "❌ 服务异常，请稍后重试")

        return "", state_manager.get_chat_history_for_gradio(), state_manager.get_status_text()

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
