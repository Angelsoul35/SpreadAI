"""SpreadAI HTTP API."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from .service import SpreadService

app = FastAPI(
    title="SpreadAI",
    version="1.0.0",
    summary="Extract, validate, and analyse financial statements, and draft a credit memo.",
)

service = SpreadService()


class SpreadTextRequest(BaseModel):
    text: str


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.post("/spread/text", tags=["spread"])
def spread_text(request: SpreadTextRequest) -> dict:
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="text is empty")
    return service.spread_text(request.text)


@app.post("/spread/pdf", tags=["spread"])
async def spread_pdf(file: UploadFile = File(...)) -> dict:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="please upload a .pdf file")
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        return service.spread_pdf(tmp_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)
