Installation
############

From PyPi::

  pip install nornir_salt[prodmin]

From GitHub master branch::

  python3 -m pip install git+https://github.com/dmulyalin/nornir-salt

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
   * - ``prodmin``
     - Production ready minimum set. Installs Netmiko, Ncclient and requests libraries 
       to provide support for managing devices over SSH, NETCONF and RESTCONF. In addition, 
       installs libraries to extended Salt-Nornir functionality such as Tabulate, Rich, TTP 
       etc. All libraries have versions fixed to produce tested and working environment.
   * - ``prodmax``
     - Production ready maximum set. Installs all ``prodmin`` libraries together with 
       additional modules required to support complete Salt-Nornir feature set such as 
       PyGNMI, PyATS, Scrapli, NAPALM etc. All libraries have versions fixed to produce 
       tested and working environment.

To install Nornir-Salt only, without any additional plugins::

    pip install salt-nornir

To install minimum production set::

    pip install salt-nornir[prodmin]

To install maximum production set::

    pip install salt-nornir[prodmax]
