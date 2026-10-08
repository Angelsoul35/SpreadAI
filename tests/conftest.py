from __future__ import annotations

import pytest

from spreadai.generate import make_statement, render_text
from spreadai.service import SpreadService


@pytest.fixture
def statement():
    return make_statement(7)


@pytest.fixture
def statement_text(statement):
    return render_text(statement)


@pytest.fixture
def service():
    return SpreadService()
