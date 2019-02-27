ifeq ($(origin CC), default)
CC = gcc
endif

C_SOURCES := \
	tests/main.c \
	src/c/detools.c

CFLAGS := \
	-Wall \
	-Wextra \
	-Wdouble-promotion \
	-Wfloat-equal \
	-Wformat=2 \
	-Wshadow \
	-Werror

test:
	env CFLAGS=--coverage python3 setup.py test
	$(MAKE) test-sdist
	find . -name "*.gcno" -exec gcov {} +

test-sdist:
	rm -rf dist
	python3 setup.py sdist
	cd dist && \
	mkdir test && \
	cd test && \
	tar xf ../*.tar.gz && \
	cd detools-* && \
	python3 setup.py test

test-c:
	$(CC) $(CFLAGS) -Wconversion -Wpedantic -std=c99 -O3 $(C_SOURCES) \
	    -o main
	./main

release-to-pypi:
	python3 setup.py sdist
	twine upload dist/*
