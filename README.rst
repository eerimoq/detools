|buildstatus|_
|coverage|_

About
=====

Binary diff/patch utility in Python 3, using C extensions.

Based on http://www.daemonology.net/bsdiff/, with the following
changes:

- LZMA compression instead of BZ2 for smaller patches.

- Linear patch file access pattern to allow streaming.

- `SA-IS`_ instead of qsufsort for speed and reliability.

Project homepage: https://github.com/eerimoq/bsdiff

Documentation: http://bsdiff.readthedocs.org/en/latest

Installation
============

.. code-block:: python

    pip install bsdiff

Statistics
==========

+-----------+-----------+-----------+-----------+------------+---------------+
| From name | To name   | From size |   To size | Patch size | To compressed |
+===========+===========+===========+===========+============+===============+
| python3.5 | python3.6 |   4464400 |   4568920 |    1493488 |       1402663 |
+-----------+-----------+-----------+-----------+------------+---------------+
|   foo.old |   foo.new |      2780 |      2780 |        192 |          1934 |
+-----------+-----------+-----------+-----------+------------+---------------+

Contributing
============

#. Fork the repository.

#. Implement the new feature or bug fix.

#. Implement test case(s) to ensure that future changes do not break
   legacy.

#. Run the tests.

   .. code-block:: text

      make test

#. Create a pull request.

.. |buildstatus| image:: https://travis-ci.org/eerimoq/bsdiff.svg?branch=master
.. _buildstatus: https://travis-ci.org/eerimoq/bsdiff

.. |coverage| image:: https://coveralls.io/repos/github/eerimoq/bsdiff/badge.svg?branch=master
.. _coverage: https://coveralls.io/github/eerimoq/bsdiff

.. _SA-IS: https://sites.google.com/site/yuta256/sais
