TESTS += test_detools.c
TESTS += test_dump_restore.c
TESTS += test_command_line.c

INC += ../heatshrink
INC += ../../../3pp/xz/src/liblzma/api
INC += ../../../3pp/xz/src/liblzma/common
INC += ../../../3pp/xz/src/liblzma/lz
INC += ../../../3pp/xz/src/liblzma/rangecoder
INC += ../../../3pp/xz/src/liblzma/lzma
INC += ../../../3pp/xz/src/common

SRC += ../detools.c
SRC += ../heatshrink/heatshrink_decoder.c
SRC += utils.c
SRC += ../../../3pp/xz/src/liblzma/lzma/lzma_decoder.c
SRC += ../../../3pp/xz/src/liblzma/lz/lz_decoder.c
SRC += ../../../3pp/xz/src/liblzma/common/common.c
SRC += ../../../3pp/xz/src/liblzma/common/alone_decoder.c

CFLAGS += -DHAVE_STDBOOL_H
CFLAGS += -DHAVE_STDINT_H

default:
	$(MAKE) -C .. OPT=-O0 CFLAGS_EXTRA="-coverage"
	$(MAKE) all

include test.mk
