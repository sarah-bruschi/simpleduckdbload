PYTHON := ./.venv/bin/python

install:
	$(PYTHON) -m pip install -r requirements.txt

run-generator:
	$(PYTHON) data_generator/generator.py
