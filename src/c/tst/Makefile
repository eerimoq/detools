TESTS += test_detools.c
TESTS += test_dump_restore.c
TESTS += test_command_line.c
INC += ../heatshrink
SRC += ../detools.c
SRC += ../heatshrink/heatshrink_decoder.c
SRC += utils.c
LIBS += lzma

default:
	$(MAKE) -C .. OPT=-O0 CFLAGS_EXTRA="-coverage"
	$(MAKE) all

include test.mk
