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
	$(MAKE) -C src/c/tst SANITIZE=yes
	$(CC) $(CFLAGS) -DDETOOLS_CONFIG_FILE_IO=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-file-io.o
	$(CC) $(CFLAGS) -DDETOOLS_CONFIG_COMPRESSION_NONE=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-none.o
	$(CC) $(CFLAGS) -DDETOOLS_CONFIG_COMPRESSION_LZMA=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-lzma.o
	$(CC) $(CFLAGS) -DDETOOLS_CONFIG_COMPRESSION_CRLE=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-crle.o
	$(CC) $(CFLAGS) -DDETOOLS_CONFIG_COMPRESSION_HEATSHRINK=0 -Isrc/c/heatshrink \
	    -c src/c/detools.c -o detools.no-crle.o
	$(CC) $(CFLAGS) \
	    -DDETOOLS_CONFIG_COMPRESSION_NONE=0 \
	    -DDETOOLS_CONFIG_COMPRESSION_CRLE=0 \
	    -Isrc/c/heatshrink -c src/c/detools.c -o detools.no-crle.o
	$(CC) $(CFLAGS) \
	    -DDETOOLS_CONFIG_COMPRESSION_NONE=0 \
	    -DDETOOLS_CONFIG_COMPRESSION_LZMA=0 \
	    -DDETOOLS_CONFIG_COMPRESSION_CRLE=0 \
	    -Isrc/c/heatshrink -c src/c/detools.c -o detools.no-crle.o
	$(CC) $(CFLAGS) \
	    -DDETOOLS_CONFIG_COMPRESSION_NONE=0 \
	    -DDETOOLS_CONFIG_COMPRESSION_CRLE=0 \
	    -DDETOOLS_CONFIG_COMPRESSION_HEATSHRINK=0 \
	    -Isrc/c/heatshrink -c src/c/detools.c -o detools.no-crle.o
	$(MAKE) -C src/c library
	$(MAKE) -C src/c/examples/in-place all
	$(MAKE) -C src/c/examples/in-place heatshrink
	$(MAKE) -C src/c/examples/in-place crle
	$(MAKE) -C src/c/examples/dump_restore

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

benchmark:
	$(MAKE) -C src/c
	python3 setup.py test -s \
	    tests.test_detools.DetoolsTest.test_create_and_apply_patch_foo
	tests/benchmark.sh
