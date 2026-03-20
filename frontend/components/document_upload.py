"""
文档上传组件 - 修复版本
"""
import gradio as gr
import logging
import tempfile
import os
import time
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
                """格式化文件列表为更易读的格式"""
                if not rows:
                    return ""
                
                # 使用更清晰的格式
                lines = ["📄 已上传文件列表:", ""]
                for i, row in enumerate(rows, 1):
                    filename, status, file_id = row
                    lines.append(f"{i}. {filename}")
                    lines.append(f"   状态: {status}")
                    lines.append(f"   ID: {file_id}")
                    lines.append("")  # 空行分隔
                
                return "\n".join(lines)
            
            # 处理成功响应
            logger.info(f"开始处理成功响应，响应类型: {type(response)}")
            logger.info(f"响应内容: {response}")
            
            if isinstance(response, dict):
                logger.info("响应是字典格式，开始解析...")
                # 检查是否是多文件响应
                if "data" in response:
                    data = response["data"]
                    logger.info(f"找到data字段: {data}")
                else:
                    data = response
                    logger.info("没有data字段，直接使用响应")
                
                # 检查filename字段是否包含多个文件名
                filename = data.get("filename", "")  # 从data字段获取
                file_id = data.get("file_id", "")      # 从data字段获取
                
                logger.info(f"提取的filename: '{filename}'")
                logger.info(f"提取的file_id: '{file_id}'")
                
                if "," in filename and "," in file_id:
                    # 多文件响应
                    logger.info(f"检测到多文件响应: {filename}")
                    filenames = [f.strip() for f in filename.split(",")]
                    file_ids = [f.strip() for f in file_id.split(",")]
                    
                    results = []
                    for i, (fname, fid) in enumerate(zip(filenames, file_ids)):
                        # 增强文件名提取逻辑
                        logger.info(f"处理文件 {i+1}: 原始文件名='{fname}', 提取文件名...")
                        filename_clean = self._extract_filename(files[i], f"文件{i+1}")
                        logger.info(f"提取的文件名: '{filename_clean}'")
                        
                        state_manager.add_uploaded_file({
                            "filename": fname,  # 使用后端返回的文件名
                            "file_id": fid,
                            "status": "success"
                        })
                        results.append([fname, "✅ 成功", fid])
                    
                    success_msg = f"✅ 成功上传 {len(results)} 个文件:\n" + "\n".join([f"• {result[0]}" for result in results])
                    logger.info(success_msg)
                    return success_msg, _format_file_list(results), None
                else:
                    # 单文件响应
                    filename_clean = self._extract_filename(files[0], "上传的文件")
                    state_manager.add_uploaded_file({
                        "filename": filename,
                        "file_id": file_id,
                        "status": "success"
                    })
                    result = [[filename, "✅ 成功", file_id]]
                    success_msg = f"✅ 成功上传文件: {filename}"
                    logger.info(success_msg)
                    return success_msg, _format_file_list(result), None
            
            elif isinstance(response, list):
                # 直接的列表响应（备用方案）
                logger.info(f"处理列表响应，文件数量: {len(response)}")
                results = []
                for i, file_info in enumerate(response):
                    logger.info(f"处理文件 {i+1}: {file_info}")
                    # 增强文件名提取逻辑
                    filename = self._extract_filename(files[i], f"文件{i+1}")
                    file_id = file_info.get("file_id", f"file_{i+1}")
                    logger.info(f"文件 {i+1} - 文件名: {filename}, ID: {file_id}")
                    
                    state_manager.add_uploaded_file({
                        "filename": filename,
                        "file_id": file_id,
                        "status": "success"
                    })
                    results.append([filename, "✅ 成功", file_id])
                
                logger.info(f"多文件结果: {results}")
                success_msg = f"✅ 成功上传 {len(results)} 个文件:\n" + "\n".join([f"• {result[0]}" for result in results])
                logger.info(success_msg)
                return success_msg, _format_file_list(results), None
        
        except Exception as e:
            logger.error(f"上传文档时出错: {e}", exc_info=True)
            error_msg = f"❌ 上传失败: {str(e)}"
            return error_msg, "", None
    
    def _extract_filename(self, file_obj, default_name="上传的文件"):
        """增强的文件名提取逻辑"""
        # 尝试多种方式获取文件名
        filename_candidates = []
        
        # 方法1：orig_name属性
        if hasattr(file_obj, 'orig_name') and file_obj.orig_name:
            filename_candidates.append(file_obj.orig_name)
            logger.info(f"找到orig_name: {file_obj.orig_name}")
        
        # 方法2：name属性
        if hasattr(file_obj, 'name') and file_obj.name:
            # 如果是路径，提取文件名
            if isinstance(file_obj.name, str) and os.path.sep in file_obj.name:
                extracted_name = os.path.basename(file_obj.name)
                filename_candidates.append(extracted_name)
                logger.info(f"从路径提取文件名: {extracted_name}")
            else:
                filename_candidates.append(file_obj.name)
                logger.info(f"找到name: {file_obj.name}")
        
        # 方法3：file_path属性
        if hasattr(file_obj, 'file_path') and file_obj.file_path:
            if isinstance(file_obj.file_path, str) and os.path.sep in file_obj.file_path:
                extracted_name = os.path.basename(file_obj.file_path)
                filename_candidates.append(extracted_name)
                logger.info(f"从file_path提取文件名: {extracted_name}")
        
        # 方法4：字典结构
        if isinstance(file_obj, dict):
            for key in ['name', 'filename', 'orig_name', 'file_name']:
                if key in file_obj and file_obj[key]:
                    filename_candidates.append(file_obj[key])
                    logger.info(f"从字典提取文件名({key}): {file_obj[key]}")
        
        # 选择最佳候选
        for filename in filename_candidates:
            if filename and filename != "上传的文件":
                # 清理文件名，移除路径部分
                clean_name = os.path.basename(str(filename)) if os.path.sep in str(filename) else str(filename)
                if clean_name and clean_name != ".":
                    logger.info(f"最终文件名: {clean_name}")
                    return clean_name
        
        logger.warning(f"无法提取文件名，使用默认值: {default_name}")
        return default_name
    
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
