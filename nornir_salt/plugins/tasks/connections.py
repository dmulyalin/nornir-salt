"""
connections
###########

Collection of task plugins to work with Nornir hosts' connections

Sample usage
============

Code to invoke ``connections`` task plugins::

    TBD

API reference
=============

.. autofunction:: nornir_salt.plugins.tasks.connections.connections
.. autofunction:: nornir_salt.plugins.tasks.connections.conn_list
.. autofunction:: nornir_salt.plugins.tasks.connections.conn_close
"""
import traceback
import logging

from nornir.core.task import Result

log = logging.getLogger(__name__)


def conn_list(task, *args, **kwargs):
    """
    Function to list hos's active connections.

    return: (list) list of hosts's connections
    """
    # form list of host connections
    ret = [
        {"connection_name": conn_name, "connection_type": str(type(conn_obj))}
        for conn_name, conn_obj in task.host.connections.items()
    ]

    return Result(host=task.host, result=ret)


def conn_close(task, conn_name="all", *args, **kwargs):
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


def connections(task, call, *args, **kwargs):
    """
    Dispatcher function to call one of the functions.

    :param call: (str) nickname of function to call
    :param arg: (list) function arguments
    :param kwargs: (dict) function key-word arguments
    :return: function execution results

    Call function nicknames:

    * ls - calls conn_list
    * close - calls conn_close
    """
    dispatcher = {"ls": conn_list, "close": conn_close}
    return dispatcher[call](task, *args, **kwargs)
