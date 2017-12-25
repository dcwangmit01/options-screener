PYTHON ?= python

venv:
	if [ ! -d .venv ] ; then \
	  virtualenv -p python3 .venv; \
	fi

install:
	pip install --editable .

pep8:
	yapf -i $$(find * -type f -name '*.py')
	flake8 ./app ./tests

test:
	pip -q install -r test-requirements.txt
	pytest
	flake8 ./app ./tests

test_fixtures:
	mkdir -p tests/fixtures
	echo date > ./tests/fixtures/fixtures_last_updated.txt

dist: clean
	(cd $(BASE) && $(PYTHON) setup.py sdist)

run:
	options coveredcalls run config.yaml coveredcalls.csv
	options longputs run config.yaml longputs.csv
	options longcalls run config.yaml longcalls.csv

clean:
	find * -type f -name *.pyc | xargs rm -f
	find * -type f -name *~ |xargs rm -f
	find * -type d -name __pycache__ |xargs rm -rf
	rm -rf *.egg-info
	rm -rf dist/
	rm -f *.csv
