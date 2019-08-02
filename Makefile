COMNETSEMU = comnetsemu/*.py
CE_BIN = bin/ce
TEST = comnetsemu/test/*.py
EXAMPLES = examples/*.py
PYSRC = $(COMNETSEMU) $(EXAMPLES) $(CE_BIN) $(TEST)
PYTHON ?= python3
P8IGN = E251,E201,E302,E202,E126,E127,E203,E226
PREFIX ?= /usr
DOCDIRS = doc/html doc/latex

CFLAGS += -Wall -Wextra

all: errcheck

clean:
	rm -rf build dist *.egg-info *.pyc $(DOCDIRS)

codecheck: $(PYSRC)
	@echo "*** Running code check"
	pyflakes $(PYSRC)
	pylint --rcfile=.pylint $(PYSRC)
	pep8 --repeat --ignore=$(P8IGN) `ls $(PYSRC)`

errcheck: $(PYSRC)
	@echo "*** Running check for errors only"
	pyflakes $(PYSRC)
	pylint -E --rcfile=.pylint $(PYSRC)

test_examples: $(COMNETSEMU)
	@echo "*** Running basic functional examples of the emulator"
	$(PYTHON) ./examples/dockerhost.py
	$(PYTHON) ./examples/dockerindocker.py

test_examples_full: $(COMNETSEMU) $(EXAMPLES)
	@echo "*** Running all examples added by ComNetsEmu (Exclude Mininet's official examples)"
	@echo "*** WARN: It takes time..."
	@echo "**** Basic functional examples of the emulator"
	$(PYTHON) ./examples/dockerhost.py
	$(PYTHON) ./examples/dockerindocker.py
	@echo "**** Examples for security..."
	$(PYTHON) ./examples/nftables.py
	$(PYTHON) ./examples/wireguard.py

test: $(COMNETSEMU) $(TEST)
	@echo "Running tests of ComNetsEmu python module."
	$(PYTHON) ./comnetsemu/test/runner.py -v

check_installer: ./util/install.sh
	@ echo "*** Check installer"
	bash ./check_installer.sh


install:
	$(PYTHON) setup.py install

develop: $(MNEXEC) $(MANPAGES)
	$(PYTHON) setup.py develop

.PHONY: doc

doc: $(PYSRC)
	doxygen doc/Doxyfile

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
