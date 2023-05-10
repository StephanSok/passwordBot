.PHONY: run
run:
	python3 bot.py

.PHONY: install
install:
	pip install -r requirements.txt

#.PHONY: test
#test: # Runs pytest
#	pytest tests/test.py

.PHONY: lint
lint: # Lint code
	black --line-length 93 --skip-string-normalization .
	flake8 --ignore=E203,W503,E722 --max-line-length=93 --exclude venv .
	mypy --ignore-missing-imports --exclude venv .

.PHONY: check
check: lint test