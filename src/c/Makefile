CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar

# Install prefix.
PREFIX ?= /usr/local

CFLAGS := \
	-Wall \
	-Wextra \
	-Wdouble-promotion \
	-Wfloat-equal \
	-Wformat=2 \
	-Wshadow \
	-Werror \
	-std=c99 \
	-O2 \
	-Iheatshrink
CFLAGS += $(CFLAGS_EXTRA)

SRC := \
	heatshrink/heatshrink_decoder.c \
	detools.c \
	main.c

all:
	$(CC) $(CFLAGS) $(SRC) -llzma -o detools

library:
	$(CC) $(CFLAGS) detools.c -c -o detools.o
	$(AR) cr libdetools.a detools.o

install:
	mkdir -p $(PREFIX)/include
	install -c -m 644 detools.h $(PREFIX)/include
	mkdir -p $(PREFIX)/lib
	install -c -m 644 libdetools.a $(PREFIX)/lib
