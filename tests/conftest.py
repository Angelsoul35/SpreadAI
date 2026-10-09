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


@pytest.fixture(scope="session")
def real_train():
    from spreadai.real_data import load_dataset

    return load_dataset("train")


@pytest.fixture(scope="session")
def real_test():
    from spreadai.real_data import load_dataset

    return load_dataset("test")
