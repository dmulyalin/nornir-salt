"""
network
#######

Collection of task plugins to work with networks. Primarily
useful for testing DNS, host connectivity etc.

Sample usage
============

Code to invoke ``network`` task plugins::

    from nornir import InitNornir
    from nornir_salt.plugins.tasks import network

    nr = InitNornir(config_file="config.yaml")

    # resolve host's hostname
    answers = nr.run(
        task=network,
        call="resolve_dns"
    )

API reference
=============

.. autofunction:: nornir_salt.plugins.tasks.network.network
.. autofunction:: nornir_salt.plugins.tasks.network.resolve_dns
"""
import time
import traceback
import logging
import socket

try:
    import dns.resolver

    HAS_DNS = True
except ImportError:
    HAS_DNS = False

try:
    import pythonping

    HAS_PYTHONPING = True
except ImportError:
    HAS_PYTHONPING = False

from typing import Optional, Any, Dict, Union
from nornir.core.task import Result
from nornir_salt.utils.pydantic_models import model_network, model_network_resolve_dns
from nornir_salt.utils.yangdantic import ValidateFuncArgs

log = logging.getLogger(__name__)


@ValidateFuncArgs(model_network_resolve_dns)
def resolve_dns(
    task,
    servers: Union[list, str] = None,
    use_host_name: bool = False,
    timeout: float = 2.0,
    ipv4: bool = True,
    ipv6: bool = False,
) -> Result:
    """
    Function to resolve host's hostname A and AAAA records.

    ``dnspython`` package need to be installed for this function to work::

        pip install dnspython

    :param server: list or comma separated string of IP addresses or FQDNs
        of DNS servers to use
    :param use_host_name: if True resolves host's ``name`` instead of host's ``hostname``
    :param timeout: number of seconds to wait for response from DNS server
    :param ipv4: resolve 'A' record
    :param ipv6: resolve 'AAAA' record
    :return: returns a list of resolved addresses
    """
    task.name = "resolve_dns"
    if not HAS_DNS:
        return Result(
            host=task.host,
            failed=True,
            result="Failed importing dnspython, is it installed?",
        )

    res = set()
    failed = False
    exception_messages = []
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout

    # decide on the records list to resolve
    records = ["A"] if ipv4 else []
    if ipv6:
        records.append("AAAA")

    # add custom DNS servers
    if servers:
        if isinstance(servers, str):
            servers = [i.strip() for i in servers.split(",")]
        resolver.nameservers = servers

    # source FQDN to resolve
    if use_host_name:
        hostname = task.host.name
    else:
        hostname = task.host.hostname

    # resolve DNS records
    for record in records:
        try:
            answers = resolver.resolve(hostname, rdtype=record)
            for answer in answers:
                res.add(answer.address)
        except:
            tb = traceback.format_exc()
            failed = True
            exception_messages.append(
                f"resolve_dns '{task.host.name}' failed to resolve '{record}' record for '{hostname}'\n{tb}"
            )

    return Result(
        host=task.host,
        failed=failed,
        exception="\n".join(exception_messages) if exception_messages else None,
        result=list(sorted(res)),
    )


def icmp_ping(task, use_host_name: bool = False, **kwargs) -> Result:
    """
    Functiont to ping host using ICMP.

    Requires `pythonping <https://github.com/alessandromaggio/pythonping>_`
    library.

    :param use_host_name: if True pings host's ``name`` instead of host's ``hostname``
    :param kwargs: any additional arguments for ``pythonping.ping`` call
    """
    ret = {}
    task.name = "ping"

    if not HAS_PYTHONPING:
        return Result(
            host=task.host,
            failed=True,
            result="Failed importing pythonping, is it installed?",
        )

    # source target to ping
    if use_host_name:
        target = task.host.name
    else:
        target = task.host.hostname

    try:
        ret["result"] = pythonping.ping(target, **kwargs)
    except:
        ret["result"] = None
        ret["failed"] = True
        ret["exception"] = traceback.format_exc()

    return Result(host=task.host, **ret)


@ValidateFuncArgs(model_network)
def network(task, call, **kwargs) -> Result:
    """
    Dispatcher function to call one of the functions.

    :param call: (str) nickname of function to call
    :param kwargs: (dict) function key-word arguments
    :return: call function execution results

    Call functions:

    * resolve_dns - resolve hostname DNS
    """
    dispatcher = {
        "resolve_dns": resolve_dns,
        "ping": icmp_ping,
        # "reverse_dns": reverse_dns,
        # traceroute
        # connect
    }

    return dispatcher[call](task, **kwargs)
