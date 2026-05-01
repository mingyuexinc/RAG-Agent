import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

from agent.orchestrator.planner import TaskPlanner
from agent.response.response_generator import process_tool_result
from api.schemas_response import QueryRequest, QueryResponse, UploadResponse
from infra.config.app_config import AppConfig
from infra.container import AppContainer
from infra.logs.logger_config import get_logger
from rag.ingestion.pipeline import create_default_pipeline

logger = get_logger("api_server_tool_execute")

app = FastAPI(title="RAG Agent", version="1.0.3")

data_dir = Path(__file__).parent.parent.parent / "data"
data_dir.mkdir(exist_ok=True)
app.mount("/file", StaticFiles(directory=str(data_dir)), name="file")


@app.get("/api/image")
async def get_image(path: str):
    """Return an image file through the API."""
    logger.info(f"API_IMAGE received request: path={path}")
    try:
        import mimetypes

        full_path = Path(__file__).parent.parent.parent / path
        logger.info(f"API_IMAGE resolved path: {full_path}")

        if not full_path.exists():
            logger.error(f"API_IMAGE file not found: {full_path}")
            raise HTTPException(status_code=404, detail="Image not found")

        if not full_path.is_file():
            logger.error(f"API_IMAGE path is not a file: {full_path}")
            raise HTTPException(status_code=404, detail="Image not found")

        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
        if full_path.suffix.lower() not in allowed_extensions:
            logger.error(f"API_IMAGE unsupported file type: {full_path.suffix}")
            raise HTTPException(status_code=400, detail="Unsupported file type")

        media_type, _ = mimetypes.guess_type(str(full_path))
        if not media_type:
            media_type = "image/webp"

        logger.info(f"API_IMAGE returning file: {full_path}")
        logger.info(f"API_IMAGE media type: {media_type}")
        logger.info(f"API_IMAGE file size: {full_path.stat().st_size} bytes")

        return FileResponse(
            path=str(full_path),
            media_type=media_type,
            filename=full_path.name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API_IMAGE failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health():
    """Health check used by the frontend."""
    return {"status": "ok"}


document_pipeline = create_default_pipeline(enable_vector_store=True)


@app.post("/tool/execute", response_model=QueryResponse)
async def chat_with_session(
    request: QueryRequest,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    session_id = x_session_id

    logger.info(
        {
            "request_id": request_id,
            "event": "execute_tool",
            "time_stamp": datetime.now().isoformat(),
            "received_session_id": session_id,
        }
    )

    try:
        planner = TaskPlanner()
        doc_agent = AppContainer.get_doc_agent()
        logger.info({"request_id": request_id, "event": "planning_start"})

        session_id = doc_agent.ensure_session(session_id)
        state = doc_agent.state_manager.load(session_id)
        plan = planner.analyze_task(request.query, state)

        logger.info(
            {
                "request_id": request_id,
                "event": "execution_start",
                "task_type": plan.task_type,
                "tools": plan.tools,
            }
        )

        result = doc_agent.execute_with_session(plan, session_id)
        response = await process_tool_result(result, doc_agent, request, state)
        duration = time.time() - start_time

        logger.info(
            {
                "request_id": request_id,
                "event": "execution_end",
                "duration": round(duration, 1),
                "status": result.success,
            }
        )

        return JSONResponse(
            content=response.dict(),
            headers={"X-Session-ID": session_id},
        )
    except HTTPException as e:
        duration = time.time() - start_time
        logger.error(
            {
                "request_id": request_id,
                "event": "execution_failed",
                "status": "error",
                "duration": duration * 1000,
                "error_message": e.detail,
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            {
                "request_id": request_id,
                "event": "execution_failed",
                "status": "error",
                "duration": duration * 1000,
                "error_message": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=UploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload one or more documents and process them through the ingestion pipeline."""
    try:
        uploaded_files = []
        new_docs_metadata = []
        upload_dir = AppConfig.vector.FILE_LOAD_PATH
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        for file in files:
            file_id = str(uuid.uuid4())
            file_extension = file.filename.split(".")[-1].lower()
            logger.info(f"Processing upload: {file.filename}, extension={file_extension}")

            if file_extension not in AppConfig.vector.FILE_SUFFIX:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file_extension}",
                )

            file_path = os.path.join(upload_dir, f"{file_id}.{file_extension}")
            try:
                await file.seek(0)
                content = await file.read()
                logger.info(f"Read upload: {file.filename}, size={len(content)} bytes")

                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                logger.info(f"Saved upload: {file_path}")
            except Exception as e:
                logger.error(f"File processing failed {file.filename}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"File processing failed: {str(e)}",
                )

            doc_metadata = document_pipeline.process_document(file_path, file_id, file.filename)
            if doc_metadata:
                new_docs_metadata.append(
                    {
                        "file_id": file_id,
                        "filename": file.filename,
                        "doc_metadata": doc_metadata,
                    }
                )
                uploaded_files.append(
                    {
                        "filename": file.filename,
                        "file_id": file_id,
                        "status": "new",
                    }
                )
            else:
                uploaded_files.append(
                    {
                        "filename": file.filename,
                        "file_id": file_id,
                        "status": "duplicate",
                    }
                )
                os.remove(file_path)

        total_files = len(uploaded_files)
        new_files = len([f for f in uploaded_files if f["status"] == "new"])
        duplicate_files = total_files - new_files
        logger.info(f"Upload response: total={total_files}, new={new_files}")

        if total_files == 1:
            file_info = uploaded_files[0]
            response = UploadResponse(
                message="File uploaded successfully",
                filename=file_info["filename"],
                file_id=file_info["file_id"],
            )
            logger.info(f"Single upload response: {response}")
            return response

        if new_files > 0:
            message = f"Successfully processed {new_files} new files"
            if duplicate_files > 0:
                message += f", skipped {duplicate_files} duplicates"
        else:
            message = f"All {duplicate_files} files already exist, no new files processed"

        response = UploadResponse(
            message=message,
            filename=", ".join([f["filename"] for f in uploaded_files]),
            file_id=", ".join([f["file_id"] for f in uploaded_files]),
        )
        logger.info(f"Multi upload response: {response}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
