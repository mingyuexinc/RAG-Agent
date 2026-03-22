"""
图片显示组件
用于在聊天界面中显示流程图图片
"""
from typing import Dict, List
from pathlib import Path

from infra.logs.logger_config import get_logger

logger = get_logger("frontend.components.image_display")


class ImageDisplay:
    """图片显示组件"""
    
    def __init__(self):
        """初始化图片显示组件"""
        pass
    
    def create_image_html(self, payload: dict) -> List[Dict]:
        """创建结构化图片消息"""
        if not payload:
            return []
        
        try:
            # 直接使用api_path，不再构造路径
            image_url = payload.get("api_path")
            if not image_url:
                logger.error("payload中缺少api_path字段")
                return [{"type": "text", "text": "❌ 图片显示失败: 缺少API路径"}]
            
            logger.info(f"图片URL: {image_url}")
            logger.info(f"图片payload: {payload}")
            
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
