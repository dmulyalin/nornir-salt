"""
connections
###########

Collection of task plugins to work with Nornir hosts' connections

Sample usage
============

Code to invoke ``connections`` task plugins::

    from nornir import InitNornir

    from nornir_salt.plugins.tasks import connections

    nr = InitNornir(config_file="config.yaml")

    # get a list of connection
    connections_active = nr.run(
        task=connections,
        call="ls"
    )

    # close all connections
    conn_close = nr.run(
        task=connections,
        call="close"
    )

    # connect netmiko connections
    connections_connect = nr.run(
        task=connections,
        call="open",
        conn_name="netmiko",
        username="user123",
        password="pass123",
        reconnect=[
            {
                "username": "user321",
                "password": "pass321",
            },
            "local_creds",
        ]
    )

API reference
=============

.. autofunction:: nornir_salt.plugins.tasks.connections.connections
.. autofunction:: nornir_salt.plugins.tasks.connections.conn_list
.. autofunction:: nornir_salt.plugins.tasks.connections.conn_close
.. autofunction:: nornir_salt.plugins.tasks.connections.conn_open
"""
import time
import traceback
import logging

from typing import Optional, Any, Dict
from nornir.core.task import Result
from nornir.core.inventory import Host
from nornir_salt.utils.pydantic_models import (
    model_conn_list,
    model_conn_close,
    model_conn_open,
    model_connections,
)
from nornir_salt.utils.yangdantic import ValidateFuncArgs

log = logging.getLogger(__name__)


@ValidateFuncArgs(model_conn_list)
def conn_list(task, conn_name: str = "all") -> list:
    """
    Function to list host's active connections.

    :param conn_name: name of connection to list, default is "all"
    :return: list of hosts' connections
    """
    # form list of host connections
    ret = [
        {
            "connection_name": conn,
            "connection_plugin": str(type(conn_obj)).split(" ")[1].strip(">"),
        }
        for conn, conn_obj in task.host.connections.items()
        if conn_name == "all" or conn == conn_name
    ]

    return Result(host=task.host, result=ret)


@ValidateFuncArgs(model_conn_close)
def conn_close(task, conn_name: str = "all") -> list:
    """
    Task to close host's connections.

    :param conn_name: name of connection to close, default is "all"
    :return: list of connections closed
    """
    ret = []

    # iterate over connections and close them
    for conn in list(task.host.connections.keys()):
        if conn_name != "all" and conn != conn_name:
            continue
        ret.append({"connection_name": conn})
        try:
            task.host.close_connection(conn)
        except:
            ret[-1]["status"] = traceback.format_exc()
        _ = task.host.connections.pop(conn, None)
        ret[-1].setdefault("status", "closed")

    return Result(host=task.host, result=ret)


@ValidateFuncArgs(model_conn_open)
def conn_open(
    task,
    conn_name,
    host: Optional[Host] = None,
    hostname: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = None,
    platform: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    default_to_host_attributes: bool = True,
    close_open: bool = False,
    reconnect: list = None,
    raise_on_error: bool = False,
):
    """
    Helper function to open connections to hosts. Supports reconnect
    logic retrying different connection parameters.

    :param conn_name: name of connection to open
    :param hostname: hostname or ip address to connect to
    :param username: username to use to open the connection
    :param password: password to use to open the connection
    :param port: port to use to open the connection
    :param platform: platform name connection parameter
    :param extras: connection plugin extras parameters
    :param default_to_host_attributes: on True uses host's inventory data for not supplied arguments
    :param close_open: if True, closes already open connection and connects again
    :param reconnect: list of parameters to use to try connecting to device if primary set of
        parameters fails. If ``reconnect`` item is a dictionary, it is supplied as ``**kwargs``
        to host open connection call. Alternatively, ``reconnect`` item can refer to a name
        of credentials set from inventory data ``credentials`` section within host, groups or
        defaults section.
    :param raise_on_error: raises error if not able to establish connection even after trying
        all ``reconnect`` parameters, used to signal exception to parent function e.g. RetryRunner
    :param host: Nornir Host object supplied by RetryRunner
    :return: boolean, True on success

    Sample ``reconnect`` list content::

        [
            {
                "username": "foo123",
                "port": "24",
                "password": "123foo",
            },
            "deprecated_creds",
            "local_account"
        ]

    Where ``deprecated_creds`` and ``local_account`` could be stored
    in Nornir inventory default data credentials section::

        defaults:
          data:
            credentials:
              deprecated_creds:
                password: foo
                username: bar
              local_account:
                password: nornir
                username: nornir
    """
    reconnect = reconnect or []
    ret = {}
    host = host or task.host

    # check if need to close connection first
    if conn_name in host.connections:
        if close_open:
            host.close_connection(conn_name)
        else:
            return Result(host=host, result="Connection already open")

    conn_params = [
        {
            "hostname": str(hostname) if hostname is not None else None,
            "username": str(username) if username is not None else None,
            "password": str(password) if password is not None else None,
            "port": int(port) if port is not None else None,
            "platform": str(platform) if platform is not None else None,
            "extras": extras,
            "default_to_host_attributes": default_to_host_attributes,
        }
    ] + reconnect

    for index, param in enumerate(conn_params):
        param_name = "kwargs" if index == 0 else index

        # source parameters from inventory crdentials section
        if isinstance(param, str):
            param_name = param
            param = host.get("credentials", {}).get(param)

        if not isinstance(param, dict):
            raise TypeError("'{}' parameters not found or invalid".format(param_name))

        try:
            host.open_connection(
                **param, connection=conn_name, configuration=task.nornir.config
            )
            if index == 0:
                msg = "Connected with 'kwargs' parameters"
            elif isinstance(param_name, str):
                msg = "Connected with '{}' parameters, reconnect index '{}'".format(
                    param_name, index - 1
                )
            else:
                msg = "Connected with reconnect index '{}'".format(index - 1)
            ret = {"result": msg}
            break
        except:
            tb = traceback.format_exc()
            ret = {
                "result": f"Connection failed\n\n{tb}",
                "exception": tb,
                "failed": True,
            }
            time.sleep(0.1)

    # check if need to raise an error
    if ret.get("exception") and raise_on_error:
        raise RuntimeError(ret["exception"])

    return Result(host=host, **ret)


@ValidateFuncArgs(model_connections)
def connections(task, call, **kwargs):
    """
    Dispatcher function to call one of the functions.

    :param call: (str) nickname of function to call
    :param arg: (list) function arguments
    :param kwargs: (dict) function key-word arguments
    :return: call function execution results

    Call function nicknames:

    * ls - calls conn_list task
    * close - calls conn_close task
    * open - calls conn_open task
    """
    if "conn_name" in kwargs:
        task.name = "connections:{}:{}".format(call, kwargs["conn_name"])
    else:
        task.name = "connections:{}".format(call)

    dispatcher = {"ls": conn_list, "close": conn_close, "open": conn_open}

    return dispatcher[call](task, **kwargs)
