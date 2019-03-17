About
=====

An implementation of detools in the C programming language.

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

Apply a normal patch.

.. code-block:: text

   $ ./detools apply_patch \
         ../../tests/files/foo.old ../../tests/files/foo.patch foo.new

Apply an in-place patch.

.. code-block:: text

   $ cp ../../tests/files/foo.old foo.mem
   $ ./detools apply_patch_in_place \
         foo.mem ../../tests/files/foo-in-place-3000-500.patch
