"""
缓存管理器
负责图片缓存的索引和管理
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from infra.logs.logger_config import setup_logger

logger = setup_logger("services.cache_manager")


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_file: str = "data/save_pic/cache.json"):
        # 智能获取项目根目录
        import os
        current_cwd = os.getcwd()
        if str(current_cwd).endswith('app'):
            project_root = Path(current_cwd).parent
        else:
            project_root = Path(current_cwd)
        
        self.cache_file = project_root / cache_file
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_data = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """加载缓存数据"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return {}
    
    def _save_cache(self):
        """保存缓存数据"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def add_entry(self, url: str, local_path: str, file_size: int = 0):
        """添加缓存条目"""
        url_hash = self._get_url_hash(url)
        self.cache_data[url_hash] = {
            "url": url,
            "local_path": local_path,
            "file_size": file_size,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 1
        }
        self._save_cache()
        logger.info(f"添加缓存条目: {url_hash}")
    
    def get_entry(self, url: str) -> Optional[Dict[str, Any]]:
        """获取缓存条目"""
        url_hash = self._get_url_hash(url)
        if url_hash in self.cache_data:
            entry = self.cache_data[url_hash]
            # 更新访问信息
            entry["last_accessed"] = datetime.now().isoformat()
            entry["access_count"] = entry.get("access_count", 0) + 1
            self._save_cache()
            logger.info(f"命中缓存: {url_hash}")
            return entry
        return None
    
    def update_entry(self, url: str, **kwargs):
        """更新缓存条目"""
        url_hash = self._get_url_hash(url)
        if url_hash in self.cache_data:
            self.cache_data[url_hash].update(kwargs)
            self._save_cache()
            logger.info(f"更新缓存条目: {url_hash}")
    
    def remove_entry(self, url: str):
        """删除缓存条目"""
        url_hash = self._get_url_hash(url)
        if url_hash in self.cache_data:
            del self.cache_data[url_hash]
            self._save_cache()
            logger.info(f"删除缓存条目: {url_hash}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_entries = len(self.cache_data)
        total_size = sum(entry.get("file_size", 0) for entry in self.cache_data.values())
        
        # 计算访问频率
        access_counts = [entry.get("access_count", 0) for entry in self.cache_data.values()]
        avg_access = sum(access_counts) / len(access_counts) if access_counts else 0
        
        return {
            "total_entries": total_entries,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "average_access": round(avg_access, 1),
            "cache_file": str(self.cache_file)
        }
    
    def cleanup_invalid_entries(self, valid_paths: list):
        """清理无效的缓存条目"""
        valid_paths_set = set(valid_paths)
        invalid_entries = []
        
        for url_hash, entry in self.cache_data.items():
            if entry.get("local_path") not in valid_paths_set:
                invalid_entries.append(url_hash)
        
        for url_hash in invalid_entries:
            del self.cache_data[url_hash]
            logger.info(f"清理无效缓存条目: {url_hash}")
        
        if invalid_entries:
            self._save_cache()
        
        return len(invalid_entries)
    
    def get_recent_entries(self, limit: int = 10) -> list:
        """获取最近使用的缓存条目"""
        entries = list(self.cache_data.values())
        # 按最后访问时间排序
        entries.sort(key=lambda x: x.get("last_accessed", ""), reverse=True)
        return entries[:limit]
    
    def _get_url_hash(self, url: str) -> str:
        """获取URL哈希（需要与ImageService保持一致）"""
        import hashlib
        return hashlib.md5(url.encode('utf-8')).hexdigest()


# 全局实例
cache_manager = CacheManager()
