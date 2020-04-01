PYTHON ?= python

DATE:=$(shell date "+%Y%m%d")

venv:
	if [ ! -d .venv ] ; then \
	  virtualenv -p python3 .venv; \
	fi

install:
	pipenv install
	pipenv install --dev
	pip install --editable .

pep8:
	yapf -i $$(find * -type f -name '*.py')
	flake8 ./app ./tests

test:
	pytest
	flake8 ./app ./tests

test_fixtures:
	mkdir -p tests/fixtures
	echo date > ./tests/fixtures/fixtures_last_updated.txt

dist: clean
	(cd $(BASE) && $(PYTHON) setup.py sdist)

run:
	options coveredcalls run config.yaml $(DATE)_coveredcalls.csv
	options longputs run config.yaml $(DATE)_longputs.csv
	options longcalls run config.yaml $(DATE)_longcalls.csv

clean:
	find * -type f -name *.pyc | xargs rm -f
	find * -type f -name *~ |xargs rm -f
	find * -type d -name __pycache__ |xargs rm -rf
	rm -rf *.egg-info
	rm -rf dist/
	rm -f *.csv
