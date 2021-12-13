"""
PyGNMIPlugin
############

`PyGNMI library <https://pypi.org/project/pygnmi/>`_ connection plugin to interact
with devices over `gNMI <https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md>`_
protocol.

This plugin maintains long running gNMI connection to devices, if this behavior
not desirable, consider using Nornir host's ``close_connection`` method to close
gNMI connection.

PyGNMIPlugin reference
========================

.. autofunction:: nornir_salt.plugins.connections.PyGNMIPlugin.PyGNMIPlugin
"""
from typing import Any, Dict, Optional
from nornir.core.configuration import Config

try:
    from pygnmi.client import gNMIclient

    HAS_PYGNMI = True
except ImportError:
    HAS_PYGNMI = False

CONNECTION_NAME = "pygnmi"


class PyGNMIPlugin:
    """
    Full list of inventory extras see `PyGNMI Docs <https://github.com/akarneliuk/pygnmi>`_
    for ``gNMIclient`` class.

    Sample inventory::

        host-1:
          hostname: 192.168.16.20
          username: admin
          password: admin
          port: 2022
          connection_options:
            pygnmi:
              extras:
                insecure: True
                gnmi_timeout: 10

    Anything under inventory ``extras`` section passed on to PyGNMI
    ``gNMIclient`` class object instantiation.
    """  # noqa

    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        extras = extras or {}

        parameters: Dict[str, Any] = {
            "target": (hostname, port or 6030),
            "username": username,
            "password": password,
        }

        parameters.update(extras)

        self.client = gNMIclient(**parameters)
        self.connection = self.client.connect()

    def close(self) -> None:
        self.client.close()
        self.connection.close()
