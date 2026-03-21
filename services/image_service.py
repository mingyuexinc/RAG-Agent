"""
图片处理服务
负责流程图图片的下载、转换、缓存和存储
"""
import os
import hashlib
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import Image
import io
from datetime import datetime, timedelta

from infra.logs.logger_config import setup_logger

logger = setup_logger("services.image_service")


class ImageService:
    """图片处理服务"""
    
    def __init__(self):
        import os
        from datetime import datetime
        
        # 安全获取当前工作目录
        try:
            current_cwd = os.getcwd()
            logger.info(f"当前工作目录: {current_cwd}")
        except OSError as e:
            logger.warning(f"无法获取当前工作目录: {e}")
            # 使用备选方案
            current_cwd = "/home/studio_service/PROJECT"  # ModelScope环境默认路径
            logger.info(f"使用默认路径: {current_cwd}")
        
        # 获取项目根目录（无论从哪里运行都指向项目根目录）
        if current_cwd.endswith('app'):
            # 如果在app目录运行，返回上一级
            project_root = Path(current_cwd).parent
        else:
            # 否则使用当前目录
            project_root = Path(current_cwd)
        
        self.base_dir = project_root / "data" / "save_pic"
        self.base_dir = self.base_dir.resolve()  # 获取绝对路径
        
        logger.info(f"项目根目录: {project_root}")
        logger.info(f"图片存储基础目录: {self.base_dir}")
        
        # 创建基础目录
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"基础目录创建成功: {self.base_dir}")
        except Exception as e:
            logger.error(f"基础目录创建失败: {e}")
            # 尝试使用绝对路径
            try:
                abs_base_dir = Path("/home/studio_service/PROJECT/data/save_pic")
                abs_base_dir.mkdir(parents=True, exist_ok=True)
                self.base_dir = abs_base_dir
                logger.info(f"使用绝对路径创建基础目录成功: {self.base_dir}")
            except Exception as e2:
                logger.error(f"绝对路径创建也失败: {e2}")
                # 最后尝试使用临时目录
                import tempfile
                temp_dir = Path(tempfile.gettempdir()) / "rag_agent_images"
                temp_dir.mkdir(exist_ok=True)
                self.base_dir = temp_dir
                logger.warning(f"使用临时目录: {self.base_dir}")
        
        # 创建年度目录
        current_year = datetime.now().year
        self.current_year_dir = self.base_dir / str(current_year)
        
        try:
            self.current_year_dir.mkdir(exist_ok=True)
            logger.info(f"年度目录创建成功: {self.current_year_dir}")
        except Exception as e:
            logger.error(f"年度目录创建失败: {e}")
            # 尝试使用绝对路径
            try:
                abs_year_dir = self.base_dir / str(current_year)
                abs_year_dir.mkdir(exist_ok=True)
                self.current_year_dir = abs_year_dir
                logger.info(f"使用绝对路径创建年度目录成功: {self.current_year_dir}")
            except Exception as e2:
                logger.error(f"年度目录创建完全失败: {e2}")
                # 直接使用基础目录
                self.current_year_dir = self.base_dir
                logger.warning(f"使用基础目录替代年度目录: {self.current_year_dir}")
        
        # 配置参数
        self.max_width = 800
        self.max_height = 600
        self.quality = 85
        self.max_storage_mb = 100
        
        logger.info(f"图片服务初始化完成")
        logger.info(f"最终存储目录: {self.current_year_dir}")
        logger.info(f"基础目录存在: {self.base_dir.exists()}")
        logger.info(f"年度目录存在: {self.current_year_dir.exists()}")
    
    def get_url_hash(self, url: str) -> str:
        """获取URL的MD5哈希"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def get_image_path(self, url_hash: str) -> Path:
        """获取图片存储路径"""
        return self.current_year_dir / f"{url_hash}.webp"
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """异步下载图片"""
        max_retries = 2
        timeout = aiohttp.ClientTimeout(total=45)  # 增加到45秒
        
        # 创建SSL上下文，处理证书验证问题
        import ssl
        import os
        verify_ssl = os.getenv('VERIFY_SSL', 'false').lower() == 'true'
        
        if verify_ssl:
            # 启用SSL验证（生产环境推荐）
            ssl_context = ssl.create_default_context()
            logger.info("SSL证书验证已启用")
        else:
            # 禁用SSL验证（解决证书问题）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL证书验证已禁用（临时解决方案）")
        
        # 创建连接器
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"下载图片尝试 {attempt + 1}/{max_retries}: {url[:50]}...")
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    # 添加User-Agent头，避免被拒绝
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.read()
                            logger.info(f"下载成功，数据大小: {len(data)} bytes")
                            return data
                        else:
                            logger.error(f"下载图片失败，状态码: {response.status}")
                            if response.status == 503:
                                logger.error("mermaid.ink服务暂时不可用，请稍后重试")
                            return None
            except asyncio.TimeoutError:
                logger.warning(f"下载超时，尝试 {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # 增加等待时间
                continue
            except Exception as e:
                logger.error(f"下载图片异常: {e}")
                if "SSL" in str(e) or "certificate" in str(e).lower():
                    logger.warning("检测到SSL相关问题，建议检查VERIFY_SSL环境变量")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # 等待1秒后重试
                continue
        
        logger.error(f"下载图片失败，已重试 {max_retries} 次")
        return None
    
    def optimize_image(self, image_data: bytes) -> Optional[bytes]:
        """优化图片：调整尺寸和格式转换"""
        try:
            # 打开图片
            with Image.open(io.BytesIO(image_data)) as img:
                # 转换为RGB模式（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 计算新尺寸（保持比例）
                width, height = img.size
                if width > self.max_width or height > self.max_height:
                    ratio = min(self.max_width / width, self.max_height / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 转换为WebP格式
                output = io.BytesIO()
                img.save(output, format='WebP', quality=self.quality, optimize=True)
                return output.getvalue()
                
        except Exception as e:
            logger.error(f"图片优化失败: {e}")
            return None
    
    def save_image(self, image_data: bytes, file_path: Path) -> bool:
        """保存图片到本地"""
        try:
            # 记录详细的路径信息
            import os
            
            # 安全获取当前工作目录
            try:
                current_cwd = os.getcwd()
            except OSError:
                current_cwd = "无法获取"
                logger.warning("无法获取当前工作目录，使用项目根目录")
            
            abs_file_path = file_path.resolve()
            parent_dir = file_path.parent.resolve()
            
            logger.info(f"当前工作目录: {current_cwd}")
            logger.info(f"目标文件路径: {file_path}")
            logger.info(f"绝对文件路径: {abs_file_path}")
            logger.info(f"父目录路径: {parent_dir}")
            logger.info(f"父目录存在: {parent_dir.exists()}")
            logger.info(f"图片数据大小: {len(image_data)} bytes")
            
            # 确保目录存在
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"目录创建完成: {parent_dir}")
            except Exception as e:
                logger.error(f"创建目录失败: {e}")
                # 尝试使用绝对路径创建
                abs_parent = parent_dir.resolve()
                if not abs_parent.exists():
                    try:
                        abs_parent.mkdir(parents=True, exist_ok=True)
                        logger.info(f"使用绝对路径创建目录成功: {abs_parent}")
                    except Exception as e2:
                        logger.error(f"绝对路径创建目录也失败: {e2}")
                        return False
            
            # 写入文件
            try:
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                    # 在文件关闭前强制刷新到磁盘
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as e:
                logger.error(f"写入文件失败: {e}")
                # 尝试使用绝对路径写入
                try:
                    abs_file = file_path.resolve()
                    with open(abs_file, 'wb') as f:
                        f.write(image_data)
                        f.flush()
                        os.fsync(f.fileno())
                    logger.info(f"使用绝对路径写入成功: {abs_file}")
                except Exception as e2:
                    logger.error(f"绝对路径写入也失败: {e2}")
                    return False
            
            # 验证文件
            if file_path.exists():
                file_size = file_path.stat().st_size
                logger.info(f"文件验证成功: {file_path}, 大小: {file_size} bytes")
                if file_size > 0:
                    logger.info(f"图片已保存: {file_path}")
                    return True
                else:
                    logger.error(f"文件保存但为空: {file_path}")
                    return False
            else:
                logger.error(f"文件保存后不存在: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    async def process_flowchart_image(self, chart_url: str) -> Dict[str, Any]:
        """处理流程图图片：下载、优化、保存"""
        try:
            # 生成URL哈希
            url_hash = self.get_url_hash(chart_url)
            local_path = self.get_image_path(url_hash)
            
            logger.info(f"处理流程图图片: {chart_url[:50]}...")
            logger.info(f"目标路径: {local_path}")
            logger.info(f"基础目录: {self.base_dir}")
            logger.info(f"年度目录: {self.current_year_dir}")
            
            # 检查是否已缓存
            logger.info(f"检查缓存: {local_path}")
            logger.info(f"缓存文件存在: {local_path.exists()}")
            if local_path.exists():
                logger.info(f"使用缓存的图片: {local_path}")
                return {
                    "success": True,
                    "local_path": str(local_path),
                    "url": chart_url,
                    "cached": True,
                    "file_size": local_path.stat().st_size
                }
            else:
                logger.info(f"缓存文件不存在，需要下载: {local_path}")
            
            # 下载图片
            logger.info(f"开始下载流程图: {chart_url}")
            image_data = await self.download_image(chart_url)
            
            if not image_data:
                # 如果下载失败，尝试使用最近的缓存图片
                logger.info("下载失败，尝试使用备用缓存图片")
                cached_images = list(self.current_year_dir.glob("*.webp"))
                if cached_images:
                    # 使用最新的缓存图片
                    latest_image = max(cached_images, key=lambda f: f.stat().st_mtime)
                    logger.info(f"使用备用缓存图片: {latest_image}")
                    return {
                        "success": True,
                        "local_path": str(latest_image),
                        "url": chart_url,
                        "cached": True,
                        "file_size": latest_image.stat().st_size,
                        "fallback": True
                    }
                
                return {
                    "success": False,
                    "error": "流程图服务暂时不可用，请稍后重试",
                    "url": chart_url,
                    "retry_suggestion": "可能是mermaid.ink服务繁忙，建议稍后重试"
                }
            
            logger.info(f"下载成功，数据大小: {len(image_data)} bytes")
            
            # 优化图片
            logger.info("开始优化图片...")
            optimized_data = self.optimize_image(image_data)
            
            if not optimized_data:
                return {
                    "success": False,
                    "error": "图片优化失败",
                    "url": chart_url
                }
            
            logger.info(f"优化成功，数据大小: {len(optimized_data)} bytes")
            
            # 保存图片
            logger.info(f"开始保存图片到: {local_path}")
            if self.save_image(optimized_data, local_path):
                return {
                    "success": True,
                    "local_path": str(local_path),
                    "url": chart_url,
                    "cached": False,
                    "original_size": len(image_data),
                    "optimized_size": len(optimized_data),
                    "compression_ratio": len(optimized_data) / len(image_data) if image_data else 0
                }
            else:
                return {
                    "success": False,
                    "error": "图片保存失败",
                    "url": chart_url
                }
                
        except Exception as e:
            logger.error(f"处理流程图图片失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": chart_url
            }
    
    def get_relative_path(self, full_path: str) -> str:
        """获取相对于项目根目录的路径"""
        try:
            # 使用与初始化相同的逻辑获取项目根目录
            current_cwd = Path.cwd()
            if str(current_cwd).endswith('app'):
                project_root = current_cwd.parent
            else:
                project_root = current_cwd
            
            path_obj = Path(full_path)
            relative_path = path_obj.relative_to(project_root)
            return str(relative_path).replace('\\', '/')
        except Exception as e:
            logger.error(f"获取相对路径失败: {e}, full_path: {full_path}")
            return full_path
    
    def cleanup_old_images(self, days: int = 30) -> int:
        """清理旧的图片文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for year_dir in self.base_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                    
                for file_path in year_dir.iterdir():
                    if file_path.is_file():
                        # 检查文件修改时间
                        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mod_time < cutoff_date:
                            file_path.unlink()
                            deleted_count += 1
                            logger.info(f"删除旧图片: {file_path}")
            
            logger.info(f"清理完成，删除了 {deleted_count} 个旧图片文件")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧图片失败: {e}")
            return 0
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        try:
            total_size = 0
            file_count = 0
            
            for year_dir in self.base_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                    
                for file_path in year_dir.iterdir():
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1
            
            return {
                "total_files": file_count,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "storage_limit_mb": self.max_storage_mb,
                "usage_percent": round((total_size / (1024 * 1024)) / self.max_storage_mb * 100, 1)
            }
        except Exception as e:
            logger.error(f"获取存储信息失败: {e}")
            return {"error": str(e)}


# 全局实例
image_service = ImageService()
