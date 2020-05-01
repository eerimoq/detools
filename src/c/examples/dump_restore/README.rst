Dump and restore
================

Command line tool to test the dump and restore feature.

.. code-block:: text

   $ ./dump-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         10 25
   Restoring state from 'state.bin'.
   Processing 10 byte(s) patch data starting at offset 0.
   Storing state in 'state.bin'.
   Processing 25 byte(s) patch data after dump starting at offset 10.
   $ ./dump-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         90 20
   Restoring state from 'state.bin'.
   Processing 90 byte(s) patch data starting at offset 10.
   Storing state in 'state.bin'.
   Processing 20 byte(s) patch data after dump starting at offset 100.
   $ ./dump-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         25 0
   Restoring state from 'state.bin'.
   Processing 25 byte(s) patch data starting at offset 100.
   Removing state 'state.bin'.
   Patch successfully applied.
   $ cmp foo.new ../../../../tests/files/foo/new
   $
