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
	-Werror \
	-Wconversion \
	-Wpedantic \
	-std=c99 \
	-g \
	--coverage

test:
	env CFLAGS=--coverage python3 setup.py test
	$(MAKE) test-sdist
	$(MAKE) test-c
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
	$(CC) -DDETOOLS_CONFIG_FILE_IO=0 -c src/c/detools.c \
	    -o detools.no-file-io.o
	$(CC) -DDETOOLS_CONFIG_COMPRESSION_NONE=0 -c src/c/detools.c \
	    -o detools.no-none.o
	$(CC) -DDETOOLS_CONFIG_COMPRESSION_LZMA=0 -c src/c/detools.c \
	    -o detools.no-lzma.o
	$(CC) -DDETOOLS_CONFIG_COMPRESSION_CRLE=0 -c src/c/detools.c \
	    -o detools.no-crle.o
	$(CC) $(CFLAGS) $(C_SOURCES) -llzma -o main
	./main
	$(MAKE) -C src/c
	src/c/detools-apply-patch tests/files/foo.old tests/files/foo.patch foo.new
	cmp foo.new tests/files/foo.new

release-to-pypi:
	python3 setup.py sdist
	twine upload dist/*
