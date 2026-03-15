"""
文档上传组件 - 修复版本
"""
import gradio as gr
import logging
import tempfile
import os
from typing import List, Tuple, Optional
from frontend.services import api_client, state_manager


logger = logging.getLogger(__name__)


class DocumentUpload:
    """文档上传组件 - 修复版本"""
    
    def __init__(self):
        self.file_input = gr.File(
            label="上传PDF文档",
            file_count="multiple",
            file_types=[".pdf"]
        )
        
        self.upload_btn = gr.Button("上传文档", variant="primary")
        self.clear_files_btn = gr.Button("清空文件", variant="secondary")
        
        self.upload_status = gr.Textbox(
            label="上传状态",
            value="等待上传...",
            interactive=False,
            lines=3
        )
        # 使用 Textbox 替代 DataFrame，避免 Gradio 5.x 中 get_api_info() 对 boolean schema 的解析崩溃
        self.file_list = gr.Textbox(
            label="已上传文件",
            value="",
            interactive=False,
            lines=6,
            placeholder="上传成功后将在此显示文件列表"
        )
    
    def setup_events(self):
        """设置事件处理"""
        # 上传事件
        self.upload_btn.click(
            self._handle_upload,
            inputs=[self.file_input],
            outputs=[self.upload_status, self.file_list, self.file_input]
        )
        
        # 清空文件事件
        self.clear_files_btn.click(
            self._clear_files,
            outputs=[self.file_input, self.upload_status, self.file_list]
        )
        
        return []
    
    def _handle_upload(self, files: Optional[List]) -> Tuple[str, str, Optional[List]]:
        """处理文档上传 - 修复版本。返回 (状态文案, 文件列表文案, 清空后的 file_input)。"""
        if not files:
            return "❌ 请选择要上传的文件", "", None
        
        try:
            logger.info(f"开始上传文档，文件数量: {len(files)}")
            
            # 调试：打印文件对象信息
            for i, file_obj in enumerate(files):
                logger.info(f"文件 {i+1}: {type(file_obj)}, 属性: {dir(file_obj)}")
                if hasattr(file_obj, 'name'):
                    logger.info(f"  - name: {file_obj.name}")
                if hasattr(file_obj, 'orig_name'):
                    logger.info(f"  - orig_name: {file_obj.orig_name}")
                if hasattr(file_obj, 'file_path'):
                    logger.info(f"  - file_path: {file_obj.file_path}")
            
            # 处理Gradio文件对象
            temp_files = []
            file_paths = []
            
            for file_obj in files:
                try:
                    # 方法1：尝试直接获取文件路径
                    if hasattr(file_obj, 'name') and os.path.exists(file_obj.name):
                        file_paths.append(file_obj.name)
                        logger.info(f"使用直接路径: {file_obj.name}")
                        continue
                    
                    # 方法2：尝试orig_name属性
                    if hasattr(file_obj, 'orig_name'):
                        logger.info(f"文件名: {file_obj.orig_name}")
                    
                    # 方法3：处理临时文件
                    if hasattr(file_obj, 'file') and hasattr(file_obj.file, 'read'):
                        # 创建临时文件
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                            file_obj.file.seek(0)  # 重置文件指针
                            temp_file.write(file_obj.file.read())
                            temp_file_path = temp_file.name
                            temp_files.append(temp_file_path)
                            file_paths.append(temp_file_path)
                            logger.info(f"创建临时文件: {temp_file_path}")
                        continue
                    
                    # 方法4：如果是字符串路径
                    if isinstance(file_obj, str) and os.path.exists(file_obj):
                        file_paths.append(file_obj)
                        logger.info(f"使用字符串路径: {file_obj}")
                        continue
                    
                    # 方法5：如果是字典格式
                    if isinstance(file_obj, dict):
                        if 'name' in file_obj and os.path.exists(file_obj['name']):
                            file_paths.append(file_obj['name'])
                            logger.info(f"使用字典路径: {file_obj['name']}")
                            continue
                        elif 'file_path' in file_obj and os.path.exists(file_obj['file_path']):
                            file_paths.append(file_obj['file_path'])
                            logger.info(f"使用字典file_path: {file_obj['file_path']}")
                            continue
                    
                    logger.error(f"无法处理文件对象: {file_obj}")
                    
                except Exception as e:
                    logger.error(f"处理单个文件时出错: {e}")
                    continue
            
            if not file_paths:
                return "❌ 无法获取有效的文件路径", "", None
            
            logger.info(f"准备上传的文件路径: {file_paths}")
            
            # 调用API上传
            response = api_client.upload_documents(file_paths)
            logger.info(f"API响应: {response}")
            
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            if "error" in response:
                error_msg = f"❌ 上传失败: {response['error']}"
                logger.error(error_msg)
                return error_msg, "", None
            
            def _format_file_list(rows: List[List[str]]) -> str:
                if not rows:
                    return ""
                lines = ["文件名\t状态\t文件ID", "---"]
                for row in rows:
                    lines.append("\t".join(str(c) for c in row))
                return "\n".join(lines)
            
            # 处理成功响应
            if isinstance(response, list):
                # 多文件上传
                results = []
                for i, file_info in enumerate(response):
                    filename = files[i].orig_name if hasattr(files[i], 'orig_name') else f"文件{i+1}"
                    file_id = file_info.get("file_id", "unknown")
                    state_manager.add_uploaded_file({
                        "filename": filename,
                        "file_id": file_id,
                        "status": "success"
                    })
                    results.append([filename, "✅ 成功", file_id])
                success_msg = f"✅ 成功上传 {len(results)} 个文件"
                logger.info(success_msg)
                return success_msg, _format_file_list(results), None
            
            else:
                # 单文件上传
                filename = files[0].orig_name if hasattr(files[0], 'orig_name') else "上传的文件"
                file_id = response.get("file_id", "unknown")
                state_manager.add_uploaded_file({
                    "filename": filename,
                    "file_id": file_id,
                    "status": "success"
                })
                result = [[filename, "✅ 成功", file_id]]
                success_msg = f"✅ 成功上传文件: {filename}"
                logger.info(success_msg)
                return success_msg, _format_file_list(result), None
        
        except Exception as e:
            logger.error(f"上传文档时出错: {e}", exc_info=True)
            error_msg = f"❌ 上传失败: {str(e)}"
            return error_msg, "", None
    
    def _clear_files(self) -> Tuple[Optional[List], str, str]:
        """清空文件列表。返回 (file_input, 状态文案, 文件列表文案)。"""
        return None, "等待上传...", ""
    
    def get_layout(self):
        """获取组件布局"""
        with gr.Column(elem_classes=["upload-container"]):
            gr.HTML("<div class='upload-header'>📄 文档上传</div>")
            
            with gr.Row():
                self.file_input.render()
            
            with gr.Row():
                with gr.Column(scale=1):
                    self.upload_btn.render()
                with gr.Column(scale=1):
                    self.clear_files_btn.render()
            
            self.upload_status.render()
            
            gr.HTML("<div class='files-header'>📋 已上传文件</div>")
            self.file_list.render()
        
        return [self.file_input, self.upload_btn, self.clear_files_btn,
                self.upload_status, self.file_list]
    
    def get_uploaded_files_count(self) -> int:
        """获取已上传文件数量"""
        return len(state_manager.uploaded_files)
