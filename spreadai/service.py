"""The spreading flow: extract -> validate -> ratios -> memo -> review flag."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings, get_settings
from .extract.base import ExtractionResult
from .extract.pdf import parse_pdf
from .extract.text_parser import parse_text
from .llm import LLMClient
from .memo import llm_memo, template_memo
from .ratios import compute_ratios
from .validate import validate


@dataclass
class SpreadService:
    settings: Settings | None = None
    memo_llm: LLMClient | None = None  # injected in tests

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def _finalize(self, extraction: ExtractionResult) -> dict:
        statement = extraction.statement
        validation = validate(
            statement, extraction.field_coverage, self.settings.balance_tolerance
        )
        ratios = compute_ratios(statement)

        needs_review = (
            validation.confidence < self.settings.confidence_review_threshold
            or not validation.balanced
        )

        if self.settings.memo_mode == "llm" or self.memo_llm is not None:
            memo = llm_memo(
                statement, validation, llm=self.memo_llm,
                provider_spec=self.settings.llm_providers,
            )
        else:
            memo = template_memo(statement, validation)

        return {
            "company": statement.company,
            "period": statement.period,
            "currency": statement.currency,
            "method": extraction.method,
            "statement": statement.model_dump(),
            "summary": statement.summary(),
            "ratios": ratios,
            "validation": validation.as_dict(),
            "needs_human_review": needs_review,
            "memo": memo,
        }

    def spread_text(self, text: str) -> dict:
        return self._finalize(parse_text(text))

    def spread_pdf(self, path: str) -> dict:
        return self._finalize(parse_pdf(path))

    def spread_extraction(self, extraction: ExtractionResult) -> dict:
        """Spread an already-extracted statement (e.g. from the LLM extractor)."""
        return self._finalize(extraction)
