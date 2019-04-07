|buildstatus|_
|coverage|_
|codecov|_

About
=====

Binary `delta encoding`_ in Python 3 and C.

Based on http://www.daemonology.net/bsdiff/, with the following
differences:

- BZ2, LZMA or CRLE compression.

- Linear patch file access pattern to allow streaming and less RAM
  usage.

- `SA-IS`_ instead of qsufsort.

- Variable length size fields.

- `Incremental apply patch`_ implemented in C, suitable for memory
  constrained embedded devices.

- Optional data format aware algorithm for potentially smaller
  patches. There is a risk this functionality uses patent
  https://patents.google.com/patent/EP1988455B1/en. Anyway, this
  patent expires in August 2019 as I understand it.

  Supported data formats:

  - ARM Cortex-M4

  - AArch64

Planned functionality:

- in-place patch type support in C.

Ideas:

- Make the in-place patch type resumable.

Project homepage: https://github.com/eerimoq/detools

Documentation: http://detools.readthedocs.org/en/latest

Installation
============

.. code-block:: python

    pip install detools

Statistics
==========

"LZMA reference" is the target binary compressed with ``lzma --best``.

All sizes are in bytes.

+---------------------+----------+------------------+---------------------+---------------------+
| Update              |  To size | LZMA reference   | LZMA compression    | CRLE compression    |
+=====================+==========+=========+========+============+========+============+========+
|                                |    Size |  Ratio | Patch size |  Ratio | Patch size |  Ratio |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| upy v1.9.4 -> v1.10 |   615388 |  367500 | 59.8 % |      71802 | 11.7 % |     161403 | 26.2 % |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| python 3.5 -> 3.6   |  4568920 | 1402663 | 30.7 % |    1451510 | 31.8 % |         \- |     \- |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| foo old -> new      |     2780 |    1934 | 69.5 % |        126 |  4.5 % |        189 |  6.8 % |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| upy 1f5d945af (1)   |   319988 |  183976 | 57.5 % |       8208 |  2.6 % |         \- |     \- |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| upy 1f5d945af (2)   |   319988 |  183976 | 57.5 % |       5039 |  1.6 % |         \- |     \- |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| upy 1f5d945af (3)   |   319988 |  183976 | 57.5 % |       2994 |  0.9 % |         \- |     \- |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| python3 (4)         |  3498472 |  912539 | 26.1 % |      88485 |  2.5 % |         \- |     \- |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| python3 (5)         |  3498472 |  912539 | 26.1 % |      47203 |  1.3 % |         \- |     \- |
+---------------------+----------+---------+--------+------------+--------+------------+--------+

Two builds of MicroPython for PYBv1.1. The from-file is built from
commit 1f5d945af, while the to-file is built from the same commit, but
with line 209 in ``vm.c`` deleted.

(1): Default settings.

.. code-block:: text

   detools create_patch \
       tests/files/pybv11/1f5d945af/firmware1.bin \
       tests/files/pybv11/1f5d945af-dirty/firmware1.bin \
       tests/files/pybv11/1f5d945af--1f5d945af-dirty.patch

(2): ARM Cortex-M4 aware algorithm.

.. code-block:: text

   detools create_patch \
       --data-format arm-cortex-m4 \
       tests/files/pybv11/1f5d945af/firmware1.bin \
       tests/files/pybv11/1f5d945af-dirty/firmware1.bin \
       tests/files/pybv11/1f5d945af--1f5d945af-dirty-arm-cortex-m4.patch

(3): ARM Cortex-M4 aware algorithm with data and code sections.

.. code-block:: text

   detools create_patch \
       --data-format arm-cortex-m4 \
       --from-data-offset-begin 0x36f7c \
       --from-data-offset-end 0x4e1f0 \
       --from-data-begin 0x8056f7c \
       --from-data-end 0x806e1f0 \
       --from-code-begin 0x8020000 \
       --from-code-end 0x8056f7c \
       --to-data-offset-begin 0x36f54 \
       --to-data-offset-end 0x4e1d4 \
       --to-data-begin 0x8056f54 \
       --to-data-end 0x806e1d4 \
       --to-code-begin 0x8020000 \
       --to-code-end 0x8056f54 \
       tests/files/pybv11/1f5d945af/firmware1.bin \
       tests/files/pybv11/1f5d945af-dirty/firmware1.bin \
       tests/files/pybv11/1f5d945af--1f5d945af-dirty-arm-cortex-m4-data-sections.patch

Python 3 built for a 64-bit ARM processor.

(4): Default settings.

.. code-block:: text

   detools create_patch \
       tests/files/python3/aarch64/3.7.2-3/libpython3.7m.so.1.0 \
       tests/files/python3/aarch64/3.7.3-1/libpython3.7m.so.1.0 \
       tests/files/python3/aarch64/3.7.2-3--3.7.3-1.patch

(5): AArch64 aware algorithm.

.. code-block:: text

   detools create_patch \
       --data-format aarch64 \
       tests/files/python3/aarch64/3.7.2-3/libpython3.7m.so.1.0 \
       tests/files/python3/aarch64/3.7.3-1/libpython3.7m.so.1.0 \
       tests/files/python3/aarch64/3.7.2-3--3.7.3-1-aarch64.patch

Example usage
=============

Command line tool
-----------------

The create patch subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a patch ``foo.patch`` from ``tests/files/foo/old`` to
``tests/files/foo/new``.

.. code-block:: text

   $ detools create_patch tests/files/foo/old tests/files/foo/new foo.patch
   $ ls -l foo.patch
   -rw-rw-r-- 1 erik erik 127 Mar  1 19:18 foo.patch

Create the same patch as above, but without compression.

.. code-block:: text

   $ detools create_patch --compression none \
         tests/files/foo/old tests/files/foo/new foo-no-compression.patch
   $ ls -l foo-no-compression.patch
   -rw-rw-r-- 1 erik erik 2792 Mar  1 19:18 foo-no-compression.patch

Create an in-place patch ``foo-in-place.patch``.

.. code-block:: text

   $ detools create_patch --type in-place --memory-size 3000 --segment-size 500 \
         tests/files/foo/old tests/files/foo/new foo-in-place.patch
   $ ls -l foo-in-place.patch
   -rw-rw-r-- 1 erik erik 672 Mar 16 08:49 foo-in-place.patch

The apply patch subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^^

Apply the patch ``foo.patch`` to ``tests/files/foo/old`` to create
``foo.new``.

.. code-block:: text

   $ detools apply_patch tests/files/foo/old foo.patch foo.new
   $ ls -l foo.new
   -rw-rw-r-- 1 erik erik 2780 Mar  1 19:18 foo.new

The in-place apply patch subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Apply the in-place patch ``foo-in-place.patch`` to ``foo.mem``.

.. code-block:: text

   $ cp tests/files/foo/old foo.mem
   $ detools apply_patch_in_place foo.mem foo-in-place.patch
   $ ls -l foo.mem
   -rwxrwxr-x 1 erik erik 2780 Mar 16 08:51 foo.mem

The patch info subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^

Print information about the patch ``foo.patch``.

.. code-block:: text

   $ detools patch_info foo.patch
   Type:               normal
   Patch size:         127 bytes
   To size:            2.71 KiB
   Patch/to ratio:     4.6 % (lower is better)
   Diff/extra ratio:   9828.6 % (higher is better)
   Size/data ratio:    0.3 % (lower is better)
   Compression:        lzma

   Number of diffs:    2
   Total diff size:    2.69 KiB
   Average diff size:  1.34 KiB
   Median diff size:   1.34 KiB

   Number of extras:   2
   Total extra size:   28 bytes
   Average extra size: 14 bytes
   Median extra size:  14 bytes

Contributing
============

#. Fork the repository.

#. Install prerequisites.

   .. code-block:: text

      pip install -r requirements.txt

#. Implement the new feature or bug fix.

#. Implement test case(s) to ensure that future changes do not break
   legacy.

#. Run the tests.

   .. code-block:: text

      make test

#. Create a pull request.

.. |buildstatus| image:: https://travis-ci.org/eerimoq/detools.svg?branch=master
.. _buildstatus: https://travis-ci.org/eerimoq/detools

.. |coverage| image:: https://coveralls.io/repos/github/eerimoq/detools/badge.svg?branch=master
.. _coverage: https://coveralls.io/github/eerimoq/detools

.. |codecov| image:: https://codecov.io/gh/eerimoq/detools/branch/master/graph/badge.svg
.. _codecov: https://codecov.io/gh/eerimoq/detools

.. _SA-IS: https://sites.google.com/site/yuta256/sais

.. _Incremental apply patch: https://github.com/eerimoq/detools/tree/master/src/c

.. _delta encoding: https://en.wikipedia.org/wiki/Delta_encoding
