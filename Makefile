ifeq ($(origin CC), default)
CC = gcc
endif

C_SOURCES := \
	tests/main.c \
	src/c/detools.c \
	src/c/heatshrink/heatshrink_decoder.c

CFLAGS := \
	-Wall \
	-Wextra \
	-Wdouble-promotion \
	-Wfloat-equal \
	-Wformat=2 \
	-Wshadow \
	-Werror \
	-Wpedantic \
	-std=c99 \
	-g \
	--coverage \
	-Isrc/c/heatshrink

FUZZER_CFLAGS = \
	-fprofile-instr-generate \
	-fcoverage-mapping \
	-Itests/files/c_source \
	-g -fsanitize=address,fuzzer \
	-fsanitize=signed-integer-overflow \
	-fno-sanitize-recover=all
FUZZER_EXECUTION_TIME ?= 30

test:
	env CFLAGS=--coverage python3 setup.py test
	$(MAKE) test-sdist
	$(MAKE) test-c
	find . -name "*.gcno" -exec gcov {} +
	$(MAKE) test-c-fuzzer FUZZER_EXECUTION_TIME=1

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
	$(CC) -DDETOOLS_CONFIG_FILE_IO=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-file-io.o
	$(CC) -DDETOOLS_CONFIG_COMPRESSION_NONE=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-none.o
	$(CC) -DDETOOLS_CONFIG_COMPRESSION_LZMA=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-lzma.o
	$(CC) -DDETOOLS_CONFIG_COMPRESSION_CRLE=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-crle.o
	$(CC) -DDETOOLS_CONFIG_COMPRESSION_HEATSHRINK=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-crle.o
	$(CC) $(CFLAGS) $(C_SOURCES) -llzma -o main
	./main
	$(MAKE) -C src/c library
	$(MAKE) -C src/c
	src/c/detools apply_patch tests/files/foo/old tests/files/foo/patch foo.new
	cmp foo.new tests/files/foo/new
	rm foo.new
	cp tests/files/foo/old foo.mem
	src/c/detools apply_patch_in_place foo.mem tests/files/foo/in-place-3000-500.patch
	cmp foo.mem tests/files/foo/in-place-3000-500.mem
	src/c/detools apply_patch \
	    tests/files/foo/old tests/files/foo/heatshrink.patch foo.new
	cmp foo.new tests/files/foo/new
	! src/c/detools
	! src/c/detools apply_patch
	! src/c/detools apply_patch tests/files/foo/old tests/files/foo/patch
	! src/c/detools apply_patch_in_place
	! src/c/detools apply_patch_in_place tests/files/foo/old
	$(MAKE) -C src/c/examples/in-place all
	$(MAKE) -C src/c/examples/in-place heatshrink
	$(MAKE) -C src/c/examples/in-place crle

test-c-fuzzer:
	clang $(FUZZER_CFLAGS) \
	    src/c/detools.c \
	    src/c/heatshrink/heatshrink_decoder.c \
	    tests/fuzzer.c \
	    -l lzma -o fuzzer
	rm -f fuzzer.profraw
	LLVM_PROFILE_FILE="fuzzer.profraw" \
	    ./fuzzer \
	    -max_total_time=$(FUZZER_EXECUTION_TIME) \
	    -print_final_stats
	llvm-profdata merge \
	    -sparse fuzzer.profraw \
	    -o fuzzer.profdata
	llvm-cov show ./fuzzer \
	    -instr-profile=fuzzer.profdata

release-to-pypi:
	python3 setup.py sdist
	twine upload dist/*
