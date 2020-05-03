CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar

# Install prefix.
PREFIX ?= /usr/local

INC += heatshrink
INC += ../../3pp/xz/src/liblzma/api
INC += ../../3pp/xz/src/liblzma/common
INC += ../../3pp/xz/src/liblzma/lz
INC += ../../3pp/xz/src/liblzma/rangecoder
INC += ../../3pp/xz/src/liblzma/lzma
INC += ../../3pp/xz/src/common

SRC += ../../3pp/xz/src/liblzma/lzma/lzma_decoder.c
SRC += ../../3pp/xz/src/liblzma/lz/lz_decoder.c
SRC += ../../3pp/xz/src/liblzma/common/common.c
SRC += ../../3pp/xz/src/liblzma/common/alone_decoder.c
SRC += heatshrink/heatshrink_decoder.c
SRC += detools.c
SRC += main.c

OPT ?= -O2
CFLAGS += -g
CFLAGS += -Wall
CFLAGS += -Wextra
CFLAGS += -Wdouble-promotion
CFLAGS += -Wfloat-equal
CFLAGS += -Wformat=2
CFLAGS += -Wshadow
CFLAGS += -Werror
CFLAGS += $(OPT)
CFLAGS += -DHAVE_STDBOOL_H
CFLAGS += -DHAVE_STDINT_H
CFLAGS += $(INC:%=-I%)
CFLAGS += $(CFLAGS_EXTRA)

all:
	$(CC) $(CFLAGS) $(SRC) -o detools

library:
	$(CC) $(CFLAGS) detools.c -c -o detools.o
	$(AR) cr libdetools.a detools.o

install:
	mkdir -p $(PREFIX)/include
	install -c -m 644 detools.h $(PREFIX)/include
	mkdir -p $(PREFIX)/lib
	install -c -m 644 libdetools.a $(PREFIX)/lib
