"""
ConnectionsPool
###############

Connection pooling plugin to manage multiple connections to devices.

This plugin maintains a pool of connections to devices, allowing tasks to acquire
and release connections from the pool. If this behavior is not desirable, consider
using standard connection plugins instead.

ConnectionsPool reference
=========================

.. autofunction:: nornir_salt.plugins.connections.ConnectionsPool.ConnectionsPool
"""  # noqa

import logging
import time
from typing import Any, Dict, Optional
from nornir.core.configuration import Config
from nornir.core.inventory import Host
from multiprocessing import Lock

log = logging.getLogger(__name__)


class ConnObjWrap:
    """
    Helper class to wrap connection object to implement context manager.
    """

    def __init__(self, connection: Any, host: Host) -> None:
        self.connection = connection
        self.host = host
        self.lock = Lock()

    def __enter__(self) -> Any:
        self.lock.acquire(block=False)
        return self.connection

    def __exit__(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
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
              platform: arista_eos
            ConnectionsPool:
              extras:
                max: 3
    """  # noqa

    def __init__(self) -> None:
        self.connections: list = []
        self.parameters: Dict[str, Any] = {}
        self.max: int = 3
        self.connection: Optional["ConnectionsPool"] = None

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
        for c in self.connections:
            c.connection.close()

    def __enter__(self, connection_name: str, host: Host) -> Any:
        host_conn = self.get_connection(connection_name, host)
        with host_conn as c:
            return c

    def __exit__(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        pass

    def get_connection(
        self, connection_name: str, host: Host, timeout: int = 3
    ) -> ConnObjWrap:
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
