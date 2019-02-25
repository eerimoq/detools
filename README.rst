|buildstatus|_
|coverage|_
|codecov|_

About
=====

Binary delta encoding in Python 3.

Based on http://www.daemonology.net/bsdiff/, with the following
differences:

- LZMA or CRLE compression instead of BZ2.

- Linear patch file access pattern to allow streaming.

- `SA-IS`_ instead of qsufsort.

- Variable length size fields.

Planned functionality:

- Incremental apply patch implemented in C, suitable for memory
  constrained embedded devices.

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
+=====================+==========+=========+========+============+========+=====================+
|                                |    Size |  Ratio | Patch size |  Ratio | Patch size |  Ratio |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| upy v1.9.4 -> v1.10 |   615388 |  367500 | 59.8 % |      71868 | 11.6 % |     161419 | 26.2 % |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| python 3.5 -> 3.6   |  4568920 | 1402663 | 30.7 % |    1451788 | 31.8 % |         \- |     \- |
+---------------------+----------+---------+--------+------------+--------+------------+--------+
| foo old -> new      |     2780 |    1934 | 69.5 % |        188 |  6.8 % |        206 |  7.4 % |
+---------------------+----------+---------+--------+------------+--------+------------+--------+

Example usage
=============

Command line tool
-----------------

The create patch subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a patch ``foo.patch`` from ``tests/files/foo.old`` to
``tests/files/foo.new``.

.. code-block:: text

   $ detools create_patch tests/files/foo.old tests/files/foo.new foo.patch
   $ ls -l foo.patch
   -rw-rw-r-- 1 erik erik 188 feb 21 07:28 foo.patch

Create the same patch as above, but without compression.

.. code-block:: text

   $ detools create_patch --compression none tests/files/foo.old tests/files/foo.new foo-no-compression.patch
   $ ls -l foo-no-compression.patch
   -rw-rw-r-- 1 erik erik 2808 Feb 23 10:19 foo-no-compression.patch

The apply patch subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^^

Apply the patch ``foo.patch`` to ``tests/files/foo.old`` to create
``foo.new``.

.. code-block:: text

   $ detools apply_patch tests/files/foo.old foo.patch foo.new
   $ ls -l foo.new
   -rw-rw-r-- 1 erik erik 2780 feb 21 07:30 foo.new

The patch info subcommand
^^^^^^^^^^^^^^^^^^^^^^^^^

Print information about the patch ``foo.patch``.

.. code-block:: text

   $ detools patch_info foo.patch
   Type:               normal
   Patch size:         188 bytes
   To size:            2.78 KB
   Patch/to ratio:     6.8 % (lower is better)
   Diff/extra ratio:   9828.6 % (higher is better)
   Size/data ratio:    0.3 % (lower is better)
   Compression:        lzma

   Number of diffs:    2
   Total diff size:    2.75 KB
   Average diff size:  1.38 KB
   Median diff size:   1.38 KB

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
