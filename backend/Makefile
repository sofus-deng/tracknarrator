.PHONY: dev test e2e ci clean seed

dev:
	uv run uvicorn tracknarrator.api:app --host 0.0.0.0 --port 8000 --reload

test:
	uv run pytest -q

e2e:
	uv run pytest -q tests/test_e2e_pipeline.py

ci:
	uv run pytest -q && uv run pytest -q tests/test_e2e_pipeline.py

seed:
	uv run python -c "import json,urllib.request; d=json.load(open('../fixtures/bundle_sample_barber.json')); req=urllib.request.Request('http://127.0.0.1:8000/dev/seed', data=json.dumps(d).encode('utf-8'), headers={'Content-Type':'application/json'}); print(urllib.request.urlopen(req).read().decode())"

clean:
	rm -rf .coverage htmlcov/ .pytest_cache/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

demo:
	bash demo/run_demo.sh