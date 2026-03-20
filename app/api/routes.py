import os
import shutil
import time
import uuid
from datetime import datetime
from typing import List
from pathlib import Path

from fastapi import FastAPI, HTTPException, File, UploadFile, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.responses import JSONResponse

from agent.orchestrator.planner import TaskPlanner
from app.api.schemas_response import QueryResponse, QueryRequest, UploadResponse
from infra.config.app_config import AppConfig
from infra.container import AppContainer
from infra.logs.logger_config import setup_logger

from agent.response.response_generator import process_tool_result

# 使用新的pipeline导入
from rag.ingestion.pipeline import create_default_pipeline


# 使用统一的日志配置
logger = setup_logger("api_server_tool_execute")

app = FastAPI(title="RAG Agent", version="1.0.3")

# 添加静态文件服务
# 使用绝对路径
data_dir = Path(__file__).parent.parent.parent / "data"
data_dir.mkdir(exist_ok=True)  # 确保目录存在

app.mount("/file", StaticFiles(directory=str(data_dir)), name="file")


@app.get("/health")
async def health():
    """健康检查，供前端判断是否已连接后端"""
    return {"status": "ok"}

# 创建全局pipeline实例
document_pipeline = create_default_pipeline(enable_vector_store=True)

@app.post("/tool/execute", response_model=QueryResponse)
async def chat_with_session(request:QueryRequest, x_session_id: str = Header(None, alias="X-Session-ID")):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 使用标准化的session_id
    session_id = x_session_id
    logger.info({
        "request_id": request_id,
        "event": "execute_tool",
        "time_stamp":datetime.now().isoformat(),
        "received_session_id": session_id
    })

    try:
        planner = TaskPlanner()
        # init agent
        doc_agent = AppContainer.get_doc_agent()

        logger.info({
            "request_id": request_id,
            "event":"planning_start",
        })

        session_id = doc_agent.ensure_session(session_id)
        state = doc_agent.state_manager.load(session_id)

        plan = planner.analyze_task(request.query,state)

        logger.info({
            "request_id": request_id,
            "event": "execution_start",
            "task_type":plan.task_type,
            "tools":plan.tools
        })

        result = doc_agent.execute_with_session(plan,session_id)
        response = await process_tool_result(result,doc_agent,request,state)


        duration = time.time() - start_time

        logger.info({
            "request_id": request_id,
            "event": "execution_end",
            "duration":round(duration,1),
            "status":result.success
        })
        return JSONResponse(
            content=response.dict(),
            headers={"X-Session-ID": session_id}
        )

    except Exception as e:
        duration = time.time() - start_time
        logger.error({
            "request_id": request_id,
            "event": "execution_failed",
            "status":"error",
            "duration":duration*1000,
            "error_message":str(e),
            "error_type":type(e).__name__
        },exc_info=True)
        raise HTTPException(status_code=500)

@app.post("/upload", response_model=UploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    统一的文档上传接口，支持单文件和多文件上传
    使用新的pipeline处理方式
    """
    try:
        uploaded_files = []
        new_docs_metadata = []
        
        upload_dir = AppConfig.vector.FILE_LOAD_PATH
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        # 处理所有上传的文件
        for file in files:
            file_id = str(uuid.uuid4())
            # 统一使用小写扩展名，避免 .PDF / .Docx 等大小写导致类型判断失败
            file_extension = file.filename.split(".")[-1].lower()
            
            logger.info(f"处理文件: {file.filename}, 扩展名: {file_extension}")
            
            # 类型检查
            if file_extension not in AppConfig.vector.FILE_SUFFIX:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
                
            file_path = os.path.join(upload_dir, f"{file_id}.{file_extension}")
            
            try:
                # 重置文件指针到开始位置
                await file.seek(0)
                logger.info(f"文件指针已重置: {file.filename}")
                
                # 读取文件内容
                content = await file.read()
                logger.info(f"文件内容读取完成: {file.filename}, 大小: {len(content)} bytes")
                
                # 写入本地文件
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                
                logger.info(f"文件保存成功: {file_path}")
                
            except Exception as e:
                logger.error(f"文件处理失败 {file.filename}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")
            
            # 使用新的pipeline处理文档，自动去重和向量化
            doc_metadata = document_pipeline.process_document(file_path, file_id, file.filename)
            
            if doc_metadata:
                # 新文档，记录其 metadata
                new_docs_metadata.append({
                    "file_id": file_id,
                    "filename": file.filename,
                    "doc_metadata": doc_metadata
                })
                uploaded_files.append({
                    "filename": file.filename,
                    "file_id": file_id,
                    "status": "new"
                })
            else:
                # 重复文档
                uploaded_files.append({
                    "filename": file.filename,
                    "file_id": file_id,
                    "status": "duplicate"
                })
                # 清理重复文件
                os.remove(file_path)
        
        # 构造响应
        total_files = len(uploaded_files)
        new_files = len([f for f in uploaded_files if f["status"] == "new"])
        duplicate_files = total_files - new_files

        logger.info(f"构造响应: 总文件数={total_files}, 新文件数={new_files}")

        if total_files == 1:
            file_info = uploaded_files[0]
            message = f"File uploaded successfully"
            response = UploadResponse(
                message=message,
                filename=file_info["filename"],
                file_id=file_info["file_id"]
            )
            logger.info(f"单文件响应: {response}")
            return response
        else:
            if new_files > 0:
                message = f"Successfully processed {new_files} new files"
                if duplicate_files > 0:
                    message += f", skipped {duplicate_files} duplicates"
            else:
                message = f"All {duplicate_files} files already exist, no new files processed"

            response = UploadResponse(
                message=message,
                filename=", ".join([f["filename"] for f in uploaded_files]),
                file_id=", ".join([f["file_id"] for f in uploaded_files])
            )
            logger.info(f"多文件响应: {response}")
            return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")





