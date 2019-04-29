|buildstatus|_
|appveyor|_
|coverage|_
|codecov|_

About
=====

Binary `delta encoding`_ in Python 3 and C.

Based on http://www.daemonology.net/bsdiff/, with the following
differences:

- BZ2, LZMA, `heatshrink`_ or CRLE compression.

- Linear patch file access pattern to allow streaming and less RAM
  usage.

- `SA-IS`_ instead of qsufsort.

- Variable length size fields.

- `Incremental apply patch`_ implemented in C, suitable for memory
  constrained embedded devices.

- `Normal`_ or `in-place`_ (resumable) updates.

- Optional experimental data format aware algorithm for potentially
  smaller patches. I don't recommend anyone to use this functionality
  as the gain is small in relation to memory usage and code
  complexity!

  There is a risk this functionality uses patent
  https://patents.google.com/patent/EP1988455B1/en. Anyway, this
  patent expires in August 2019 as I understand it.

  Supported data formats:

  - ARM Cortex-M4

  - AArch64

Project homepage: https://github.com/eerimoq/detools

Documentation: http://detools.readthedocs.org/en/latest

Installation
============

.. code-block:: python

    pip install detools

Statistics
==========

"LZMA ref." is the target binary compressed with ``lzma --best``.

The percentages are calculated as "patch size" / "to size". Lower is
better.

+---------------------+----------+-----------+---------+------------+---------+
| Update              |  To size | LZMA ref. | LZMA    | heatshrink | CRLE    |
+=====================+==========+===========+=========+============+=========+
| upy v1.9.4 -> v1.10 |   615388 |    59.8 % |  11.7 % |     15.7 % |  26.2 % |
+---------------------+----------+-----------+---------+------------+---------+
| python 3.5 -> 3.6   |  4568920 |    30.7 % |  31.8 % |         \- |      \- |
+---------------------+----------+-----------+---------+------------+---------+
| foo old -> new      |     2780 |    69.5 % |   4.5 % |      4.5 % |   6.8 % |
+---------------------+----------+-----------+---------+------------+---------+

Example usage
=============

Examples in C are found in `src/c`_.

Command line tool
-----------------

The create patch subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a patch ``foo.patch`` from ``tests/files/foo/old`` to
``tests/files/foo/new``.

.. code-block:: text

   $ detools create_patch tests/files/foo/old tests/files/foo/new foo.patch
   Successfully created patch 'foo.patch'!
   $ ls -l foo.patch
   -rw-rw-r-- 1 erik erik 127 Mar  1 19:18 foo.patch

Create the same patch as above, but without compression.

.. code-block:: text

   $ detools create_patch --compression none \
         tests/files/foo/old tests/files/foo/new foo-no-compression.patch
   Successfully created patch 'foo-no-compression.patch'!
   $ ls -l foo-no-compression.patch
   -rw-rw-r-- 1 erik erik 2792 Mar  1 19:18 foo-no-compression.patch

Create an in-place patch ``foo-in-place.patch``.

.. code-block:: text

   $ detools create_patch --type in-place --memory-size 3000 --segment-size 500 \
         tests/files/foo/old tests/files/foo/new foo-in-place.patch
   Successfully created patch 'foo-in-place.patch'!
   $ ls -l foo-in-place.patch
   -rw-rw-r-- 1 erik erik 672 Mar 16 08:49 foo-in-place.patch

Create a bsdiff patch ``foo-bsdiff.patch``, compatible with the
original bsdiff program.

.. code-block:: text

   $ detools create_patch --type bsdiff \
         tests/files/foo/old tests/files/foo/new foo-bsdiff.patch
   Successfully created patch 'foo-bsdiff.patch'!
   $ ls -l foo-bsdiff.patch
   -rw-rw-r-- 1 erik erik 261 Apr 22 18:20 foo-bsdiff.patch

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

The bsdiff apply patch subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Apply the patch ``foo-bsdiff.patch`` to ``tests/files/foo/old`` to
create ``foo.new``.

.. code-block:: text

   $ detools apply_patch_bsdiff tests/files/foo/old foo-bsdiff.patch foo.new
   $ ls -l foo.new
   -rw-rw-r-- 1 erik erik 2780 Mar  1 19:18 foo.new

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

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/eerimoq/detools?svg=true
.. _appveyor: https://ci.appveyor.com/project/eerimoq/detools/branch/master

.. |coverage| image:: https://coveralls.io/repos/github/eerimoq/detools/badge.svg?branch=master
.. _coverage: https://coveralls.io/github/eerimoq/detools

.. |codecov| image:: https://codecov.io/gh/eerimoq/detools/branch/master/graph/badge.svg
.. _codecov: https://codecov.io/gh/eerimoq/detools

.. _SA-IS: https://sites.google.com/site/yuta256/sais

.. _Incremental apply patch: https://github.com/eerimoq/detools/tree/master/src/c

.. _delta encoding: https://en.wikipedia.org/wiki/Delta_encoding

.. _heatshrink: https://github.com/atomicobject/heatshrink

.. _Normal: https://detools.readthedocs.io/en/latest/#id1

.. _in-place: https://detools.readthedocs.io/en/latest/#id2

.. _src/c: https://github.com/eerimoq/detools/tree/master/src/c
