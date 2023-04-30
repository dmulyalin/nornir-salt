Installation
############

From PyPI::

  pip install nornir_salt[prodmax]

From GitHub master branch::

  python3 -m pip install git+https://github.com/dmulyalin/nornir-salt

.. warning:: Python 3.6 support deprecated starting with Nornir-Salt version 0.12.0

Installation extras
===================

Nornir-Salt comes with these installation extras.

.. list-table:: Nornir-Salt extras packages
   :widths: 15 85
   :header-rows: 1

   * - Name
     - Description
   * - ``dev``
     - Installs libraries required for development e.g. pytest, black, pre-commit etc.
   * - ``prodminminion``
     - Production ready minimum set. Installs Netmiko, Ncclient and requests libraries
       to provide support for managing devices over SSH, NETCONF and RESTCONF. In addition,
       installs libraries to extended Nornir-Salt functionality such as Tabulate, Rich, TTP
       etc. All libraries have versions fixed to produce tested and working environment.
   * - ``prodmaxminion``
     - Production ready maximum set. Installs all ``prodmin`` libraries together with
       additional modules required to support complete Nornir-Salt feature set such as
       PyGNMI, PyATS, Scrapli, NAPALM etc. All libraries have versions fixed to produce
       tested and working environment.
   * - ``netmiko``
     - Installs netmiko, nornir-netmiko
   * - ``napalm``
     - Installs napalm, nornir-napalm
   * - ``scrapli``
     - Installs scrapli, scrapli-community
   * - ``pyats``
     - Installs genie, pyats
   * - ``netconf``
     - Installs ncclient, scrapli-netconf
   * - ``gnmi``
     - Installs pygnmi
   * - ``restconf``
     - Installs requests
   * - ``dataprocessor``
     - Installs cerberus, jmespath, ntc-templates, pyyaml, tabulate, ttp,
       ttp-templates, xmltodict, lxml

To install Nornir-Salt with its core dependencies (Nornir and Pydantic) only,
without any additional libraries::

    pip install Nornir-Salt

To install minimum production set::

    pip install Nornir-Salt[prodminminion]

To install maximum production set::

    pip install Nornir-Salt[prodmaxminion]

**Why different extras?** - to simplify dependency installation for different requirements. It might
make sense to start testing Nornir-Salt using ``prodmaxminion`` set, but later on narrow down to using Netmiko
and Ncclient only, in that case prodmin set would make sense as it helps to save some hard drive space
and improve installation speed.

Alternatively to using extras, individual libraries of desired version can be installed, provided
extras only use version that were tested together making it safer choice for less experienced users.
