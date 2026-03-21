"""
RAG Agent - ModelScope部署版本
统一的启动入口，保持原有UI界面和逻辑不变
同时启动前端和后端服务
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
            
            # 尝试多个端口
            import os
            # 检测是否在ModelScope环境
            is_modelscope = '/home/studio_service' in os.getcwd() or '/home/studio_service' in os.getenv('PWD', '')
            
            if is_modelscope:
                # ModelScope环境：优先检查8001
                ports_to_try = [8001, 8000, 15181]
            else:
                # 本地环境：优先检查8000
                ports_to_try = [8000, 8001, 15181]
            
            backend_url = None
            
            for port in ports_to_try:
                try:
                    response = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
                    if response.status_code == 200:
                        backend_url = f"http://127.0.0.1:{port}"
                        print(f"✅ 后端API服务器启动成功，端口: {port}")
                        break
                except requests.exceptions.ConnectionError:
                    continue
                except Exception as e:
                    print(f"端口 {port} 检查失败: {e}")
                    continue
            
            if backend_url:
                # 更新API客户端配置
                from frontend.services import api_client
                api_client.base_url = backend_url
                print(f"✅ API客户端配置完成: {backend_url}")
                return backend_process
            else:
                print("❌ 所有端口检查都失败")
                return None
                
        except Exception as e:
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

def create_demo():
    """创建Gradio演示应用"""
    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败，请安装缺失的包后重试")
        return None
    
    # 启动后端服务
    backend_process = start_backend_server()
    
    if not backend_process:
        print("❌ 后端服务启动失败，前端将无法正常工作")
        print("💡 请检查后端依赖和配置")
        return None
    
    try:
        # 导入并启动原有的前端应用
        from frontend.app import RAGAgentFrontend
        
        frontend = RAGAgentFrontend()
        demo = frontend.create_interface()
        
        # 存储后端进程以便清理
        demo._backend_process = backend_process
        
        return demo
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保前端模块可用")
        if backend_process:
            try:
                backend_process.terminate()
                backend_process.wait(timeout=5)
            except:
                try:
                    backend_process.kill()
                except:
                    pass
        return None
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("请检查错误信息并重试")
        if backend_process:
            try:
                backend_process.terminate()
                backend_process.wait(timeout=5)
            except:
                try:
                    backend_process.kill()
                except:
                    pass
        return None

# 创建演示实例
demo = create_demo()

# ModelScope标准启动方式
if demo is not None:
    demo.launch()
else:
    print("❌ 演示应用创建失败")
