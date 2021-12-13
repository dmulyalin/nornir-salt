"""
ConnectionsPool
###############

`PyGNMI library <https://pypi.org/project/pygnmi/>`_ connection plugin to interact with devices over
`gNMI <https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md>`_
protocol.

This plugin maintains long running gNMI connection to devices, if this behavior
not desirable, consider using Nornir host's ``close_connection`` method to close
gNMI connection.

ConnectionsPool reference
=========================

.. autofunction:: nornir_salt.plugins.connections.ConnectionsPool.ConnectionsPool
"""  # noqa
import logging
import time
from typing import Any, Dict, Optional
from nornir.core.configuration import Config
from multiprocessing import Lock

log = logging.getLogger(__name__)


class ConnObjWrap:
    """
    Helper class to wrap connection object into
    to implement context manager
    """

    def __init__(self, conection, host):
        self.connection = conection
        self.host = host
        self.lock = Lock()

    def __enter__(self):
        self.lock.acquire(block=False)
        return self.connection

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.lock.release()
        log.debug(
            "nornir-salt:ConnectionPool {} connection released '{}'".format(
                self.host.name, self.connection
            )
        )


class ConnectionsPool:
    """

    Sample inventory::

        host-1:
          hostname: 192.168.16.20
          username: admin
          password: admin
          port: 22
          connection_options:
            netmiko:
              platform: ariste_eos
            ConnectionsPool:
              extras:
                max: 3
    """  # noqa

    def __init__(self):
        self.connections = []
        self.parameters = {}
        self.max = 3
        self.connection = None

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

        self.parameters = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "port": port,
            "platform": platform,
            "extras": extras,
            "configuration": configuration,
        }

        self.max = extras.get("max", 3)

        self.connection = self

    def close(self) -> None:
        for c in self.connections():
            c.connection.close()

    def __enter__(self, connection_name, host):
        host_conn = self.get_connection(connection_name, host)
        with host_conn() as c:
            return c

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass

    def get_connection(self, connection_name, host, timeout=3):
        """
        Function to get connection and lock it.
        """
        host_conn = None
        stime = time.time()

        while int(time.time() - stime) < timeout:

            # see if has unused connections
            for c in self.connections:
                if c.lock.acquire(block=False):
                    host_conn = c
                    break
            if host_conn:
                break

            # establish additional connection
            if len(self.connections) < self.max:
                conn = host.get_connection(
                    connection_name, configuration=self.parameters["configuration"]
                )
                c = ConnObjWrap(conn, host)
                _ = host.connections.pop(connection_name)
                c.lock.acquire()
                self.connections.append(c)
                host_conn = c
                if len(self.connections) == self.max:
                    host.connections[connection_name] = self
                break

            time.sleep(0.1)

        # if reached this point it means failed to get connection
        else:
            raise RuntimeError(
                "nornir-salt:ConnectionPool {} failed to acquire connection '{}'".format(  # noqa
                    host.name, connection_name
                )
            )

        log.debug(
            "nornir-salt:ConnectionPool {} acquired connection '{}'".format(
                host.name, host_conn.connection
            )
        )

        return host_conn
