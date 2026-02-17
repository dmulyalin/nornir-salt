"""
tcp_ping
########

Tests connection to a TCP port by attempting to establish a three-way
handshake. Useful for network discovery or testing.

tcp_ping sample usage
=====================

Sample code to run ``tcp_ping`` task::

    import pprint
    from nornir import InitNornir
    from nornir_salt.plugins.tasks import tcp_ping
    from nornir_salt.plugins.functions import ResultSerializer

    nr = InitNornir(config_file="config.yaml")

    result = nr.run(
        task=tcp_ping,
        ports=[22]
    )

    result_dictionary = ResultSerializer(result)

    pprint.pprint(result_dictionary)

    # Example output:
    # {
    #   'IOL1': {'tcp_ping': {22: True}},
    #   'IOL2': {'tcp_ping': {22: True}}
    # }

tcp_ping returns
================

Returns a dictionary of port numbers as keys with True/False as values.

tcp_ping reference
==================

.. autofunction:: nornir_salt.plugins.tasks.tcp_ping.tcp_ping
"""

import logging
import socket
from typing import Dict, List, Optional

from nornir.core.task import Result, Task

log = logging.getLogger(__name__)


def tcp_ping(
    task: Task,
    ports: Optional[List[int]] = None,
    timeout: int = 1,
    host: Optional[str] = None,
) -> Result:
    """
    Test connection to a TCP port by attempting to establish a three-way handshake.

    :param task: Nornir task object.
    :param ports: List of TCP ports to ping. Defaults to the host's port or 22.
    :param timeout: Connection timeout in seconds. Defaults to 1.
    :param host: Address to TCP ping. Defaults to the host's ``hostname`` value.
    :return: Dictionary of port numbers as keys with True/False as values.
    """
    ports = ports or []

    if not ports:
        ports = [int(task.host.port) if task.host.port else 22]
    elif isinstance(ports, int):
        ports = [ports]

    if isinstance(ports, list):
        if not all(isinstance(port, int) for port in ports):
            raise ValueError("Invalid value for 'ports'. All ports must be integers.")
    else:
        raise ValueError("Invalid value for 'ports'. Expected a list of integers.")

    host = host or task.host.hostname

    result: Dict[int, bool] = {}
    for port in ports:
        s = socket.socket()
        s.settimeout(timeout)
        try:
            status = s.connect_ex((host, port))
            connection = status == 0
        except (socket.gaierror, socket.timeout, socket.error):
            connection = False
        finally:
            s.close()
        result[port] = connection

    return Result(host=task.host, result=result)
