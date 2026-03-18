"""
图片显示组件
用于在聊天界面中显示流程图图片
"""
from typing import Dict, List
from pathlib import Path

from infra.logs.logger_config import setup_logger

logger = setup_logger("frontend.components.image_display")


class ImageDisplay:
    """图片显示组件"""
    
    def __init__(self):
        """初始化图片显示组件"""
        pass
    
    def create_image_html(self, payload: dict) -> List[Dict]:
        """创建结构化图片消息"""
        if not payload or not payload.get("local_path"):
            return []
        
        try:
            local_path = payload.get("local_path")
            
            # 确保路径是正确的URL格式
            if isinstance(local_path, str):
                if local_path.startswith("data/"):
                    # 转换为正确的访问URL格式
                    filename = local_path.split("/")[-1]
                    image_url = f"/file/save_pic/2026/{filename}"
                elif local_path.startswith("D:\\") or local_path.startswith("/"):
                    # 如果是绝对路径，转换为URL格式
                    path_obj = Path(local_path)
                    image_url = f"/file/save_pic/2026/{path_obj.name}"
                else:
                    image_url = f"/file/save_pic/2026/{Path(local_path).name}"
            else:
                image_url = f"/file/save_pic/2026/{Path(str(local_path)).name}"
            
            logger.info(f"图片URL: {image_url}")
            
            # 使用正确的Gradio结构化消息格式
            structured_content = [
                {
                    "type": "image", 
                    "url": image_url
                }
            ]
            
            return structured_content
            
        except Exception as e:
            logger.error(f"创建结构化图片消息失败: {e}")
            return [{"type": "text", "text": f"❌ 图片显示失败: {str(e)}"}]
    
    def get_image_stats(self, payload: dict) -> str:
        """获取图片统计信息"""
        if not payload:
            return ""
        
        stats = []
        
        if payload.get("cached"):
            stats.append("⚡ 缓存命中")
        else:
            stats.append("🆕 新生成")
        
        return " | ".join(stats) if stats else ""
