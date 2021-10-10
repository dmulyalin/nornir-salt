"""
pgnmi_call
##########

Task plugin to manage devices over gNMI protocol. Uses
`PyGNMI library <https://pypi.org/project/pygnmi/>`_

This task plugin is a wrapper around ``gNMIclient`` connection object
and allows to execute any of its methods supplying method name using
``call`` attribute.

Sample code to run ``pygnmi_call`` task::

    from nornir import InitNornir
    from nornir_salt import pygnmi_call

    nr = InitNornir(config_file="config.yaml")
    
    output = nr.run(
        task=pygnmi_call,
        call="get",
        path=["openconfig-interfaces:interfaces"]
    )

In addition to calling ``gNMIclient`` methods, extra call methods supported
such as ``help``, ``dir``, ``delete`` etc, that can be used as this::

    from nornir import InitNornir
    from nornir_salt import pygnmi_call

    nr = InitNornir(config_file="config.yaml")
    
    available_methods = nr.run(
        task=pygnmi_call,
        call="dir",
    )

pygnmi_call Reference
=====================

.. autofunction:: nornir_salt.plugins.tasks.pygnmi_call.pygnmi_call

Additional Call Methods 
=======================

delete
------
.. autofunction:: nornir_salt.plugins.tasks.pygnmi_call._call_delete

dir
---
.. autofunction:: nornir_salt.plugins.tasks.pygnmi_call._call_dir

help
----
.. autofunction:: nornir_salt.plugins.tasks.pygnmi_call._call_help

replace
-------
.. autofunction:: nornir_salt.plugins.tasks.pygnmi_call._call_replace

update
------
.. autofunction:: nornir_salt.plugins.tasks.pygnmi_call._call_update
"""
import traceback
import logging

from nornir.core.task import Result, Task
from nornir_salt.plugins.connections.PyGNMIPlugin import CONNECTION_NAME

log = logging.getLogger(__name__)


def _call_dir(connection, **kwargs):
    """Function to return a list of gNMIclient available methods/operations"""
    methods = (list(dir(connection))) + ["dir", "help", "update", "delete", "replace"]
    result = sorted(
        [m for m in set(methods) if (not m.startswith("_") and not m.isupper())]
    )
    return result


def _call_help(connection, method_name: str, **kwargs):
    """
    Helper function to return docstring for requested method

    :param method_name: (str) name of method or function to return docstring for
    """
    if "_call_{}".format(method_name) in globals():
        function_obj = globals()["_call_{}".format(method_name)]
    else:
        function_obj = getattr(connection, method_name)
    h = function_obj.__doc__ if hasattr(function_obj, "__doc__") else ""
    return h


def _call_update(connection, path: list, **kwargs):
    """
    Udate function helps to update configuration for elements matched by
    single path string.

    This function effectively takes arguments provided and uses ``gNMIclient``
    ``set`` method supplying it with ``update`` argument list that consists of
    single tuple element, this tuple's first item is a provided path string with
    second item being a dictionary of provided ``**kwargs`` containing configuration
    to be updated.

    :param connection: (obj) ``gNMIclient`` object
    :param path: (list) list with single item - path to element to update config for
    :param kwargs: (dict) configuration parameters to update
    """
    return connection.set(update=[(path[0], dict(kwargs))])


def _call_replace(connection, path: list, **kwargs):
    """
    Replace function helps to replace configuration for elements matched by
    single path string.

    This function effectively takes arguments provided and uses ``gNMIclient``
    ``set`` method supplying it with ``replace`` argument list that consists of
    single tuple element, this tuple's first item is a provided path string with
    second item being a dictionary of provided ``**kwargs`` containing configuration
    to be replaced.

    :param connection: (obj) ``gNMIclient`` object
    :param path: (list) list with single item - path to element to update config for
    :param kwargs: (dict) configuration parameters to replace
    """
    return connection.set(replace=[(path[0], dict(kwargs))])


def _call_delete(connection, path: list, **kwargs):
    """
    Delete function helps to delete configuration elements matched by provided paths
    strings.

    This function effectively takes arguments provided and uses ``gNMIclient``
    ``set`` method supplying it with ``delete`` argument list that consists of
    path items strings.

    :param connection: (obj) ``gNMIclient`` object
    :param path: (list) path items to delete
    """
    return connection.set(delete=path)


def pygnmi_call(task: Task, call: str, name_arg: str = None, **kwargs) -> Result:
    """
    Task to call one of PyGNMI ``gNMIclient`` object methods or one of
    additional helper functions.

    :param call: (str) ``gNMIclient`` connection object method to call
    :param arg: (list) any ``*args`` to use with call method
    :param kwargs: (dict) any ``**kwargs`` to use with call method
    :param name_arg: (str) used as "name" argument with call method, need it
        only because "name" argument used by "Nornir.run" method itself
    """
    # update task name
    task.name = call

    # check if "_name_arg" in kwargs, use it as "name", this happens
    # if actual "name" argument given on nr.gnmi call by saltstack
    if name_arg:
        kwargs["name"] = name_arg

    # transform arguments for set delete and get calls from string to list
    if isinstance(kwargs.get("path"), str):
        kwargs["path"] = [i.strip() for i in kwargs["path"].split(",") if i.strip()]
    if isinstance(kwargs.get("delete"), str):
        kwargs["delete"] = [i.strip() for i in kwargs["delete"].split(",") if i.strip()]
    # convert set replace and set update list items to tuples
    if isinstance(kwargs.get("replace"), list):
        kwargs["replace"] = [
            tuple(i) for i in kwargs["replace"] if isinstance(i, (list, tuple))
        ]
    if isinstance(kwargs.get("update"), list):
        kwargs["update"] = [
            tuple(i) for i in kwargs["update"] if isinstance(i, (list, tuple))
        ]

    # get gNMIclient connection object
    connection = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    log.debug("nornir_salt:pygnmi_call call '{}', kwargs: '{}'".format(call, kwargs))

    # check if need to call one of helper function
    if "_call_{}".format(call) in globals():
        result = globals()["_call_{}".format(call)](connection, **kwargs)
    # call connection object method otherwise
    else:
        result = getattr(connection, call)(**kwargs)

    return Result(host=task.host, result=result)
