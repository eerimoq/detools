CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar

# Install prefix.
PREFIX ?= /usr/local

OPT ?= -O2
CFLAGS += -g
CFLAGS += -Wall
CFLAGS += -Wextra
CFLAGS += -Wdouble-promotion
CFLAGS += -Wfloat-equal
CFLAGS += -Wformat=2
CFLAGS += -Wshadow
CFLAGS += -Werror
CFLAGS += -std=c99
CFLAGS += $(OPT)
CFLAGS += -Iheatshrink
CFLAGS += $(CFLAGS_EXTRA)

SRC += heatshrink/heatshrink_decoder.c
SRC += detools.c
SRC += main.c

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
