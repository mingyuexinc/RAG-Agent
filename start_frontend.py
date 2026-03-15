"""
RAG Agent 前端启动脚本
"""
import sys
print("Python path:", sys.executable)
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """启动前端应用"""
    print("🚀 启动 RAG Agent 前端界面...")
    print("📍 访问地址: http://localhost:7860")
    print("⚠️  请确保后端API服务已启动 (http://localhost:8000)")
    print("-" * 50)
    
    try:
        # 导入并启动应用
        from frontend.app import RAGAgentFrontend
        
        frontend = RAGAgentFrontend()
        frontend.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False
        )
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所需依赖: gradio, requests")
        print("安装命令: pip install gradio requests")
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("请检查错误信息并重试")

if __name__ == "__main__":
    main()


