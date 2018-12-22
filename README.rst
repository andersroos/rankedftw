.. image:: https://travis-ci.org/andersroos/rankedftw.svg?branch=master
    :target: https://travis-ci.org/andersroos/rankedftw

Ranked For Teh Win
==================

This is the source code for the website https://www.rankedftw.com, a
StarCraft II site.
       
Building
========

Major Dependencies
------------------

* Postgresql and libpq
* Python 3
* Python libs (requirements.txt)
* Boost
* GCC
* JsonCpp
* GNU Make
* Nodejs
* Javascript libs (package.json)

For a complete and up to date list of dependecies and example on
install steps on Ubuntu 14.04 see `<.travis.yml>`_.

Basic Build Steps
-----------------

Install Postgresql, libpq, python3, boost, gcc, libjsoncpp and make,
see also `<.travis.yml>`_.

Then install python and javascript libs:

.. code-block:: bash

   make init
                
Then compile:

.. code-block:: bash

   make build -j

Running Tests
=============

Create postgres user that is allowed to create db (needed for tests):

.. code-block:: bash

   sudo -u postgres createuser $USER
   sudo -u postgres psql -c "alter user $USER with createdb;"

Then to run tests:

.. code-block:: none

   make test
                
Running Development Site
========================

First build the system, see above.

Then create databsae:

.. code-block:: bash

   sudo -u postgres createdb rankedftw
   make migrate-db

To run the development http server on ``localhost:8000``, the ladder
server (``./lib/server``) and webpack watch:

.. code-block:: bash

   make run

A few things will work (not crash) without data but most things wont.

Gettting Data
=============

If you get this far and want a sample db from the real world please contact me here
or at rankedftw.com@gmail.com.
