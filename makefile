PYTHON := ./.venv/bin/python
PIP := $(PYTHON) -m pip
VENV := .venv

.PHONY: all install venv run-generator run-main shell clean

all: run-main

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install -r requirements.txt

run-generator: install
	$(PYTHON) data_generator/generator.py

run: install
	$(PYTHON) main.py

test: install
	$(PYTHON) -m pytest tests/test_pipeline.py

shell:
	@echo "Activate with: source $(VENV)/bin/activate"

clean:
	rm -rf $(VENV)
