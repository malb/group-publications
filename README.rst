Group Publications
==================

Simple Python (3.7+) scripts to:

1. Fetch the publications of a list of people from DBLB (with some filtering rules)
2. Add them to a local database
3. Render lists of publications (with some filtering rules)

.. image:: https://github.com/malb/group-publications/workflows/Run/badge.svg
  :target: https://github.com/malb/group-publications/actions?query=workflow%3ARun

Getting started
---------------

.. code-block:: bash

    $ pip install -r requirements.txt
    $ cp example_config.py config.py #
    <edit config.py>
    $ ./cli.py sync
