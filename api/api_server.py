import logging
import os
import shutil
import time
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, File, UploadFile, Header
from starlette.responses import JSONResponse

from config.app_config import AppConfig
from core.container import AppContainer
from data_loader import data_loader
from core.planner import TaskPlanner
from result.response_api import QueryResponse, QueryRequest, UploadResponse
from result.response_generator import process_tool_result
from logs.logger_config import setup_logger

from vector_store import get_or_create_vector_database

app = FastAPI(title="RAG Agent", version="1.0.3")

logger = setup_logger("api_server_tool_execute")

@app.post("/tool/execute", response_model=QueryResponse)
async def chat_with_session(request:QueryRequest,session_id:str = Header(None)):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    logger.info({
        "request_id": request_id,
        "event": "execute_tool",
        "time_stamp":datetime.now().isoformat(),
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
        response = process_tool_result(result,doc_agent,request,state)


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
        raise HTTPException(status_code=500, detail=f"request failed：{str(e)}")

@app.post("/upload",response_model=UploadResponse)
async def upload_document(file:UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split(".")[-1]
        # type check
        if file_extension not in AppConfig.vector.FILE_SUFFIX:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        upload_dir = AppConfig.vector.FILE_LOAD_PATH
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_path = os.path.join(upload_dir, f"{file_id}.{file_extension}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # chunks
        chunks = data_loader(file_path)
        # create vector db
        get_or_create_vector_database(chunks)

        return UploadResponse(
            message="File uploaded successfully",
            filename=file.filename,
            file_id=file_id
        )

    except Exception as e:
        logging.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




