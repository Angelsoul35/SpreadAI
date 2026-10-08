from __future__ import annotations

import json

import pytest

from spreadai.extract.llm_extractor import LLMExtractor
from spreadai.llm.base import LLMError
from spreadai.llm.cascade import CascadeLLM
from spreadai.llm.factory import build_llm
from spreadai.llm.fake import FailingLLM, FakeLLM
from spreadai.memo import llm_memo
from spreadai.validate import validate


def test_cascade_falls_back():
    cascade = CascadeLLM([FailingLLM("a"), FakeLLM("ok")])
    assert cascade.complete("s", "p").text == "ok"


def test_cascade_all_fail_raises():
    with pytest.raises(LLMError):
        CascadeLLM([FailingLLM("a"), FailingLLM("b")]).complete("s", "p")


def test_build_llm_cascade():
    multi = build_llm("anthropic,openai,ollama")
    assert isinstance(multi, CascadeLLM)
    assert [c.name for c in multi.clients] == ["anthropic", "openai", "ollama"]


def test_llm_extractor_parses_json():
    payload = {
        "company": "Fake Co", "period": "FY2025", "currency": "COP",
        "cash": 100, "revenue": 1000, "cost_of_goods_sold": 600,
    }
    extractor = LLMExtractor(llm=FakeLLM(json.dumps(payload)))
    result = extractor.extract("messy statement text")
    assert result.method == "llm"
    assert result.statement.company == "Fake Co"
    assert result.statement.balance_sheet.cash == 100
    assert result.statement.income_statement.revenue == 1000
    assert "cash" in result.found_keys


def test_llm_extractor_handles_bad_json():
    result = LLMExtractor(llm=FakeLLM("not json at all")).extract("text")
    assert result.found_keys == []


def test_llm_memo_uses_injected_client(statement):
    v = validate(statement, field_coverage=1.0)
    memo = llm_memo(statement, v, llm=FakeLLM("A short credit memo."))
    assert memo == "A short credit memo."
