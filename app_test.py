"""
RAG Agent - 程序员测试版本
保留原有的main()启动方式，方便开发和调试
"""
import os
import sys
import time
import threading
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 初始化日志系统 - 在应用入口处调用
from infra.logs.logger_config import initialize_log_system
initialize_log_system()

# ModelScope演示函数
def modelscope_quickstart(name):
    """ModelScope快速启动函数"""
    return "Welcome to ModelScope, " + name + "!! This is RAG Agent - an intelligent Q&A system based on Retrieval-Augmented Generation."

def check_dependencies():
    """检查必要的依赖"""
    required_modules = {
        'uvicorn': 'uvicorn',
        'requests': 'requests',
        'gradio': 'gradio'
    }
    
    missing = []
    for module, package in required_modules.items():
        try:
            __import__(module)
            print(f"✅ {package} 已安装")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} 未安装")
    
    if missing:
        print(f"\n请安装缺失的依赖: pip install {' '.join(missing)}")
        return False
    
    return True

def start_backend_server():
    """启动后端API服务器"""
    try:
        print("🔧 启动后端API服务器...")
        
        # 直接使用原有的启动方式
        backend_process = subprocess.Popen([
            sys.executable, "app/main.py"
        ], cwd=project_root)
        
        # 等待后端启动
        print("⏳ 等待后端服务启动...")
        time.sleep(8)  # 增加等待时间，让后端完全启动
        
        # 检查后端是否启动成功
        try:
            import requests
            response = requests.get("http://127.0.0.1:8000/health", timeout=10)
            if response.status_code == 200:
                print("✅ 后端API服务器启动成功")
                return backend_process
            else:
                print(f"❌ 后端API服务器响应异常: {response.status_code}")
                # 尝试读取后端进程输出
                try:
                    stdout, stderr = backend_process.communicate(timeout=1)
                    if stderr:
                        print(f"后端错误: {stderr.decode()}")
                except:
                    pass
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 后端API服务器连接失败: {e}")
            print("💡 请检查后端服务是否正常启动")
            # 尝试读取后端进程输出
            try:
                stdout, stderr = backend_process.communicate(timeout=1)
                if stderr:
                    print(f"后端错误: {stderr.decode()}")
            except:
                pass
            return None
            
    except Exception as e:
        print(f"❌ 启动后端服务器失败: {e}")
        print("💡 请确保后端模块可用")
        return None

def main():
    """启动应用 - 程序员测试版本，使用原有的main()启动方式"""
    print("🚀 启动 RAG Agent - 程序员测试版本...")
    print("📍 前端访问地址: http://localhost:7860")
    print("🔧 后端API地址: http://localhost:8000")
    print("🎯 使用原有的UI界面和逻辑")
    print("👨‍💻 保留main()启动方式，方便调试")
    print("-" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败，请安装缺失的包后重试")
        return
    
    # 启动后端服务
    backend_process = start_backend_server()
    
    if not backend_process:
        print("❌ 后端服务启动失败，前端将无法正常工作")
        print("💡 请检查后端依赖和配置")
        return
    
    try:
        # 导入并启动原有的前端应用
        from frontend.app import RAGAgentFrontend
        
        # 修改API客户端配置，确保连接到本地后端
        from frontend.services import api_client
        api_client.base_url = "http://127.0.0.1:8000"
        print("✅ API客户端配置完成")
        
        frontend = RAGAgentFrontend()
        frontend.launch(
            server_name="0.0.0.0",  # ModelScope需要
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False
        )
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保前端模块可用")
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("请检查错误信息并重试")
    
    finally:
        # 清理后端进程
        if backend_process:
            try:
                backend_process.terminate()
                backend_process.wait(timeout=5)
                print("🔧 后端服务器已关闭")
            except:
                try:
                    backend_process.kill()
                    print("🔧 强制关闭后端服务器")
                except:
                    pass

if __name__ == "__main__":
    main()
