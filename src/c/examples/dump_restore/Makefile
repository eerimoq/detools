CFLAGS += -std=c99
CFLAGS += -I../../heatshrink

SRC += ../../detools.c
SRC += main.c
SRC += ../../heatshrink/heatshrink_decoder.c

all:
	gcc $(CFLAGS) $(SRC) -llzma -o dump-restore
	./dump-restore \
	    ../../../../tests/files/foo/old \
	    ../../../../tests/files/foo/heatshrink.patch \
	    foo.new \
	    10 25
	./dump-restore \
	    ../../../../tests/files/foo/old \
	    ../../../../tests/files/foo/heatshrink.patch \
	    foo.new \
	    90 20
	./dump-restore \
	    ../../../../tests/files/foo/old \
	    ../../../../tests/files/foo/heatshrink.patch \
	    foo.new \
	    25 0
	cmp foo.new ../../../../tests/files/foo/new
