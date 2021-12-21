"""
ncclient_call
#############

`Ncclient <https://github.com/ncclient>`_ is a popular library to interact with
devices using NETCONF, this plugin is a wrapper around ncclient connection
manager object.

NETCONF protocol has a specific set of RPC calls available for use, rather
than coding separate task for each of them, ``ncclient_call`` made to execute
any arbitrary method supported by manager object plus a set of additional
helper methods to extend Ncclient library functionality.

ncclient_call sample usage
==========================

Sample code to run ``ncclient_call`` task::

    from nornir import InitNornir
    from nornir_salt import ncclient_call

    nr = InitNornir(config_file="config.yaml")

    output = nr.run(
        task=ncclient_call,
        call="get_config",
        source="running"
    )

ncclient_call returns
=====================

Returns XML text string by default, but can return XML data transformed
in JSON, YAML or Python format.

ncclient_call reference
=======================

.. autofunction:: nornir_salt.plugins.tasks.ncclient_call.ncclient_call

additional methods reference
============================

ncclient_call - dir
-------------------
.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_dir

ncclient_call - help
--------------------
.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_help

ncclient_call - server_capabilities
-----------------------------------

.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_server_capabilities

ncclient_call - connected
-------------------------

.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_connected

ncclient_call - transaction
---------------------------

.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_transaction
"""
import traceback
import logging
import time

from nornir.core.task import Result, Task
from nornir_salt.plugins.connections.NcclientPlugin import CONNECTION_NAME

log = logging.getLogger(__name__)

try:
    import lxml.etree as etree  # nosec

    HAS_LXML = True
except ImportError:
    HAS_LXML = False

try:
    from ncclient.manager import OPERATIONS
    from ncclient.operations.errors import MissingCapabilityError

    HAS_NCCLIENT = True
except ImportError:
    HAS_NCCLIENT = False

try:
    # this import should work for ncclient >=0.6.10
    from ncclient.operations import GenericRPC

except ImportError:
    # for ncclient<0.6.10 need to reconstruct GenericRPC class
    if HAS_NCCLIENT:

        from ncclient.operations import RPC

        class GenericRPC(RPC):
            def request(self, data, *args, **kwargs):
                """
                :param data: (str) rpc xml string

                Testing:

                * Arista cEOS - not working, transport session closed error
                * Cisco IOS XR - working
                """
                ele = etree.fromstring(data.encode("UTF-8"))  # nosec
                return self._request(ele)


def _call_transaction(manager, *args, **kwargs):
    """
    Function to edit device configuration in a reliable fashion using
    capabilities advertised by NETCONF server.

    :param target: (str) name of datastore to edit configuration for, if no
        ``target`` argument provided and device supports candidate datastore uses
        ``candidate`` datastore, uses ``running`` datastore otherwise
    :param config: (str) configuration to apply
    :param format: (str) configuration string format, default is xml
    :param confirmed: (bool) if True (default) uses commit confirmed
    :param commit_final_delay: (int) time to wait before doing final commit after
        commit confirmed, default is 1 second
    :param confirm_delay: (int) device commit confirmed rollback delay, default 60 seconds
    :param validate: (bool) if True (default) validates candidate configuration before commit
    :returns result: (list) list of steps performed with details

    Function work flow:

    1. Lock target configuration datastore
    2. If server supports it - Discard previous changes if any
    3. Edit configuration
    4. If server supports it - validate configuration if ``validate`` argument is True
    5. If server supports it - do commit confirmed if ``confirmed`` argument is True
    6. If server supports it - do commit operation
    7. Unlock target configuration datastore
    8. If server supports it - discard all changes if any of steps 3, 4, 5 or 6 fail
    9. Return results list of dictionaries keyed by step name
    """
    result = []
    failed = False
    commit_final_delay = int(kwargs.get("commit_final_delay", 1))
    confirm_delay = str(
        kwargs.get("confirm_delay", 60)
    )  # ncclient expects timeout to be a string

    # get capabilities
    can_validate = ":validate" in manager.server_capabilities
    can_commit_confirmed = ":confirmed-commit" in manager.server_capabilities
    has_candidate_datastore = ":candidate" in manager.server_capabilities

    # decide on target configuration datastore
    kwargs["target"] = kwargs.get(
        "target", "candidate" if has_candidate_datastore else "running"
    )

    # execute transaction
    with manager.locked(target=kwargs["target"]):
        if has_candidate_datastore and kwargs["target"] == "candidate":
            r = manager.discard_changes()
            result.append(
                {"discard_changes": etree.tostring(r._root, pretty_print=True)}
            )
        try:
            r = manager.edit_config(
                config=kwargs["config"],
                target=kwargs["target"],
                format=kwargs.get("format", "xml"),
            )
            result.append({"edit_config": etree.tostring(r._root, pretty_print=True)})
            # validate configuration
            if can_validate and kwargs.get("validate", True):
                r = manager.validate(source=kwargs["target"])
                result.append({"validate": etree.tostring(r._root, pretty_print=True)})
            if kwargs["target"] == "candidate" and has_candidate_datastore:
                # run commit confirmed
                if can_commit_confirmed and kwargs.get("confirmed", True):
                    pid = "dob04041989"
                    r = manager.commit(
                        confirmed=True, timeout=confirm_delay, persist=pid
                    )
                    result.append(
                        {"commit_confirmed": etree.tostring(r._root, pretty_print=True)}
                    )
                    # run final commit
                    time.sleep(commit_final_delay)
                    r = manager.commit(confirmed=True, persist_id=pid)
                    result.append(
                        {"commit": etree.tostring(r._root, pretty_print=True)}
                    )
                # run normal commit
                else:
                    r = manager.commit()
                    result.append(
                        {"commit": etree.tostring(r._root, pretty_print=True)}
                    )
        except:
            tb = traceback.format_exc()
            log.error("nornir_salt:ncclient_call transaction error: {}".format(tb))
            result.append({"error": tb})
            if has_candidate_datastore and kwargs["target"] == "candidate":
                r = manager.discard_changes()
                result.append(
                    {"discard_changes": etree.tostring(r._root, pretty_print=True)}
                )
            failed = True

    return result, failed


def _call_server_capabilities(manager, *args, **kwargs):
    """Helper function to get server capabilities"""
    return [c for c in manager.server_capabilities], False


def _call_connected(manager, *args, **kwargs):
    """Helper function to get connected status"""
    return manager.connected, False


def _call_dir(manager, *args, **kwargs):
    """Function to return alist of available methods/operations"""
    methods = (
        list(dir(manager))
        + list(manager._vendor_operations.keys())
        + list(OPERATIONS.keys())
        + ["dir", "help", "transaction"]
    )
    result = sorted(
        [m for m in set(methods) if (not m.startswith("_") and not m.isupper())]
    )
    return result, False


def _call_help(manager, method_name, *args, **kwargs):
    """
    Helper function to return docstring for requested method

    :param method_name: (str) name of method or function to return docstring for
    """
    if "_call_{}".format(method_name) in globals():
        function_obj = globals()["_call_{}".format(method_name)]
    else:
        function_obj = getattr(manager, method_name)
    h = function_obj.__doc__ if hasattr(function_obj, "__doc__") else ""
    return h, False


def ncclient_call(task: Task, call: str, *args, **kwargs) -> Result:
    """
    Task to handle a call of NCClient manager object methods

    :param call: (str) ncclient manager object method to call
    :param arg: (list) any ``*args`` to use with call method
    :param kwargs: (dict) any ``**kwargs`` to use with call method
    """
    # run sanity check
    if not HAS_NCCLIENT:
        return Result(
            host=task.host, failed=True, exception="No Ncclient found, is it installed?"
        )

    # initiate parameters
    failed = False
    task.name = call

    # get rendered data if any
    if "__task__" in task.host.data:
        kwargs.update(task.host.data["__task__"])

    # check if filter formed properly - as per
    # https://ncclient.readthedocs.io/en/latest/manager.html#filter-params
    # filter should be a tuple of (type, criteria)
    if kwargs.get("filter"):
        if isinstance(kwargs["filter"], list):
            kwargs["filter"] = tuple(kwargs["filter"])
        elif isinstance(kwargs["filter"], str):
            kwargs["filter"] = tuple([kwargs.pop("ftype", "subtree"), kwargs["filter"]])

    # get Ncclient NETCONF connection object
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    # add generic RPC operation to Ncclient manager object to support RPC call
    manager._vendor_operations.setdefault("rpc", GenericRPC)

    log.debug(
        "nornir_salt:ncclient_call calling '{}' with args: '{}'; kwargs: '{}'".format(
            call, args, kwargs
        )
    )

    # check if need to call one of helper function
    if "_call_{}".format(call) in globals():
        result, failed = globals()["_call_{}".format(call)](manager, *args, **kwargs)
    # call manager object method otherwise
    else:
        result = getattr(manager, call)(*args, **kwargs)

    # format results
    if hasattr(result, "_root"):
        result = etree.tostring(result._root, pretty_print=True).decode()
    elif isinstance(result, (list, dict, bool)):
        pass
    else:
        result = str(result)

    return Result(host=task.host, result=result, failed=failed)
