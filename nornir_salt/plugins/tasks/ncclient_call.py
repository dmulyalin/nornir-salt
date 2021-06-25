"""
ncclient_call
#############

Ncclient is a popular library to interract with devices using NETCONF, this
plugin is a wrapper around ncclient connection manager object.

NETCONF protocol has a specific set of RPC calls available for use, rather
than coding separate task for each of them, ``ncclient_call`` made to execute
any arbitrary method supported by manager object plus a set of additional
helper methods to extend Ncclient library functionality.

ncclient_call sample usage
==========================

Sample code to run ``ncclient_call`` task::

    TBD


ncclient_call returns
=====================

Returns XML text string by default, but can return XML data transformed
in JSON, YAML or Python format.

ncclient_call reference
=======================

.. autofunction:: nornir_salt.plugins.tasks.ncclient_call.ncclient_call

additional methods reference
============================

dir
---
.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_dir

help
----
.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_help

server_capabilities
-------------------

.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_server_capabilities

connected
---------

.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_connected

locked
------

.. autofunction:: nornir_salt.plugins.tasks.ncclient_call._call_locked
"""
import traceback
import lxml.etree as etree
import logging
import json
import pprint

from nornir.core.task import Result, Task
from nornir_salt.plugins.connections.NcclientPlugin import CONNECTION_NAME
from ncclient.manager import OPERATIONS
from ncclient.operations.errors import MissingCapabilityError

log = logging.getLogger(__name__)

try:
    import xmltodict

    HAS_XMLTODICT = True
except ImportError:
    log.warning(
        "nornir_salt:ncclient_call failed to import xmltodict library, install it: pip install xmltodict"
    )
    HAS_XMLTODICT = False

try:
    import yaml

    HAS_YAML = True
except ImportError:
    log.warning(
        "nornir_salt:ncclient_call failed to import yaml library, install it: pip install pyyaml"
    )
    HAS_YAML = False

try:
    # this import should work for ncclient >=0.6.10
    from ncclient.operations import GenericRPC

except ImportError:
    # for ncclient<0.6.10 need to reconstruct GenericRPC class
    from ncclient.operations import RPC

    class GenericRPC(RPC):
        def request(self, data, *args, **kwargs):
            """
            :param data: (str) rpc xml string

            Testing:

            * Arista cEOS - not working, transport session closed error
            * Cisco IOS XR - working
            """
            ele = etree.fromstring(data.encode("UTF-8"))
            return self._request(ele)


def _call_locked(manager, *args, **kwargs):
    """
    Module: nornir_salt
    Task plugin: ncclient_call
    Plugin function: locked

    Helper function to run this edit-config flow:

    1. Lock target configuration/datastore
    2. Discard previous changes if any
    3. Run edit config
    4. Validate new confiugration if server supports it
    5. Run commit confirmed if server supports it
    6. Run final commit
    7. Unlock target configuration/datastore

    If any of steps 3, 4, 5, 6 fails, all changes discarded

    :param target: (str) name of datastore to edit configuration for
    :param config: (str) configuration to apply
    :param format: (str) configuration format, default is xml
    :returns result: (list) list of steps performed with details
    :returns failed: (bool) status indicator if change failed
    """
    pid = "dob04041989"
    result = []
    failed = False
    with manager.locked(target=kwargs["target"]):
        r = manager.discard_changes()
        result.append({"discard_changes": etree.tostring(r._root, pretty_print=True)})
        try:
            r = manager.edit_config(
                config=kwargs["config"],
                target=kwargs["target"],
                format=kwargs.get("format", "xml"),
            )
            result.append({"edit_config": etree.tostring(r._root, pretty_print=True)})
            # validate configuration
            try:
                r = manager.validate(source=kwargs["target"])
                result.append({"validate": etree.tostring(r._root, pretty_print=True)})
            except MissingCapabilityError:
                result.append({"validate": "MissingCapabilityError"})
                pass
            # run commit confirmed
            try:
                if kwargs.get("confirmed", True):
                    r = manager.commit(
                        confirmed=True, timeout=kwargs.get("timeout", "60"), persist=pid
                    )
                    result.append(
                        {"commit_confirmed": etree.tostring(r._root, pretty_print=True)}
                    )
                    # Could cancel but have to think about rollback criteria
                    # res = manager.cancel_commit(persist_id=pid)
            except MissingCapabilityError:
                result.append({"commit_confirmed": "MissingCapabilityError"})
                pass
            # do final commit
            r = manager.commit()
            result.append({"commit": etree.tostring(r._root, pretty_print=True)})
        except:
            tb = traceback.format_exc()
            log.error(
                "nornir_salt:ncclient_call locked edit_config call error: {}".format(tb)
            )
            result.append({"error": tb})
            failed = True
            # discard changes
            r = manager.discard_changes()
            result.append(
                {"discard_changes": etree.tostring(r._root, pretty_print=True)}
            )

    return result, failed


def _call_server_capabilities(manager, *args, **kwargs):
    """ Helper function to get server capabilities """
    return [c for c in manager.server_capabilities], False


def _call_connected(manager, *args, **kwargs):
    """ Helper function to get connected status """
    return manager.connected, False


def _call_dir(manager, *args, **kwargs):
    """ Function to return alist of available methods/operations """
    methods = (
        list(dir(manager))
        + list(manager._vendor_operations.keys())
        + list(OPERATIONS.keys())
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
    method_name = kwargs["method_name"]
    if "_call_{}".format(method_name) in globals():
        function_obj = globals()["_call_{}".format(method_name)]
    else:
        function_obj = getattr(manager, method_name)
    h = function_obj.__doc__ if hasattr(function_obj, "__doc__") else ""
    return h, False


def ncclient_call(task: Task, call: str, fmt: str = "xml", *args, **kwargs) -> Result:
    """
    Task to handle a call of NCClient manager object methods

    :param call: (str) ncclient manager object method to call
    :param fmt: (str) result formatter to use - xml (default), raw_xml, json, yaml, pprint, py
    :param *arg: (list) any arguments to use with call method
    :param **kwargs: (dict) any keyword arguments to use with call method
    """
    log.debug(
        "nornir_salt:ncclient_call calling '{}' with args: '{}'; kwargs: '{}'".format(
            call, args, kwargs
        )
    )
    failed = False
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    # add generic RPC operation
    manager._vendor_operations.update(rpc=GenericRPC)

    # check if need to call one of helper function
    if "_call_{}".format(call) in globals():
        result, failed = globals()["_call_{}".format(call)](manager, *args, **kwargs)
    # call manager object method
    else:
        result = getattr(manager, call)(*args, **kwargs)

    # format results
    if hasattr(result, "_root"):
        if fmt == "xml":
            result = etree.tostring(result._root, pretty_print=True).decode()
        elif fmt == "raw_xml":
            result = etree.tostring(result._root, pretty_print=False).decode()
        elif fmt == "json" and HAS_XMLTODICT:
            parsed_data = xmltodict.parse(etree.tostring(result._root))
            result = json.dumps(parsed_data, sort_keys=True, indent=4)
        elif fmt == "yaml" and HAS_XMLTODICT and HAS_YAML:
            parsed_data = xmltodict.parse(etree.tostring(result._root))
            result = yaml.dump(parsed_data, default_flow_style=False)
        elif fmt == "pprint" and HAS_XMLTODICT:
            parsed_data = xmltodict.parse(etree.tostring(result._root))
            result = pprint.pformat(parsed_data, indent=4)
        elif fmt == "py" and HAS_XMLTODICT:
            result = xmltodict.parse(etree.tostring(result._root))
        else:
            result = etree.tostring(result._root, pretty_print=True).decode()
    elif isinstance(result, (list, dict, bool)):
        pass
    else:
        result = str(result)

    return Result(host=task.host, result=result, failed=failed)
