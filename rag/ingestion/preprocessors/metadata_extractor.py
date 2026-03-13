from typing import Dict, Any, List, Tuple


class DocumentMetadata:
    """文档元数据类"""

    def __init__(self, file_id: str, filename: str, file_hash: str,
                 chunk_count: int, upload_time: str, chunks: List[str] = None):
        self.file_id = file_id
        self.filename = filename
        self.file_hash = file_hash
        self.chunk_count = chunk_count
        self.upload_time = upload_time
        self.chunks = chunks or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "file_hash": self.file_hash,
            "chunk_count": self.chunk_count,
            "upload_time": self.upload_time,
            "chunks": self.chunks
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        return cls(
            file_id=data["file_id"],
            filename=data["filename"],
            file_hash=data["file_hash"],
            chunk_count=data["chunk_count"],
            upload_time=data["upload_time"],
            chunks=data.get("chunks", [])
        )


class MetadataExtractor:
    """元数据提取器"""

    @staticmethod
    def extract_semantic_prefix(filename: str) -> Tuple[str, str]:
        """
        从文件名提取文档类型和语义前缀
        :param filename: 文件名
        :return: (文档类型，语义前缀)
        """
        # 移除文件扩展名
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

        # 根据文件名类型返回不同的前缀
        filename_lower = name_without_ext.lower()

        # 简历类文档 - 扩展关键词识别
        resume_keywords = [
            '简历', '应聘', 'resume', 'cv', '求职',
            '工程师', '开发', '技术', '工作', '项目',  # 新增：职业相关词汇
            '教育', '学历', '毕业', '学校', '专业'  # 新增：教育相关词汇
        ]

        # 如果包含简历相关关键词，或者是人名格式（如"吴柯江"）
        has_resume_keyword = any(keyword in filename_lower for keyword in resume_keywords)
        is_name_format = '_' in name_without_ext and len(name_without_ext.split('_')[-1]) >= 2

        if has_resume_keyword or is_name_format:
            # 尝试从文件名提取人名
            name = ''
            if '_' in name_without_ext:
                parts = name_without_ext.split('_')
                if len(parts) >= 2:
                    name = parts[-1]  # 取最后一部分作为人名

            if name:
                return ('个人简历', f'[文档类型：个人简历]\n\n以下内容来自求职者 {name}的个人简历：\n\n')
            else:
                return ('个人简历', f'[文档类型：个人简历]\n\n以下内容来自求职者的个人简历：\n\n')

        # 制度/办法类文档
        elif any(keyword in filename_lower for keyword in ['办法', '制度', '规定', '规则', '条例']):
            return ('银行管理制度', f'[文档类型：银行管理制度]\n\n以下内容来自银行内部制度文件：\n\n')

        # 合同/协议类文档
        elif any(keyword in filename_lower for keyword in ['合同', '协议', '协定']):
            return ('合同协议', f'[文档类型：合同协议]\n\n以下内容来自合同或协议文件：\n\n')

        # 报告类文档
        elif any(keyword in filename_lower for keyword in ['报告', '总结', '汇报']):
            return ('报告总结', f'[文档类型：报告总结]\n\n以下内容来自报告或总结文档：\n\n')

        # 默认前缀
        else:
            return ('参考文档', f'[文档类型：参考文档]\n\n以下内容来自参考文档：\n\n')

    @staticmethod
    def generate_guide_text(doc_type: str, filename: str) -> str:
        """
        生成引导文本，增强语义理解
        :param doc_type: 文档类型
        :param filename: 文件名
        :return: 引导文本
        """
        if doc_type == '个人简历':
            # 针对简历的特殊处理
            name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

            # 尝试从文件名提取人名（如果有）
            name = ''
            if '_' in name_without_ext:
                # 例如：AI 应用开发工程师_吴柯江.pdf
                parts = name_without_ext.split('_')
                if len(parts) >= 2:
                    name = parts[-1]  # 取最后一部分作为人名

            if name:
                return f'[文档类型：个人简历]\n\n以下内容来自求职者 {name}的个人简历：\n\n'
            else:
                return f'[文档类型：个人简历]\n\n以下内容来自求职者的个人简历：\n\n'

        elif doc_type == '银行管理制度':
            name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            return f'[文档类型：银行管理制度]\n\n以下内容来自银行内部制度文件《{name_without_ext}》：\n\n'

        else:
            # 其他类型使用通用格式
            name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            return f'[文档类型：{doc_type}]\n\n以下内容来自{name_without_ext}：\n\n'
