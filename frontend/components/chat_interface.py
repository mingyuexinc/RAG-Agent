"""
聊天界面组件
"""
import gradio as gr
from typing import Tuple, Optional, List, Dict
from frontend.services import api_client, state_manager
from frontend.components.image_display import ImageDisplay
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
    
    def _handle_message(self, message: str) -> Tuple[str, List[Dict[str, str]], str]:
        """处理用户消息"""
        if not message.strip():
            return "", state_manager.get_chat_history_for_gradio(), state_manager.get_status_text()
        
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
                task_type = response.get("task_type", "unknown")
                
                # 初始化assistant_content
                assistant_content = None
                
                # 处理流程图生成任务
                if task_type == "flowchart_generation" and "payload" in response:
                    payload = response["payload"]
                    chart_url = payload.get("chart_url")
                    chart_code = payload.get("chart_code")
                    api_path = payload.get("api_path")
                    
                    logger.info(f"🔍 流程图处理 - chart_url: {chart_url}")
                    logger.info(f"🔍 流程图处理 - api_path: {api_path}")
                    logger.info(f"🔍 流程图处理 - api_client.base_url: {api_client.base_url}")
                    
                    if api_path and chart_url:
                        # 构建文本回复
                        answer = response.get("answer", "已根据制度文档生成流程图。")
                        stats = self.image_display.get_image_stats(payload)
                        assistant_text = answer + ("\n\n" + stats if stats else "")
                        
                        # 使用新的API路径构建完整URL
                        # 使用api_client的base_url，支持动态环境
                        image_url = f"{api_client.base_url}{api_path}"
                        
                        logger.info(f"🔍 流程图处理 - 生成的完整图片URL: {image_url}")
                        
                        # 使用简单的Markdown格式（回到基础方案）
                        assistant_content = f"{assistant_text}\n\n![流程图]({image_url})"
                        
                        logger.info(f"🔍 流程图处理 - 使用Markdown格式，内容长度: {len(assistant_content)}")
                        logger.info(f"🔍 流程图处理 - Markdown内容预览: {assistant_content[:200]}...")
                        
                    else:
                        logger.error(f"❌ 流程图处理 - 缺少必要字段: api_path={api_path}, chart_url={chart_url}")
                        assistant_content = response.get("answer", "已根据制度文档生成流程图。") + "\n\n❌ 流程图生成失败"
                else:
                    assistant_content = response.get("answer", "抱歉，我无法回答这个问题。")
                
                # 更新session_id
                if "session_id" in response:
                    new_session_id = response["session_id"]
                    logger.info(f"收到新的session_id: {new_session_id}")
                    state_manager.set_session_id(new_session_id)
                else:
                    logger.warning("响应中未包含session_id")
                
                # 显示任务类型信息（非流程图任务）
                if task_type != "unknown" and task_type != "flowchart_generation":
                    if isinstance(assistant_content, str):
                        assistant_content += f"\n\n*(任务类型: {task_type})*"
                    # 如果是结构化消息，不添加任务类型
            
            # 添加助手回复（普通文本格式）
            if assistant_content is not None:
                state_manager.add_message("assistant", assistant_content)
        
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            error_reply = "❌ 服务暂时不可用，请稍后重试。"
            state_manager.add_message("assistant", error_reply)
        
        # 更新聊天历史
        chat_history = state_manager.get_chat_history_for_gradio()
        
        return "", chat_history, state_manager.get_status_text()
    
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
