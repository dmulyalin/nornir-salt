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

transaction
-----------

.. autofunction:: nornir_salt.plugins.tasks.scrapli_netconf_call._call_transaction
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
        "transaction",
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


def _call_transaction(conn, *args, **kwargs):
    """
    Function to edit device configuration in a reliable fashion using
    capabilities advertised by NETCONF server.

    :param target: (str) name of datastore to edit configuration for, if no
        ``target`` argument provided and device supports candidate datastore uses
        ``candidate`` datastore, uses ``running`` datastore otherwise
    :param config: (str) configuration to apply
    :param validate: (bool) if True (default) validates candidate configuration before commit
    :returns result: (list) list of steps performed with details

    Function work flow:

    1. Lock target configuration datastore
    2. Discard previous changes if any
    3. Edit configuration
    4. If server supports it - validate configuration if ``validate`` argument is True
    5. If server supports it - do commit operation
    6. Unlock target configuration datastore
    7. If steps 3, 4 or 5 fails, discard all changes
    8. Return results list of dictionaries keyed by step name

    Scrapli-netconf implementation lacks of support for commit confirmed operation
    as of creating this module.
    """
    failed = False
    result = []
    can_validate, can_commit_confirmed, has_candidate_datastore = False, False, False

    # get capabilities
    for i in conn.server_capabilities:
        if "urn:ietf:params:netconf:capability:validate" in i:
            can_validate = True
        elif "urn:ietf:params:netconf:capability:candidate" in i:
            has_candidate_datastore = True
        elif "urn:ietf:params:netconf:capability:confirmed-commit" in i:
            can_commit_confirmed = True

    # decide on target configuration datastore
    kwargs["target"] = kwargs.get(
        "target", "candidate" if has_candidate_datastore else "running"
    )

    # run transaction
    try:
        # lock target config/datastore
        r = conn.lock(target=kwargs["target"])
        if r.failed:
            raise RuntimeError(r.result)
        # discard previous changes if any
        if has_candidate_datastore and kwargs["target"] == "candidate":
            r = conn.discard()
            if r.failed:
                raise RuntimeError(r.result)
            result.append({"discard_changes": r.result})
        # apply configuration
        r = conn.edit_config(config=kwargs["config"], target=kwargs["target"])
        if r.failed:
            raise RuntimeError(r.result)
        result.append({"edit_config": r.result})
        # validate configuration
        if can_validate and kwargs.get("validate", True):
            r = conn.validate(source=kwargs["target"])
            if r.failed:
                raise RuntimeError(r.result)
            result.append({"validate": r.result})
        # run commit
        if kwargs["target"] == "candidate" and has_candidate_datastore:
            r = conn.commit()
            if r.failed:
                raise RuntimeError(r.result)
            result.append({"commit": r.result})
        # unlock target config/datastore
        r = conn.unlock(target=kwargs["target"])
        if r.failed:
            raise RuntimeError(r.result)
    except:
        tb = traceback.format_exc()
        log.error("nornir_salt:scrapli_netconf_call transaction error: {}".format(tb))
        result.append({"error": tb})
        # discard changes on failure
        if has_candidate_datastore and kwargs["target"] == "candidate":
            r = conn.discard()
            result.append({"discard_changes": r.result})
        # unlock target config/datastore
        r = conn.unlock(target=kwargs["target"])
        failed = True

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
