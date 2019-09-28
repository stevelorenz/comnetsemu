# vim:ft=make

COMNETSEMU = comnetsemu/*.py
CE_BIN = bin/ce
UNITTESTS = comnetsemu/test/unit/*.py
EXAMPLES = examples/*.py
PYSRC = $(COMNETSEMU) $(EXAMPLES) $(CE_BIN) $(UNITTESTS)
PYTHON ?= python3
PYTYPE = pytype
P8IGN = E251,E201,E302,E202,E126,E127,E203,E226
PREFIX ?= /usr
DOCDIRS = doc/html doc/latex

CFLAGS += -Wall -Wextra

all: errcheck

clean:
	rm -rf build dist *.egg-info *.pyc $(DOCDIRS)

codecheck: $(PYSRC)
	@echo "*** Running checks for code quality"
	$(PYTHON) -m pyflakes $(PYSRC)
	$(PYTHON) -m pylint --rcfile=.pylint $(PYSRC)
	$(PYTHON) -m pep8 --repeat --ignore=$(P8IGN) `ls $(PYSRC)`

errcheck: $(PYSRC)
	@echo "*** Running checks for errors only"
	$(PYTHON) -m pyflakes $(PYSRC)
	$(PYTHON) -m pylint -E --rcfile=.pylint $(PYSRC)

typecheck: $(PYSRC)
	@echo "*** Running type checks with $(PYTYPE)..."
	$(PYTYPE) ./comnetsemu/net.py

test-examples: $(COMNETSEMU) $(EXAMPLES)
	cd ./examples && bash ./run.sh

test-examples-all: $(COMNETSEMU) $(EXAMPLES)
	cd ./examples && bash ./run.sh -a

test: $(COMNETSEMU) $(UNITTESTS)
	@echo "Running all unit tests of ComNetsEmu python package."
	$(PYTHON) ./comnetsemu/test/unit/runner.py -v

coverage: $(COMNETSEMU) $(UNITTESTS)
	@echo "Running coverage tests of ComNetsEmu core functions."
	$(PYTHON) -m coverage run --source ./comnetsemu ./comnetsemu/test/unit/runner.py -v
	$(PYTHON) -m coverage report -m

installercheck: ./util/install.sh
	@ echo "*** Check installer"
	bash ./check_installer.sh

format: $(PYSRC)
	@echo "Format Python sources with black"
	black $(PYSRC)


install:
	$(PYTHON) setup.py install

develop: $(MNEXEC) $(MANPAGES)
	$(PYTHON) setup.py develop

.PHONY: doc

doc: $(PYSRC)
	@echo "Build documentation in HTML format"
	cd ./doc/ && make html

build-test-containers:
	@echo "Build all test containers"
	cd ./test_containers/ && ./build.sh -a

## Cleanup utilities

rm-all-containers:
	@echo "Remove all docker containers"
	docker container rm $$(docker ps -aq) -f

rm-dangling-images:
	@echo "Remove all dangling docker images"
	docker rmi $$(docker images -f "dangling=true" -q)

pp-empty-dirs:
	@echo "Print empty directories"
	@find -maxdepth 3 -type d -empty
