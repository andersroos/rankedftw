.. image:: https://travis-ci.org/andersroos/rankedftw.svg?branch=master
    :target: https://travis-ci.org/andersroos/rankedftw

Ranked For Teh Win
==================

This is the source code for the website http://www.rankedftw.com, a
StarCraft II site.
       
Building
========

Major Dependencies
------------------

* Postgresql and libpq
* Python 3
* Python Packages (requirements.txt)
* Boost
* GCC
* JsonCpp
* GNU Make
* Lessc

For a complete and up to date list of dependecies and example on
install steps on Ubuntu 14.04 see `<.travis.yml>`_.

Basic Build Steps
-----------------

Install Postgresql, libpq, python3, boost, gcc, libjsoncpp, make and
lessc, see also `<.travis.yml>`_.

Then install python libs:

.. code-block:: bash

   make init
                
Then compile:

.. code-block:: bash

   make build

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

Then to run the development http server on ``localhost:8000``:

.. code-block:: bash

   make run

You may also start the server serving the current ladder (not
required):

.. code-block:: bash

   ./lib/server

A few things will work (not crash) without data but most things wont.

Gettting Data
=============

**TBD** Plase contact me if you get this far and want some real world
 data.

