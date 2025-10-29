.PHONY: dev test clean

dev:
	uv run uvicorn tracknarrator.api:app --host 0.0.0.0 --port 8000 --reload

test:
	uv run pytest -q

clean:
	rm -rf .coverage htmlcov/ .pytest_cache/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete