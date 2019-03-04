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
	-Wconversion \
	-Wpedantic \
	-std=c99

all:
	$(CC) $(CFLAGS) detools.c main.c -llzma -o detools
