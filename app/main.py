from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db, reset_incompatible_sqlite_schema
from app.schemas import SupportMessageRequest, SupportMessageResponse
from app.services.orchestrator import handle_support_message, initialize_runtime


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
