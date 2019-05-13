COMNETSEMU = comnetsemu/*.py
TEST = comnetsemu/test/*.py
EXAMPLES = examples/*.py
PYTHON ?= python3
PYSRC = $(COMNETSEMU) $(EXAMPLES)
P8IGN = E251,E201,E302,E202,E126,E127,E203,E226
PREFIX ?= /usr
DOCDIRS = doc/html doc/latex

CFLAGS += -Wall -Wextra

all: codecheck test

clean:
	rm -rf build dist *.egg-info *.pyc $(DOCDIRS)

codecheck: $(PYSRC)
	-echo "Running code check"
	pyflakes $(PYSRC)
	pylint --rcfile=.pylint $(PYSRC)
	pep8 --repeat --ignore=$(P8IGN) `ls $(PYSRC)`

errcheck: $(PYSRC)
	-echo "Running check for errors only"
	pyflakes $(PYSRC)
	pylint -E --rcfile=.pylint $(PYSRC)

min_test: $(COMNETSEMU) $(TEST)
	-echo "Running minimal tests"

test: $(COMNETSEMU) $(TEST)
	-echo "Running tests"

slowtest: $(COMNETSEMU)
	-echo "Running slower tests (walkthrough, examples)"

install:
	$(PYTHON) setup.py install

develop: $(MNEXEC) $(MANPAGES)
	$(PYTHON) setup.py develop

.PHONY: doc

doc: $(PYSRC)
	doxygen doc/doxygen.cfg
	make -C doc/latex
