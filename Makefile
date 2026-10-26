.PHONY: dev test eval install

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3.12 -m venv $(VENV)
	$(PIP) install -e ".[dev,synth,ocr,eval]"

dev: install
	DATABASE_URL=sqlite:///data/ap_desk.db $(PY) -m api.seed
	DATABASE_URL=sqlite:///data/ap_desk.db $(PY) -m api.serve &
	sleep 2
	cd ui && npm ci && VITE_API_BASE=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1

test:
	$(PY) -m pytest -q

eval: install
	$(PY) -m datasets.synth --n 50 --seed 7 --scanned-ratio 0 --out datasets/generated
	$(PY) -m evals.run --pred truth --truth datasets/generated --report evals/out/report-smoke.json
	$(PY) -m evals.gate --report evals/out/report-smoke.json
