"""
API客户端服务 - 修复版本
用于与后端FastAPI接口通信
"""
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path

from infra.logs.logger_config import get_logger

# 使用统一的日志配置
logger = get_logger("frontend.services.api_client")


class APIClient:
    """FastAPI客户端 - 修复版本"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30  # 设置超时时间
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求 - 修复版本"""
        url = f"{self.base_url}{endpoint}"
        logger.info(f"发送{method}请求到: {url}")
        logger.info(f"请求参数: {kwargs}")
        
        try:
            response = self.session.request(method, url, **kwargs)
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"响应内容: {result}")
                    # 返回包含响应头的完整响应
                    return {
                        "data": result,
                        "headers": dict(response.headers),
                        "status_code": response.status_code
                    }
                except ValueError as e:
                    logger.error(f"JSON解析失败: {e}")
                    logger.error(f"原始响应: {response.text}")
                    return {"error": f"响应解析失败: {e}", "headers": dict(response.headers)}
            else:
                logger.error(f"请求失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}", "headers": dict(response.headers)}
                
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时: {e}")
            return {"error": f"请求超时: {e}"}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接错误: {e}")
            return {"error": f"连接失败: {e}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            return {"error": f"请求失败: {e}"}
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return {"error": f"未知错误: {e}"}
    
    def chat(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """发送聊天请求"""
        headers = {}
        if session_id:
            headers["X-Session-ID"] = session_id
            logger.info(f"发送请求时携带session_id: {session_id}")
        else:
            logger.info("发送请求时session_id为None，将创建新会话")
            
        data = {"query": query}
        
        response = self._make_request(
            "POST", 
            "/tool/execute", 
            json=data, 
            headers=headers
        )
        
        # 处理新的响应格式
        if "error" in response:
            return response
        
        # 提取session_id
        response_headers = response.get("headers", {})
        logger.info(f"响应头部: {response_headers}")
        
        if "session_id" in response_headers:
            response["session_id"] = response_headers["session_id"]
        elif "x-session-id" in response_headers:
            response["session_id"] = response_headers["x-session-id"]
        elif "X-Session-ID" in response_headers:
            response["session_id"] = response_headers["X-Session-ID"]
        else:
            logger.warning(f"未找到session_id在响应头中: {list(response_headers.keys())}")
            
        logger.info(f"提取到的session_id: {response.get('session_id', 'None')}")
        
        # 返回原始数据（兼容现有代码）
        if "data" in response:
            result = response["data"]
            result["session_id"] = response.get("session_id")
            return result
        else:
            return response
    
    def upload_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """上传文档 - 修复版本"""
        logger.info(f"开始上传文档，文件数量: {len(file_paths)}")
        logger.info(f"文件路径: {file_paths}")
        
        files = []
        valid_files = []
        
        for i, file_path in enumerate(file_paths):
            try:
                path_obj = Path(file_path)
                if path_obj.exists() and path_obj.is_file():
                    # 检查文件大小
                    file_size = path_obj.stat().st_size
                    logger.info(f"文件 {i+1}: {file_path}, 大小: {file_size} bytes")
                    
                    valid_files.append(file_path)
                else:
                    logger.error(f"文件不存在或不是文件: {file_path}")
                    
            except Exception as e:
                logger.error(f"处理文件 {file_path} 时出错: {e}")
                continue
        
        if not valid_files:
            logger.error("没有找到有效文件")
            return {"error": "没有找到有效文件"}
        
        try:
            logger.info(f"准备上传 {len(valid_files)} 个有效文件")
            
            # 记录文件信息
            for i, file_path in enumerate(valid_files):
                file_name = Path(file_path).name
                logger.info(f"上传文件 {i+1}: {file_name}")
            
            # 使用正确的文件上传格式
            upload_files = []
            for i, file_path in enumerate(valid_files):
                file_name = Path(file_path).name
                # 重新打开文件确保文件指针在开始位置
                file_obj = open(file_path, 'rb')
                upload_files.append(('files', (file_name, file_obj, 'application/octet-stream')))
            
            response = self._make_request(
                "POST",
                "/upload", 
                files=upload_files
            )
            
            # 关闭文件
            for _, (_, file_obj, _) in upload_files:
                file_obj.close()
            
            logger.info(f"上传完成，响应: {response}")
            return response
            
        finally:
            # 清理资源（现在在upload_files中处理）
            pass
    
    def health_check(self) -> bool:
        """检查API健康状态"""
        try:
            response = self._make_request("GET", "/health")
            # 正确处理包装的响应格式
            return ("error" not in response and 
                    response.get("data", {}).get("status") == "ok")
        except:
            return False


# 全局API客户端实例
api_client = APIClient()
