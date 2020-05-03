Dump and restore patcher state
==============================

Command line tool to test the dump and restore feature.

Build and run
-------------

.. code-block:: text

   $ make
   gcc -Wall -Wextra -Werror -DHAVE_STDBOOL_H -DHAVE_STDINT_H -I../../heatshrink -I../../../../3pp/xz/src/liblzma/api -I../../../../3pp/xz/src/liblzma/common -I../../../../3pp/xz/src/liblzma/lz -I../../../../3pp/xz/src/liblzma/rangecoder -I../../../../3pp/xz/src/liblzma/lzma -I../../../../3pp/xz/src/common ../../detools.c main.c ../../heatshrink/heatshrink_decoder.c ../../../../3pp/xz/src/liblzma/lzma/lzma_decoder.c ../../../../3pp/xz/src/liblzma/lz/lz_decoder.c ../../../../3pp/xz/src/liblzma/common/common.c ../../../../3pp/xz/src/liblzma/common/alone_decoder.c -o dump-restore
   ./dump-restore \
       ../../../../tests/files/foo/old \
       ../../../../tests/files/foo/heatshrink.patch \
       foo.new \
       10 25
   No state to restore.
   Processing 10 byte(s) patch data starting at offset 0.
   Storing state in 'state.bin'.
   Processing 25 byte(s) patch data starting at offset 10.
   ./dump-restore \
       ../../../../tests/files/foo/old \
       ../../../../tests/files/foo/heatshrink.patch \
       foo.new \
       90 20
   Restoring state from 'state.bin'.
   Processing 90 byte(s) patch data starting at offset 10.
   Storing state in 'state.bin'.
   Processing 20 byte(s) patch data starting at offset 100.
   ./dump-restore \
       ../../../../tests/files/foo/old \
       ../../../../tests/files/foo/heatshrink.patch \
       foo.new \
       25 0
   Restoring state from 'state.bin'.
   Processing 25 byte(s) patch data starting at offset 100.
   Removing state 'state.bin'.
   Patch successfully applied. To-file is 2780 bytes.
   cmp foo.new ../../../../tests/files/foo/new
