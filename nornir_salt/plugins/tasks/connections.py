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
    connections_close = nr.run(
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
import traceback
import logging

from typing import Optional, Any, Dict

from nornir.core.task import Result

log = logging.getLogger(__name__)


def conn_list(task, **kwargs):
    """
    Function to list host's active connections.

    :return: (list) list of hosts' connections
    """
    # form list of host connections
    ret = [
        {
            "connection_name": conn_name,
            "connection_plugin": str(type(conn_obj)).split(" ")[1].strip(">"),
        }
        for conn_name, conn_obj in task.host.connections.items()
    ]

    return Result(host=task.host, result=ret)


def conn_close(task, conn_name="all", **kwargs):
    """
    Task to close host's connections.

    :param conn_name: (str) name of connection to close, default is "all"
    :return: (list) list of connections closed
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


def conn_open(
    task,
    conn_name,
    hostname: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = None,
    platform: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    default_to_host_attributes: bool = True,
    close_open: bool = False,
    reconnect: list = None,
):
    """
    Helper function to open connection to host

    :param conn_name: name of connection to open
    :param hostname: hostname or ip address to connect to
    :param username: username to use to open the connection
    :param password: password to use to open the connection
    :param port: port to use to open the connection
    :param platform: platform name connection parameter
    :param extras: connection plugin extras parameters
    :param default_to_host_attributes: on True uses host's inventory data for not supplied arguments
    :param close_open: if True, closes already open connection and connects again
    :param reconnect: list of parameters to try connecting to device if primary set of
        parameters fails. If ``reconnect`` item is a dictionary, it is supplied as ``**kwargs``
        to host open connection call, alternatively, ``reconnect`` item can refer to a name
        of credentials set from inventory data ``credentials`` section.
    :return: boolean, True on success

    Sample ``reconnect`` list::

        [
            {
                "username": "cisco123",
                "port": "24",
                "password": "123cisco",
            },
            "deprecated_creds",
            "local_account"
        ]

    Where ``deprecated_creds`` and ``local_account`` stored in Nornir inventory data
    credentials section::

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

    # check if need to close connection first
    if conn_name in task.host.connections:
        if close_open:
            task.host.close_connection(conn_name)
        else:
            return Result(host=task.host, result="Connection already open")

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
            param = task.host.get("credentials", {}).get(param)

        if not isinstance(param, dict):
            raise TypeError("'{}' parameters not found or invalid".format(param_name))

        try:
            task.host.open_connection(
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
        except:
            tb = traceback.format_exc()
            ret = {
                "result": f"Connection failed\n\n{tb}",
                "exception": tb,
                "failed": True,
            }

    return Result(host=task.host, **ret)


def connections(task, call, **kwargs):
    """
    Dispatcher function to call one of the functions.

    :param call: (str) nickname of function to call
    :param arg: (list) function arguments
    :param kwargs: (dict) function key-word arguments
    :return: call function execution results

    Call function nicknames:

    * ls - calls conn_list
    * close - calls conn_close
    * open - calls conn_open
    """
    if "conn_name" in kwargs:
        task.name = "connections:{}:{}".format(call, kwargs["conn_name"])
    else:
        task.name = "connections:{}".format(call)

    dispatcher = {"ls": conn_list, "close": conn_close, "open": conn_open}

    return dispatcher[call](task, **kwargs)
