Dump and restore
================

Command line tool to test the dump and restore feature.

.. code-block:: text

   $ ./dump-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         10 25
   Processing 10 byte(s) patch data starting at offset 0.
   State stored in 'state.bin'.
   $ ./dump-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         90 20
   Restoring state from 'state.bin'.
   Processing 90 byte(s) patch data starting at offset 10.
   State stored in 'state.bin'.
   $ ./dump-restore \
         ../../../../tests/files/foo/old \
         ../../../../tests/files/foo/heatshrink.patch \
         foo.new \
         25 0
   Restoring state from 'state.bin'.
   Processing 25 byte(s) patch data starting at offset 100.
   Patch successfully applied.
   $ cmp foo.new ../../../../tests/files/foo/new
   $
