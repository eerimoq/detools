About
=====

An implementation of detools in the C programming language.

Features:

- Incremental apply of `sequential`_ and `in-place`_ patches.

- bsdiff algorithm.

- LZMA, `heatshrink`_ or CRLE compression.

- Dump (and store) the apply patch state at any time. Restore it
  later, possibly after a system reboot or program crash.

  Only `heatshrink`_ and CRLE compressions are currently supported.

Goals:

- Low RAM usage.

- Small code size.

Configuration
=============

Use the build time configuration to customize detools for your
application needs. See ``DETOOLS_CONFIG_*`` defines in ``detools.h``
for details.

Command line utility
====================

Build the command line utility.

.. code-block:: text

   $ make

Apply a sequential patch.

.. code-block:: text

   $ ./detools apply_patch \
         ../../tests/files/foo/old ../../tests/files/foo/patch foo.new

Apply an in-place patch.

.. code-block:: text

   $ cp ../../tests/files/foo/old foo.mem
   $ ./detools apply_patch_in_place \
         foo.mem ../../tests/files/foo-in-place-3000-500.patch

Incremental in-place patching
=============================

Below is an example of how to incrementally apply an in-place patch.

.. code-block:: c

   /* Helper functions. */
   static int flash_read(void *arg_p, void *dst_p, uintptr_t src, size_t size);
   static int flash_write(void *arg_p, uintptr_t dst, void *src_p, size_t size);
   static int flash_erase(void *arg_p, uintptr_t addr, size_t size);
   static int step_set(void *arg_p, int step);
   static int step_get(void *arg_p, int *step_p);
   static int serial_read(uint8_t *buf_p, size_t size);
   static int verify_written_data(int to_size, uint32_t to_crc);

   /* The update function. Returns zero(0) on success. */
   static int update(size_t patch_size, uint32_t to_crc)
   {
       struct detools_apply_patch_in_place_t apply_patch;
       uint8_t buf[256];
       size_t left;
       int res;

       /* Initialize the in-place apply patch object. */
       res = detools_apply_patch_in_place_init(&apply_patch,
                                               flash_read,
                                               flash_write,
                                               flash_erase,
                                               step_set,
                                               step_get,
                                               patch_size,
                                               NULL);

       if (res != 0) {
           return (res);
       }

       left = patch_size;

       /* Incrementally process patch data until the whole patch has been
          applied or an error occurrs. */
       while ((left > 0) && (res == 0)) {
           res = serial_read(&buf[0], sizeof(buf));

           if (res > 0) {
               left -= res;
               res = detools_apply_patch_in_place_process(&apply_patch,
                                                          &buf[0],
                                                          res);
           }
       }

       /* Finalize patching and verify written data. */
       if (res == 0) {
           res = detools_apply_patch_in_place_finalize(&apply_patch);

           if (res >= 0) {
               res = verify_written_data(res, to_crc);
           }
       } else {
           (void)detools_apply_patch_in_place_finalize(&apply_patch);
       }

       return (res);
   }

Code size
=========

Build an in-place apply patch application using gcc. The code size
will likely be smaller when cross compiling for an embedded device.

All functionality enabled.

.. code-block:: text

   $ make -s -C examples/in-place all
        text    data     bss     dec     hex filename
        8973     608       8    9589    2575 in-place

Only heatshrink decompression.

.. code-block:: text

   $ make -s -C examples/in-place heatshrink
        text    data     bss     dec     hex filename
        6339     544       8    6891    1aeb in-place-heatshrink

Only CRLE decompression.

.. code-block:: text

   $ make -s -C examples/in-place crle
        text    data     bss     dec     hex filename
        5651     544       8    6203    183b in-place-crle

.. _heatshrink: https://github.com/atomicobject/heatshrink

.. _sequential: https://detools.readthedocs.io/en/latest/#id1

.. _in-place: https://detools.readthedocs.io/en/latest/#id3
