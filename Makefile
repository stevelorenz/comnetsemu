# vim:ft=make

COMNETSEMU = $(shell find ./comnetsemu/ -name '*.py')
CE_BIN = bin/ce
UNITTESTS = comnetsemu/test/unit/*.py
TESTS = $(UNITTESTS) comnetsemu/test/*.py
EXAMPLES = $(shell find ./examples/ -name '*.py')
PYSRC = $(COMNETSEMU) $(EXAMPLES) $(CE_BIN) $(TESTS)
PYTHON ?= python3
PIP ?= pip3
PYTYPE = pytype
FLAKE8IGNORE=W503,E501,C0330
DOCBUILD = doc/build/
BASHSRC = $(shell find ./ -name '*.sh')
PYC = $(shell find ./ -name '*.pyc')

all: errcheck

.PHONY: clean
clean:
	@echo "*** Remove Python dist files, eggs and documentation build directory"
	rm -rf build dist *.egg-info $(PYC) $(DOCBUILD)

.PHONY: codecheck
codecheck: $(PYSRC)
	@echo "Run checks for Python sources quality"
	-$(PYTHON) -m flake8 --ignore=W503,E501,C0330 --max-complexity 10 $(PYSRC)
	-$(PYTHON) -m pylint --rcfile=.pylint $(PYSRC)
	@echo "*** Run shellcheck for Bash sources"
	-shellcheck $(BASHSRC)

.PHONY: errcheck
errcheck: $(PYSRC)
	@echo "Run checks for Python sources errors"
	$(PYTHON) -m flake8 --ignore=$(FLAKE8IGNORE) $(PYSRC)
	$(PYTHON) -m pylint -E --rcfile=.pylint $(PYSRC)
	@echo "Run shellcheck for Bash sources"
	shellcheck $(BASHSRC)

# typecheck: $(PYSRC)
# 	@echo "*** Running type checks with $(PYTYPE)..."
# 	$(PYTYPE) $(COMNETSEMU)

.PHONY: test-examples
test-examples: $(COMNETSEMU) $(EXAMPLES)
	cd ./examples && bash ./run.sh

.PHONY: test-examples-all
test-examples-all: $(COMNETSEMU) $(EXAMPLES)
	cd ./examples && bash ./run.sh -a

.PHONY: test
test: $(COMNETSEMU) $(UNITTESTS)
	@echo "Run all unit tests of ComNetsEmu Python package."
	$(PYTHON) ./comnetsemu/test/unit/runner.py -v

.PHONY: test-quick
test-quick: $(COMNETSEMU) $(UNITTESTS)
	@echo "Run quick unit tests of ComNetsEmu Python package."
	$(PYTHON) ./comnetsemu/test/unit/runner.py -v -quick

.PHONY: coverage
coverage: $(COMNETSEMU) $(UNITTESTS)
	@echo "Run coverage tests of ComNetsEmu core functions."
	$(PYTHON) -m coverage run --source ./comnetsemu ./comnetsemu/test/unit/runner.py -v
	$(PYTHON) -m coverage report -m

.PHONY: format
format: $(PYSRC)
	@echo "Format Python sources with black"
	black $(PYSRC)

.PHONY: install
install:
	$(PIP) install .

.PHONY: develop
develop:
	$(PIP) install --editable .

.PHONY: doc
doc: $(PYSRC)
	@echo "Build documentation in HTML format"
	-rm ./doc/api/*.rst
	-rm -r ./doc/build/
	# Use sphinx-apidoc to generate API sources
	cd ./doc/ && sphinx-apidoc -o api ../comnetsemu -H 'Python API' --separate
	# Build HTML files
	cd ./doc/ && make html
