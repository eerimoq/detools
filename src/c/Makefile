ifeq ($(origin CC), default)
CC = gcc
endif

CFLAGS := \
	-Wall \
	-Wextra \
	-Wdouble-promotion \
	-Wfloat-equal \
	-Wformat=2 \
	-Wshadow \
	-Werror \
	-Wpedantic \
	-std=c99

SRC := \
	heatshrink/heatshrink_decoder.c \
	detools.c \
	main.c

all:
	$(CC) $(CFLAGS) $(SRC) -llzma -o detools
