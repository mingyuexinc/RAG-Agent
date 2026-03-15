"""
Gradio主应用入口
RAG Agent 前端界面
"""
# 补丁：Gradio 5.17 的 gradio_client 在解析 JSON Schema 时，遇到 additionalProperties: true/false
# 会传入 bool，get_type() 内执行 "const" in schema 导致 TypeError。在创建任何 gr 组件前先打补丁。
try:
    import gradio_client.utils as _gc_utils
    _orig_get_type = getattr(_gc_utils, "get_type", None)
    if callable(_orig_get_type):
        def _patched_get_type(schema):
            if isinstance(schema, bool):
                return "object"
            return _orig_get_type(schema)
        _gc_utils.get_type = _patched_get_type
    # 同时保护 _json_schema_to_python_type：若 schema 为 bool 直接返回 "Any"，避免深入解析
    _orig_json_schema_to_python = getattr(_gc_utils, "_json_schema_to_python_type", None)
    if callable(_orig_json_schema_to_python):
        def _patched_json_schema(schema, defs=None):
            if isinstance(schema, bool):
                return "Any"
            return _orig_json_schema_to_python(schema, defs or {})
        _gc_utils._json_schema_to_python_type = _patched_json_schema
except Exception:
    pass

import gradio as gr
import logging
import time
import threading
from frontend.components import ChatInterface, DocumentUpload
from frontend.services import api_client, state_manager


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGAgentFrontend:
    """RAG Agent 前端应用"""
    
    def __init__(self):
        self.chat_interface = ChatInterface()
        self.document_upload = DocumentUpload()
        self.setup_health_check()
    
    def setup_health_check(self):
        """设置健康检查"""
        def check_connection():
            while True:
                try:
                    is_connected = api_client.health_check()
                    state_manager.is_connected = is_connected
                except Exception as e:
                    logger.error(f"健康检查失败: {e}")
                    state_manager.is_connected = False
                
                time.sleep(10)  # 每10秒检查一次
        
        # 启动后台健康检查线程
        health_thread = threading.Thread(target=check_connection, daemon=True)
        health_thread.start()
    
    def create_interface(self):
        """创建Gradio界面"""
        # Gradio 4.x 有 gr.themes，3.x 没有；兼容两种版本
        blocks_kwargs = dict(
            title="RAG Agent",
            css=self._get_custom_css(),
            elem_classes=["main-container"],
        )
        if getattr(gr, "themes", None) is not None:
            blocks_kwargs["theme"] = gr.themes.Soft()
        with gr.Blocks(**blocks_kwargs) as app:
            
            # 页面标题
            gr.HTML("""
            <div class="header">
                <h1>🤖 RAG Agent</h1>
                <p>基于检索增强生成的智能问答系统</p>
            </div>
            """)
            
            with gr.Tabs() as tabs:
                # 聊天标签页
                with gr.TabItem("💬 对话", elem_classes=["tab-content"]):
                    self.chat_interface.get_layout()
                    self.chat_interface.setup_events()
                
                # 文档上传标签页
                with gr.TabItem("📄 文档上传", elem_classes=["tab-content"]):
                    self.document_upload.get_layout()
                    self.document_upload.setup_events()
                
                # 关于标签页
                with gr.TabItem("ℹ️ 关于", elem_classes=["tab-content"]):
                    gr.HTML("""
                    <div class="about-content">
                        <h3>关于 RAG Agent</h3>
                        <p>
                            RAG Agent 是一个基于检索增强生成(Retrieval-Augmented Generation)技术的智能问答系统。
                            系统支持PDF文档上传、智能检索和自然语言问答。
                        </p>
                        
                        <h4>主要功能：</h4>
                        <ul>
                            <li>📄 PDF文档上传和处理</li>
                            <li>🔍 智能文档检索</li>
                            <li>💬 多轮对话支持</li>
                            <li>🎯 精准问答回复</li>
                        </ul>
                        
                        <h4>使用说明：</h4>
                        <ol>
                            <li>在"文档上传"页面上传PDF文件</li>
                            <li>等待文档处理完成</li>
                            <li>在"对话"页面开始提问</li>
                        </ol>
                        
                        <p><em>版本: 1.0.0 | 技术栈: Python + Gradio + FastAPI</em></p>
                    </div>
                    """)
            
            # 页脚
            gr.HTML("""
            <div class="footer">
                <p>© 2024 RAG Agent - Powered by FastAPI + Gradio</p>
            </div>
            """)
        
        return app
    
    def _get_custom_css(self) -> str:
        """获取自定义CSS样式"""
        return """
        /* 全局样式 */
        .main-container {
            max-width: 1200px;
            margin: 0 auto;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* 头部样式 */
        .header {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
            font-weight: 600;
        }
        
        .header p {
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
            font-size: 1.1rem;
        }
        
        /* 标签页样式 */
        .tab-content {
            padding: 1.5rem;
        }
        
        /* 聊天容器样式 */
        .chat-container {
            border: 1px solid #e1e5e9;
            border-radius: 10px;
            padding: 1.5rem;
            background: #f8f9fa;
        }
        
        .chat-header {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2c3e50;
        }
        
        /* 聊天机器人样式 */
        #chatbot {
            border-radius: 8px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        /* 输入容器样式 */
        .input-container {
            margin-top: 1rem;
            gap: 0.5rem;
        }
        
        /* 上传容器样式 */
        .upload-container {
            border: 1px solid #e1e5e9;
            border-radius: 10px;
            padding: 1.5rem;
            background: #f8f9fa;
        }
        
        .upload-header {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2c3e50;
        }
        
        .files-header {
            font-size: 1.1rem;
            font-weight: 600;
            margin: 1rem 0 0.5rem 0;
            color: #2c3e50;
        }
        
        /* 按钮样式 */
        .gradio-button {
            border-radius: 6px !important;
            font-weight: 500 !important;
        }
        
        /* 文本框样式 */
        .gradio-textbox {
            border-radius: 6px !important;
        }
        
        /* 关于页面样式 */
        .about-content {
            padding: 1rem;
            line-height: 1.6;
        }
        
        .about-content h3 {
            color: #2c3e50;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
        }
        
        .about-content h4 {
            color: #34495e;
            margin-top: 1.5rem;
        }
        
        .about-content ul, .about-content ol {
            margin-left: 1.5rem;
        }
        
        .about-content li {
            margin: 0.5rem 0;
        }
        
        /* 页脚样式 */
        .footer {
            text-align: center;
            padding: 1.5rem 0;
            margin-top: 2rem;
            border-top: 1px solid #e1e5e9;
            color: #6c757d;
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .main-container {
                padding: 0 1rem;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .input-container {
                flex-direction: column;
            }
        }
        """
    
    def launch(self, **kwargs):
        """启动应用"""
        app = self.create_interface()
        
        # 默认启动参数：使用 127.0.0.1 避免浏览器访问 0.0.0.0 时出现 502
        default_kwargs = {
            "server_name": "127.0.0.1",
            "server_port": 7860,
            "share": False,
            "show_error": True,
            "quiet": False,
        }
        
        # 合并用户参数
        default_kwargs.update(kwargs)
        
        logger.info("启动 RAG Agent 前端界面...")
        app.launch(**default_kwargs)


def main():
    """主函数"""
    frontend = RAGAgentFrontend()
    frontend.launch()


if __name__ == "__main__":
    main()
