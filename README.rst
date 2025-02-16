.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/doc-agent.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/doc-agent
    .. image:: https://readthedocs.org/projects/doc-agent/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://doc-agent.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/coveralls/github/<USER>/doc-agent/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/doc-agent
    .. image:: https://img.shields.io/pypi/v/doc-agent.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/doc-agent/
    .. image:: https://img.shields.io/conda/vn/conda-forge/doc-agent.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/doc-agent
    .. image:: https://pepy.tech/badge/doc-agent/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/doc-agent
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/doc-agent

.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

=========
doc-agent
=========

A simple command line interface to run a workflow defined in a YAML file.


Installation
------------

You can install **doc-agent** via pip:

To install doc-agent, run this command in your terminal 
.. code-block:: bash

    $ pip install doc-agent

If you don't have `pip` installed, this `Python installation guide <https://packaging.python.org/tutorials/installing-packages/>`_ can guide you through the process.

Usage
-----

After installing doc-agent, you can use it from the command line. Here are some examples:

.. code-block:: bash

    $ doc-agent --help

Quickstart
----------

To use doc-agent, you need to create a YAML file with the workflow you want to run. Here is an example:

1. Generate a example workflow file:

.. code-block:: bash

    $ doc-agent generate

2. Test the workflow:

.. code-block:: bash

    $ doc-agent test workflow.yml

3. Run the workflow:

.. code-block:: bash

    $ doc-agent run workflow.yml
