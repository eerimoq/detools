TESTS += test_dump_restore.c
TESTS += test_command_line.c
INC += ../heatshrink
SRC += ../detools.c
SRC += ../heatshrink/heatshrink_decoder.c
SRC += utils.c
CFLAGS += -DDETOOLS_CONFIG_COMPRESSION_LZMA=0

default:
	$(MAKE) -C .. OPT=-O0 CFLAGS_EXTRA="-coverage"
	$(MAKE) all

include test.mk
