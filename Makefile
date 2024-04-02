lint:
	mypy --install-types --non-interactive --config-file setup.cfg .
	flake8 .

style:
	black --target-version py311 --line-length 120 --check --diff .
	isort . -c --diff

test: style lint
	pytest -vv tests/

isort:
	isort .

black:
	black --target-version py311 --line-length 120 .

format: isort black

ftest: format test

flint: format lint
