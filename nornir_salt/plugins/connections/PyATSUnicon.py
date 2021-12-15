"""
PyATSUnicon
###########

`PyATS <https://pubhub.devnetcloud.com/media/pyats/docs/index.html>`_
connection plugin to interact with network devices.

Check `supported platofrms <https://pubhub.devnetcloud.com/media/unicon/docs/user_guide/supported_platforms.html>`_
page for platform codes.

This plugin uses Genie to load testbed inventory with single device and optional jumphosts definition,
Genie itslef relies on PyATS to perform lower level tasks, where PyATS relies on Unicon library to
communicate with devices over CLI.

PyATSUnicon reference
=====================

.. autofunction:: nornir_salt.plugins.connections.PyATSUnicon.PyATSUnicon
"""
import logging
from typing import Any, Dict, Optional
from nornir.core.configuration import Config

try:
    from genie import testbed

    HAS_GENIE = True
except ImportError:
    HAS_GENIE = False

CONNECTION_NAME = "pyats"

log = logging.getLogger(__name__)


class PyATSUnicon:
    """
    This plugin makes use of PyATS tesbed definition to initiate device connections, testbed can
    be partially reconstructed out of Nornir inventory or complete testbed data can be provided under
    extras section.

    Sample minimum inventory that reconstructed to PyATS testbed::

        host-1:
          hostname: 192.168.16.20
          username: admin
          password: admin
          port: 22
          connection_options:
            pyats:
              platform: eos
              extras:
                devices:
                  host-1: {}

    ``connection_options:pyats:extras`` section used to load PyATS testbed object.

    Above invetory reconstructed to this PyATS testbed data::

        devices:
          host-1:
            os: eos
            credentials:
              default:
                username: admin
                password: admin
            connections:
              default:
                protocol: ssh
                ip: 192.168.16.20
                port: 22
              vty_1:
                protocol: ssh
                ip: 192.168.16.20

    Alternatively, full testbed data can be specified using extras like this::

        host-1:
          hostname: 192.168.16.20
          username: admin
          password: admin
          connection_options:
            pyats:
              extras:
                testbed:
                  name: eos_testbed
                devices:
                  host-1:
                    os: eos
                    credentials:
                      default:
                        username: admin
                        password: admin
                    connections:
                      default:
                        protocol: ssh
                        ip: 192.168.16.20
                        port: 22

    In that case, because all mandatory parameters ``os``, ``connections`` and ``credentials`` provided,
    extras data used as is to load PyATS tesbed.

    It is mandatory to specify exact device cli prompt under ``connection_options:pyats:extras:devices``
    as a dictionary key as well as for top level device key. In other words this will not work::

        host-1-foo:
          hostname: 192.168.16.20
          connection_options:
            pyats:
              extras:
                devices:
                  host-1-bar: {}

    Where ``host-1-foo`` is Nornir invetory host name and ``host-1-bar`` is actual device prompt
    as seen on cli, these two keys must be of the same value.

    This plugin establishes all connections to device on startup.

    To use connections pool instead of single connection, need to provide ``pool`` argument integer
    of value more or equal to 2 in connection's parametre, otherwise connection ignored::

        host-1:
          hostname: 192.168.16.20
          username: admin
          password: admin
          connection_options:
            pyats:
              extras:
                devices:
                  host-1:
                    os: eos
                    connections:
                      default:
                        protocol: ssh
                        ip: 192.168.16.20
                        pool: 3

    ``pool`` connection argument is not part of PyATS native testbed schema and only
    relevant in PyATSUnicon plugin context.
    """  # noqa

    def open(
        self,
        hostname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        port: Optional[int] = None,
        platform: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        extras = extras or {}
        pools = {}  # keyed by device name, connections name and pool_size

        # check if need to add missing data to devices in testbed
        for device_name, device_data in extras["devices"].items():
            if "credentials" not in device_data:
                device_data["credentials"] = {
                    "default": {"username": username, "password": password}
                }
            if "connections" not in device_data:
                device_data["connections"] = {
                    "default": {"protocol": "ssh", "ip": hostname, "port": port or 22}
                }
            if "os" not in device_data and platform:
                device_data["os"] = platform

            # add/extract data to/from connections
            for connection_name, connection_data in device_data["connections"].items():
                # check if connection is a pool
                pool_size = int(connection_data.pop("pool", 0))
                if pool_size > 1:
                    pools.setdefault(device_name, {})
                    pools[device_name][connection_name] = pool_size
                # check if connection missing "ip" field
                if "ip" not in connection_data and hostname:
                    connection_data["ip"] = hostname

        # load testbed
        self.connection = testbed.load(extras)

        # initiate non pool connections
        for device_name, device_data in extras["devices"].items():
            for connection_name, connection_data in device_data["connections"].items():
                # check if need to skip as there is connections pool exists already
                if not pools.get(device_name, {}).get(connection_name):
                    self.connection.devices[device_name].connect(
                        alias=connection_name, via=connection_name
                    )

        # initiate pool connections if any
        for device_name, device_data in pools.items():
            for connection_name, pool_size in device_data.items():
                self.connection.devices[device_name].start_pool(
                    size=pool_size, via=connection_name, alias=connection_name
                )
                # set pool size attribute to connections pool object for tasks to make use of it
                conn = getattr(self.connection.devices[device_name], connection_name)
                conn._pool_size = pool_size

    def close(self) -> None:
        # destroy connections to all devices in this testbed
        self.connection.destroy()
