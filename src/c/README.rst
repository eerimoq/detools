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

Build and run the command line utility.

.. code-block:: text

   $ make
   $ ./detools ../../tests/files/foo.old ../../tests/files/foo.patch foo.new
