Dump and restore
================

Command line tool to test the dump and restore feature.

.. code-block:: text

   $ ./dump-and-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         0 10
   Processing 1 byte(s) patch data starting at offset 0.
   State stored in 'state.bin'.
   $ ./dump-and-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         10 90
   Restoring state from 'state.bin'.
   Processing 90 byte(s) patch data starting at offset 10.
   State stored in 'state.bin'.
   $ ./dump-and-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         100 25
   Restoring state from 'state.bin'.
   Processing 25 byte(s) patch data starting at offset 100.
   Patch successfully applied.
   $
