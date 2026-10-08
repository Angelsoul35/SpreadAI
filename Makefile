.PHONY: install test lint run demo sample clean

install:
	pip install -e ".[dev]"

test:
	pytest --cov=spreadai --cov-report=term-missing

lint:
	ruff check spreadai tests

run:
	uvicorn spreadai.main:app --reload --port 8000

sample:          ## Generate a sample financial-statement PDF in out/
	python -m spreadai.generate --pdf out/sample_statement.pdf

demo:            ## Generate a statement, spread it, and print the result
	python -m spreadai.cli demo

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov out/*.pdf
	touch out/.gitkeep
