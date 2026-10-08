from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from spreadai.generate import make_statement, render_pdf
from spreadai.llm.fake import FakeLLM
from spreadai.main import app
from spreadai.service import SpreadService


def test_spread_text_full_result(service, statement_text):
    result = service.spread_text(statement_text)
    assert result["validation"]["balanced"] is True
    assert result["needs_human_review"] is False
    assert result["ratios"]["current_ratio"] is not None
    assert result["memo"].startswith("CREDIT MEMO")
    assert result["method"] == "text"


def test_spread_routes_low_confidence_to_review(service):
    result = service.spread_text("Company: X\nRevenue: 1000")
    assert result["needs_human_review"] is True


def test_service_uses_injected_llm_for_memo(statement_text):
    service = SpreadService(memo_llm=FakeLLM("LLM-written memo."))
    result = service.spread_text(statement_text)
    assert result["memo"] == "LLM-written memo."


def test_spread_pdf(service):
    statement = make_statement(3)
    with tempfile.TemporaryDirectory() as d:
        path = render_pdf(statement, str(Path(d) / "s.pdf"))
        result = service.spread_pdf(path)
    assert result["method"] == "pdf"
    assert result["validation"]["balanced"] is True


client = TestClient(app)


def test_api_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_api_spread_text(statement_text):
    response = client.post("/spread/text", json={"text": statement_text})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["validation"]["balanced"] is True
    assert "memo" in body


def test_api_rejects_empty_text():
    assert client.post("/spread/text", json={"text": "   "}).status_code == 422


def test_api_spread_pdf_upload():
    statement = make_statement(5)
    with tempfile.TemporaryDirectory() as d:
        path = render_pdf(statement, str(Path(d) / "s.pdf"))
        with open(path, "rb") as fh:
            response = client.post(
                "/spread/pdf", files={"file": ("s.pdf", fh, "application/pdf")}
            )
    assert response.status_code == 200, response.text
    assert response.json()["method"] == "pdf"
