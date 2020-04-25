PYTHON ?= python

DATE:=$(shell date "+%Y%m%d")
APP:=options-screener

install:  ## Install an editable version of this app
install:
	pipenv run pip install --editable .

uninstall:  ## Uninstall this app
	pipenv run pip uninstall -y $(APP)

format:  ## Auto-format and check pep8
	pipenv run yapf -i $$(find * -type f -name '*.py')
	pipenv run flake8 ./app ./tests

test:  ## Run tests
	pipenv run pytest
	pipenv run flake8 ./app ./tests

dist:  ## Create a binary dist
dist: clean
	(cd $(BASE) && $(PYTHON) setup.py sdist)

.PHONY: tags
tags:  ## Create tags for code navigation
	rm -f TAGS
	etags -a $$(find * -type f -name '*.py')

run:
	$(APP) coveredcalls run config.yaml $(DATE)_coveredcalls.csv
	$(APP) longputs run config.yaml $(DATE)_longputs.csv
	$(APP) longcalls run config.yaml $(DATE)_longcalls.csv

clean:  ## Clean all temporary files
clean:
	pipenv --rm || true
	find * -type f -name *.pyc | xargs rm -f
	find * -type f -name *~ | xargs rm -f
	find * -type d -name __pycache__ | xargs rm -rf
	rm -rf *.egg-info
	rm -rf dist/
	rm -f *.csv

include scripts/help.mk  # Must be included last.
