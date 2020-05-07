About
=====

An implementation of detools in the C programming language.

Features:

- Incremental apply of `sequential`_ and `in-place`_ patches.

- bsdiff algorithm.

- LZMA, `heatshrink`_ or CRLE compression.

- Dump (and store) the apply patch state at any time. Restore it
  later, possibly after a system reboot or program crash. Only
  `heatshrink`_ and CRLE compressions are currently supported.

Goals:

- Easy to use.

- Low RAM usage.

- Small code size.

- Portable.

ToDo:

- Implement dump and restore for LZMA and/or other compression
  algorithms. Requires implementing dump and restore functions in
  these libraries, which may not be trivial.

Configuration
=============

Use the build time configuration to customize detools for your
application needs. See ``DETOOLS_CONFIG_*`` defines in `detools.h`_
for details.

Examples
========

There are examples in the `examples folder`_.

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

Code size
=========

Build an in-place apply patch application using gcc. The code size
will likely be smaller when cross compiling for an embedded device.

All functionality enabled.

.. code-block:: text

   $ make -s -C examples/in_place all
        text    data     bss     dec     hex filename
        9048     664       8    9720    25f8 in-place

Only heatshrink decompression.

.. code-block:: text

   $ make -s -C examples/in_place heatshrink
        text    data     bss     dec     hex filename
        6582     600       8    7190    1c16 in-place-heatshrink

Only CRLE decompression.

.. code-block:: text

   $ make -s -C examples/in_place crle
        text    data     bss     dec     hex filename
        5954     600       8    6562    19a2 in-place-crle

.. _heatshrink: https://github.com/atomicobject/heatshrink

.. _sequential: https://detools.readthedocs.io/en/latest/#id1

.. _in-place: https://detools.readthedocs.io/en/latest/#id3

.. _detools.h: https://github.com/eerimoq/detools/blob/master/src/c/detools.h

.. _examples folder: https://github.com/eerimoq/detools/tree/master/src/c/examples
