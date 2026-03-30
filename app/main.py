from __future__ import annotations

import io
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db, reset_incompatible_sqlite_schema
from app.schemas import Attachment, SupportMessageRequest, SupportMessageResponse
from app.services.document_review import review_uploaded_documents
from app.services.orchestrator import handle_support_message, initialize_runtime
from app.services.platform_registry import registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    reset_incompatible_sqlite_schema(str(engine.url))
    Base.metadata.create_all(bind=engine)
    initialize_runtime()
    yield


app = FastAPI(title="OpenClaw AI Support Core", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/support/message", response_model=SupportMessageResponse)
def support_message(payload: SupportMessageRequest, db: Session = Depends(get_db)) -> SupportMessageResponse:
    return handle_support_message(db, payload)


@app.post("/v1/debug/review-documents")
async def debug_review_documents(
    files: list[UploadFile] = File(...),
    platform_id: str = Form(default="okx_help"),
) -> dict:
    """
    测试端点：直接向 AI Server 上传文件，验证 document_review 能力是否正常工作。

    - 支持多文件同时上传（图片/PDF/DOCX/XLSX）
    - 不走完整的 orchestrator，直接调用 review_uploaded_documents
    - 返回原始审查结果，供调试用
    """
    attachments: list[Attachment] = []
    for f in files:
        content = await f.read()
        size = len(content)

        # 写临时文件，提供 file:// URL 给 document_review 读取
        suffix = Path(f.filename or "upload").suffix.lower()
        tmp_path = Path("/tmp/ai-server-debug-uploads")
        tmp_path.mkdir(exist_ok=True)
        tmp_file = tmp_path / f"{datetime.now(timezone.utc).timestamp()}_{f.filename}"
        tmp_file.write_bytes(content)

        attachments.append(
            Attachment(
                attachment_id=f"debug-{datetime.now(timezone.utc).timestamp()}",
                name=f.filename or "unknown",
                mime_type=f.content_type or "application/octet-stream",
                url=str(tmp_file),
                size_bytes=size,
            )
        )

    try:
        package = registry.get(platform_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found. Available: {list(registry.packages.keys())}")

    result = review_uploaded_documents(attachments, package, datetime.now(timezone.utc))

    return {
        "platform_id": platform_id,
        "files_received": [a.name for a in attachments],
        "review_result": result.model_dump(mode="json"),
    }
