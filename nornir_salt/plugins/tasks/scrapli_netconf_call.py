"""
scrapli_netconf_call
####################

Dependencies: `Scrapli Netconf <https://pypi.org/project/scrapli-netconf/>`_ need to be installed

Scrapli Netconf is a library to interact with devices using NETCONF. ``scrapli_netconf_call`` task 
plugin is a wrapper around Scrapli Netconf connection object.

NETCONF protocol has a specific set of RPC calls available for use, rather
than coding separate task for each of them, ``scrapli_netconf_call`` made to execute
any arbitrary method supported by Scrapli Netconf connection object plus a set 
of additional helper methods for extended functionality.

Sample code to run ``scrapli_netconf_call`` task::

    from nornir import InitNornir
    from nornir_salt import scrapli_netconf_call

    nr = InitNornir(config_file="config.yaml")
    
    output = nr.run(
        task=scrapli_netconf_call,
        call="get_config",
        source="running"
    )

API Reference
=============

.. autofunction:: nornir_salt.plugins.tasks.scrapli_netconf_call.scrapli_netconf_call

Additional Call Methods Reference
=================================

dir
---
.. autofunction:: nornir_salt.plugins.tasks.scrapli_netconf_call._call_dir

help
----
.. autofunction:: nornir_salt.plugins.tasks.scrapli_netconf_call._call_help

server_capabilities
-------------------

.. autofunction:: nornir_salt.plugins.tasks.scrapli_netconf_call._call_server_capabilities

connected
---------

.. autofunction:: nornir_salt.plugins.tasks.scrapli_netconf_call._call_connected

locked
------

.. autofunction:: nornir_salt.plugins.tasks.scrapli_netconf_call._call_locked
"""
import logging
import traceback
from nornir.core.task import Result, Task

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "scrapli_netconf"


def _call_dir(conn, *args, **kwargs):
    """Helper function to return a list of supported tasks"""
    methods = [m for m in dir(conn) if not m.startswith("_")] + [
        "dir",
        "connected",
        "locked",
    ]
    return sorted(methods), False


def _call_help(conn, *args, **kwargs):
    """
    Helper function to return docstring for requested method

    :param method_name: (str) name of method or function to return docstring for
    """
    method_name = kwargs["method_name"]
    if "_call_{}".format(method_name) in globals():
        function_obj = globals()["_call_{}".format(method_name)]
    else:
        function_obj = getattr(conn, method_name)
    h = function_obj.__doc__ if hasattr(function_obj, "__doc__") else ""
    return h, False


def _call_connected(conn, *args, **kwargs):
    """Helper function to return connection status"""
    return conn.isalive(), False


def _call_locked(conn, *args, **kwargs):
    """
    Helper function to run this edit-config flow:

    1. Lock target configuration/datastore
    2. Discard previous changes if any
    3. Run edit config
    4. Validate new confiugration if server supports it
    5. Commit configuration
    6. Unlock target configuration/datastore

    If any of steps 3, 4, 5 fails, all changes discarded

    :param target: (str) name of datastore to edit configuration for
    :param config: (str) configuration to apply
    :returns result: (list) list of steps performed with details
    :returns failed: (bool) status indicator if change failed
    """
    failed = False
    result = []
    try:
        # lock target config/datastore
        r = conn.lock(target=kwargs["target"])
        result.append({"lock": r.result})
        # discard previous changes if any
        r = conn.discard()
        result.append({"discard_changes": r.result})
        # apply configuration
        r = conn.edit_config(config=kwargs["config"], target=kwargs["target"])
        result.append({"edit_config": r.result})
        # validate configuration
        try:
            r = conn.validate(source=kwargs["target"])
            result.append({"validate": r.result})
        except Exception as e:
            result.append({"validate": str(e)})
            pass
        # commit configuration
        r = conn.commit()
        result.append({"commit": r.result})
        # unlock target config/datastore
        r = conn.unlock(target=kwargs["target"])
        result.append({"unlock": r.result})
    except:
        # form error message
        tb = traceback.format_exc()
        log.error(
            "nornir_salt:scrapli_netconf_call locked edit_config call error: {}".format(
                tb
            )
        )
        result.append({"error": tb})
        failed = True
        # discard changes on failure
        r = conn.discard()
        result.append({"discard_changes": r.result})
        # unlock target config/datastore
        r = conn.unlock(target=kwargs["target"])
        result.append({"unlock": r.result})

    return result, failed


def _call_server_capabilities(conn, *args, **kwargs):
    """Helper function to return NETCONF server capabilities"""
    return conn.server_capabilities, False


def scrapli_netconf_call(task: Task, call: str, *args, **kwargs) -> Result:
    """
    Dispatcher function to call one of the supported scrapli_netconf methods
    or one of helper functions.

    :param call: (str) Scrapli Netconf connection object method to call
    :param arg: (list) any ``*args`` to use with call method
    :param kwargs: (dict) any ``**kwargs`` to use with call method
    :return: result of scrapli-netconf connection method call
    """
    # initiate local parameteres
    result = None
    failed = False
    task.name = call

    # get rendered data if any
    if "__task__" in task.host.data:
        kwargs.update(task.host.data["__task__"])

    log.debug(
        "nornir_salt:scrapli_netconf_call calling '{}' with args: '{}'; kwargs: '{}'".format(
            call, args, kwargs
        )
    )

    # get scrapli-netconf connection object
    conn = task.host.get_connection("scrapli_netconf", task.nornir.config)

    # check if need to call one of helper function
    if "_call_{}".format(call) in globals():
        result, failed = globals()["_call_{}".format(call)](conn, *args, **kwargs)
    # call conn object method otherwise
    else:
        result = getattr(conn, call)(*args, **kwargs)
        failed = result.failed if hasattr(result, "failed") else failed

    # format results
    if hasattr(result, "result"):
        result = result.result
    elif isinstance(result, (list, dict, bool)):
        pass
    else:
        result = str(result)

    return Result(host=task.host, result=result, failed=failed)
