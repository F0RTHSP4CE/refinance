.PHONY: lint
lint:
	mypy --install-types --non-interactive --config-file setup.cfg .
	flake8 .

.PHONY: style
style:
	black --target-version py311 --line-length 120 --check --diff .
	isort . -c --diff

.PHONY: test
test: style lint
	pytest -vv tests/

.PHONY: isort
isort:
	isort .

.PHONY: black
black:
	black --target-version py311 --line-length 120 .

.PHONY: format
format: isort black

.PHONY: ftest
ftest: format test

.PHONY: flint
flint: format lint
