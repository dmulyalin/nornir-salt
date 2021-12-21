"""
tcp_ping
########

Tests connection to a TCP port trying to establish a three way
handshake. Useful for network discovery or testing.

tcp_ping sample usage
=====================

Sample code to run ``tcp_ping`` task::

    import pprint
    from nornir import InitNornir
    from nornir_salt.plugins.tasks import tcp_ping
    from nornir_salt.plugins.functions import ResultSerializer

    nr = InitNornir(config_file="config.yaml")

    result = NornirObj.run(
        task=tcp_ping,
        ports=[22]
    )

    result_dictionary = ResultSerializer(result)

    pprint.pprint(result_dictionary)

    # prints:
    #
    # {'IOL1': {'tcp_ping': {22: True}},
    #  'IOL2': {'tcp_ping': {22: True}}}


tcp_ping returns
================

Returns dictionary of port numbers as keys with True/False as values

tcp_ping reference
==================

.. autofunction:: nornir_salt.plugins.tasks.tcp_ping.tcp_ping
"""

import socket
from typing import Optional, List

from nornir.core.task import Result, Task


def tcp_ping(
    task: Task, ports: List[int] = None, timeout: int = 1, host: Optional[str] = None
) -> Result:
    """
    :param ports: list of int, optional, tcp ports to ping, defaults to host's port or 22
    :param timeout: int, optional, connection timeout, defaults to 1
    :param host: string, optional, address to TCP ping, defaults to hosts's ``hostname`` value
    :returns: dictionary of port numbers as keys with True/False as values
    """
    ports = ports or []

    if not ports:
        ports = [task.host.port if task.host.port else 22]
    elif isinstance(ports, int):
        ports = [ports]

    if isinstance(ports, list):
        if not all(isinstance(port, int) for port in ports):
            raise ValueError("Invalid value for 'ports'")
    else:
        raise ValueError("Invalid value for 'ports'")

    host = host or task.host.hostname

    result = {}
    for port in ports:
        s = socket.socket()
        s.settimeout(timeout)
        try:
            status = s.connect_ex((host, port))
            if status == 0:
                connection = True
            else:
                connection = False
        except (socket.gaierror, socket.timeout, socket.error):
            connection = False
        finally:
            s.close()
        result[port] = connection

    return Result(host=task.host, result=result)
