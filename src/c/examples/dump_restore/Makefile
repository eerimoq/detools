INC += ../../heatshrink
INC += ../../../../3pp/xz/src/liblzma/api
INC += ../../../../3pp/xz/src/liblzma/common
INC += ../../../../3pp/xz/src/liblzma/lz
INC += ../../../../3pp/xz/src/liblzma/rangecoder
INC += ../../../../3pp/xz/src/liblzma/lzma
INC += ../../../../3pp/xz/src/common

SRC += ../../detools.c
SRC += main.c
SRC += ../../heatshrink/heatshrink_decoder.c
SRC += ../../../../3pp/xz/src/liblzma/lzma/lzma_decoder.c
SRC += ../../../../3pp/xz/src/liblzma/lz/lz_decoder.c
SRC += ../../../../3pp/xz/src/liblzma/common/common.c
SRC += ../../../../3pp/xz/src/liblzma/common/alone_decoder.c

CFLAGS += -Wall
CFLAGS += -Wextra
CFLAGS += -Werror
CFLAGS += -DHAVE_STDBOOL_H
CFLAGS += -DHAVE_STDINT_H
CFLAGS += $(INC:%=-I%)

all:
	gcc $(CFLAGS) $(SRC) -o dump-restore
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
