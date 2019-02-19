|buildstatus|_
|coverage|_

About
=====

Binary diff/patch utility.

Based on http://www.daemonology.net/bsdiff/.

Project homepage: https://github.com/eerimoq/bsdiff

Documentation: http://bsdiff.readthedocs.org/en/latest

Installation
============

.. code-block:: python

    pip install bsdiff

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

.. |buildstatus| image:: https://travis-ci.org/eerimoq/bsdiff.svg?branch=master
.. _buildstatus: https://travis-ci.org/eerimoq/bsdiff

.. |coverage| image:: https://coveralls.io/repos/github/eerimoq/bsdiff/badge.svg?branch=master
.. _coverage: https://coveralls.io/github/eerimoq/bsdiff
