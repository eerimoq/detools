.. cantools documentation master file, created by
   sphinx-quickstart on Sat Apr 25 11:54:09 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 2

Binary delta encoding utility
=============================

.. include:: ../README.rst

Patch types
===========

Normal
------

ToDo

.. code-block:: text

   $ detools create_patch tests/files/foo.old tests/files/foo.new foo.patch

In-place
--------

The in-place patch type is designed to update an application in
place. It is useful when flash operations are faster than the external
interface transfer speed.

Use ``--type in-place`` to create an in-plance patch. The to options
``--memory-size`` and ``--segment-size`` are required, while
``--minimum-shift-size`` is optional.

.. code-block:: text

   $ detools create_patch --type in-place --memory-size 131072 --segment-size 32768 \
         tests/files/foo.old tests/files/foo.new foo.patch

Here is an example of an in-place application update from version 1 to
version 2. The two applications are represented by the character
sequences below for clarity.

.. code-block:: text

   Version 1: 0123456789abcdefghijklmnopqr
   Version 2: ABCDEFGHIJKLMNOPQRSTUVWXYZstuvwxyz

#. Before the update application version 1 is found in memory segments
   0 to 3.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |0123456789abcdefghijklmnopqr|                  |
      +-------+-------+-------+-------+-------+-------+

#. The update starts by moving the application two segments to the
   right to make room for the new version.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |               |0123456789abcdefghijklmnopqr|  |
      +-------+-------+-------+-------+-------+-------+

#. The first part of the patch is received and combined with
   application version 1. The combined data is written to segment 0.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFG|       |0123456789abcdefghijklmnopqr|  |
      +-------+-------+-------+-------+-------+-------+

#. Same as the previous step, but the combined data is written to
   segment 1.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNO|0123456789abcdefghijklmnopqr|  |
      +-------+-------+-------+-------+-------+-------+

#. Segment 2 is erased to make room for the next part of the patch.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNO|       |89abcdefghijklmnopqr|  |
      +-------+-------+-------+-------+-------+-------+

#. Combined data written to segment 2.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVW|89abcdefghijklmnopqr|  |
      +-------+-------+-------+-------+-------+-------+

#. Segment 3 is erased.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVW|       |ghijklmnopqr|  |
      +-------+-------+-------+-------+-------+-------+

#. Combined data written to segment 3.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVWXYZstuvw|ghijklmnopqr|  |
      +-------+-------+-------+-------+-------+-------+

#. Segment 4 is erased.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVWXYZstuvw|       |opqr|  |
      +-------+-------+-------+-------+-------+-------+

#. Combined data written to segment 4.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVWXYZstuvwxyz|    |opqr|  |
      +-------+-------+-------+-------+-------+-------+

#. Optionally, segment 5 is erased.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVWXYZstuvwxyz|            |
      +-------+-------+-------+-------+-------+-------+

#. Update to application version 2 complete!

An interrupted in-place update can be resumed by introducing a step
state, persistentely stored in a separate memory region. Also store
the patch header persistentely. Reject any other patch until the
currently active patch has been successfully applied.

   .. code-block:: text

          0       1       2       3       4       5
      +-------+-------+-------+-------+-------+-------+
      |0123456789abcdefghijklmnopqr|                  | Step: 0
      +-------+-------+-------+-------+-------+-------+
      |0123456789abcdefghijklmnopqr|          |opqr|  | Step: 1
      +-------+-------+-------+-------+-------+-------+
      |0123456789abcdefghijklmnopqr|  |ghijklmnopqr|  | Step: 2
      +-------+-------+-------+-------+-------+-------+
      |0123456789abcdefghijklm|89abcdefghijklmnopqr|  | Step: 3
      +-------+-------+-------+-------+-------+-------+
      |0123456789abcde|0123456789abcdefghijklmnopqr|  | Step: 4
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFG789abcde|0123456789abcdefghijklmnopqr|  | Step: 5
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNO|0123456789abcdefghijklmnopqr|  | Step: 6
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVW|89abcdefghijklmnopqr|  | Step: 7
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVWXYZstuvw|ghijklmnopqr|  | Step: 8
      +-------+-------+-------+-------+-------+-------+
      |ABCDEFGHIJKLMNOPQRSTUVWXYZstuvwxyz|    |opqr|  | Step: 0
      +-------+-------+-------+-------+-------+-------+

Functions and classes
=====================

.. autofunction:: detools.create_patch

.. autofunction:: detools.apply_patch

.. autofunction:: detools.apply_patch_in_place

.. autofunction:: detools.patch_info

.. autofunction:: detools.create_patch_filenames

.. autofunction:: detools.apply_patch_filenames

.. autofunction:: detools.apply_patch_in_place_filenames

.. autofunction:: detools.patch_info_filename
