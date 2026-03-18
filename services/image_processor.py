"""
图片处理工具
提供图片格式转换、压缩等处理功能
"""
import io
from typing import Tuple, Optional, Union
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

from infra.logs.logger_config import setup_logger

logger = setup_logger("services.image_processor")


class ImageProcessor:
    """图片处理工具类"""
    
    @staticmethod
    def resize_image(image: Image.Image, max_width: int, max_height: int, maintain_ratio: bool = True) -> Image.Image:
        """调整图片尺寸"""
        try:
            if maintain_ratio:
                # 保持宽高比缩放
                width, height = image.size
                ratio = min(max_width / width, max_height / height)
                
                if ratio < 1:  # 只缩小，不放大
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                # 强制缩放到指定尺寸
                image = image.resize((max_width, max_height), Image.Resampling.LANCZOS)
            
            return image
        except Exception as e:
            logger.error(f"调整图片尺寸失败: {e}")
            return image
    
    @staticmethod
    def convert_to_webp(image: Image.Image, quality: int = 85, optimize: bool = True) -> bytes:
        """转换为WebP格式"""
        try:
            output = io.BytesIO()
            image.save(output, format='WebP', quality=quality, optimize=optimize, method=6)
            return output.getvalue()
        except Exception as e:
            logger.error(f"转换为WebP失败: {e}")
            return b""
    
    @staticmethod
    def convert_to_rgb(image: Image.Image) -> Image.Image:
        """转换为RGB模式"""
        try:
            if image.mode in ('RGBA', 'LA', 'P'):
                # 对于有透明通道的图片，使用白色背景
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                return background
            elif image.mode != 'RGB':
                return image.convert('RGB')
            return image
        except Exception as e:
            logger.error(f"转换为RGB失败: {e}")
            return image
    
    @staticmethod
    def enhance_image(image: Image.Image, contrast: float = 1.0, sharpness: float = 1.0) -> Image.Image:
        """增强图片质量"""
        try:
            # 增强对比度
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(contrast)
            
            # 增强锐度
            if sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(sharpness)
            
            return image
        except Exception as e:
            logger.error(f"增强图片失败: {e}")
            return image
    
    @staticmethod
    def get_image_info(image_data: bytes) -> dict:
        """获取图片信息"""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.size[0],
                    "height": img.size[1],
                    "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
        except Exception as e:
            logger.error(f"获取图片信息失败: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def create_thumbnail(image: Image.Image, size: Tuple[int, int] = (200, 150)) -> Image.Image:
        """创建缩略图"""
        try:
            # 转换为RGB模式
            rgb_image = ImageProcessor.convert_to_rgb(image)
            
            # 创建缩略图
            thumbnail = rgb_image.copy()
            thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
            
            return thumbnail
        except Exception as e:
            logger.error(f"创建缩略图失败: {e}")
            return image
    
    @staticmethod
    def optimize_for_web(image: Image.Image, max_width: int = 800, max_height: int = 600, 
                      quality: int = 85) -> bytes:
        """为Web优化图片"""
        try:
            # 转换为RGB
            rgb_image = ImageProcessor.convert_to_rgb(image)
            
            # 调整尺寸
            resized_image = ImageProcessor.resize_image(rgb_image, max_width, max_height)
            
            # 轻微增强
            enhanced_image = ImageProcessor.enhance_image(resized_image, 1.1, 1.05)
            
            # 转换为WebP
            return ImageProcessor.convert_to_webp(enhanced_image, quality, optimize=True)
            
        except Exception as e:
            logger.error(f"Web优化失败: {e}")
            return b""
    
    @staticmethod
    def analyze_image_quality(image_data: bytes) -> dict:
        """分析图片质量"""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # 转换为numpy数组进行分析
                rgb_image = ImageProcessor.convert_to_rgb(img)
                img_array = np.array(rgb_image)
                
                # 计算亮度统计
                brightness = np.mean(img_array)
                
                # 计算对比度（标准差）
                contrast = np.std(img_array)
                
                # 估算清晰度（基于边缘检测）
                gray_image = np.mean(img_array, axis=2)
                laplacian = np.var(gray_image)
                
                return {
                    "brightness": round(float(brightness), 2),
                    "contrast": round(float(contrast), 2),
                    "sharpness": round(float(laplacian), 2),
                    "size": img.size,
                    "file_size": len(image_data)
                }
        except Exception as e:
            logger.error(f"分析图片质量失败: {e}")
            return {"error": str(e)}


class ImageValidator:
    """图片验证器"""
    
    @staticmethod
    def is_valid_image_format(image_data: bytes) -> bool:
        """验证图片格式"""
        try:
            Image.open(io.BytesIO(image_data))
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_safe_filename(filename: str) -> str:
        """获取安全的文件名"""
        import re
        # 移除或替换不安全的字符
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 限制长度
        if len(safe_name) > 100:
            name, ext = safe_name.rsplit('.', 1) if '.' in safe_name else (safe_name, '')
            safe_name = name[:90] + '.' + ext if ext else name[:100]
        return safe_name
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """清理路径"""
        import os
        return os.path.normpath(path).replace('..', '')
