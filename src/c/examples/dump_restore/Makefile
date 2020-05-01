CFLAGS += -std=c99
CFLAGS += -I../../heatshrink

SRC += ../../detools.c
SRC += main.c
SRC += ../../heatshrink/heatshrink_decoder.c

all:
	gcc $(CFLAGS) $(SRC) -llzma -o dump-and-restore
