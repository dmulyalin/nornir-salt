"""
puresnmp_call
#############

`puresnmp <https://github.com/exhuma/puresnmp>`_ is a library to interact with devices
using SNMP, this plugin is a wrapper around ``puresnmp`` pythonic client object.

puresnmp_call sample usage
==========================

Sample code to run ``puresnmp_call`` task::

    from nornir import InitNornir
    from nornir_salt.plugins.tasks import puresnmp_call

    nr = InitNornir(config_file="config.yaml")

    output = nr.run(
        task=puresnmp_call,
        call="get",
        oid="1.3.6.1.2.1.1.2.0"
    )

puresnmp_call returns
=====================

Returns puresnmp SNMP client call result.

puresnmp_call reference
=======================

.. autofunction:: nornir_salt.plugins.tasks.puresnmp_call.puresnmp_call

additional methods reference
============================

puresnmp_call - dir
-------------------
.. autofunction:: nornir_salt.plugins.tasks.puresnmp_call._call_dir

puresnmp_call - help
--------------------
.. autofunction:: nornir_salt.plugins.tasks.puresnmp_call._call_help
"""
import logging
import asyncio

from nornir.core.task import Result, Task
from nornir_salt.plugins.connections.PureSNMPPlugin import CONNECTION_NAME
from nornir_salt.utils.pydantic_models import model_puresnmp_call
from nornir_salt.utils.yangdantic import ValidateFuncArgs

try:
    from puresnmp.util import BulkResult
    from puresnmp.varbind import PyVarBind
    from typing import AsyncGenerator
    from x690.types import OctetString

    HAS_PURESNMP = True
except ImportError:
    HAS_PURESNMP = False

log = logging.getLogger(__name__)


def _make_value(value):
    """Helper function to process snmp operations result values"""
    if isinstance(value, (int, float)):
        return value
    elif isinstance(value, bytes):
        return value.decode(encoding="utf-8")
    return str(value)


def _form_result(result, kwargs):
    """Helper function to form snmp operation result"""
    res, oids = [], []

    # form results content
    if isinstance(result, bytes):
        res.append(result.decode(encoding="utf-8"))
    # result is a list for walk, table or multiget operations
    elif isinstance(result, list):
        for i in result:
            if isinstance(i, bytes):
                res.append(i.decode(encoding="utf-8"))
            # result is PyVarBind for walk operations
            elif isinstance(i, PyVarBind):
                res.append(_make_value(i.value))
                oids.append(i.oid)
            # value is a dict for table operations
            elif isinstance(i, dict):
                # form list of rows-lists
                res.append({k: _make_value(v) for k, v in i.items()})
            else:
                res.append(str(i))
    # result is BulkResult for bulkget operation
    elif isinstance(result, BulkResult):
        res = {
            "listing": {k.value: _make_value(v) for k, v in result.listing.items()},
            "scalars": {k.value: _make_value(v) for k, v in result.scalars.items()},
        }
    # result is PyVarBind for getnext operation
    elif isinstance(result, PyVarBind):
        res.append(_make_value(result.value))
        oids.append(result.oid)
    # multiset operation returns dictionary
    elif isinstance(result, dict):
        res = {k: _make_value(v) for k, v in result.items()}
    else:
        res.append(str(result))

    # form oids list if still empty
    if not oids:
        if "oid" in kwargs:
            oids = [kwargs["oid"]]
        elif "oids" in kwargs:
            oids = kwargs["oids"]

    # res is a list for walk and multix nmethods
    if isinstance(res, list):
        if len(oids) == len(res):
            return {"result": dict(zip(oids, res))}
        # len(oids) != len(res) and only one oid when snmp method is table
        elif len(oids) == 1:
            return {"result": {oids[0]: res}}
        else:
            return {"result": res}
    else:
        return {"result": res}


def _call_dir(client, *args, **kwargs):
    """Function to return a list of available methods"""
    methods = list(dir(client)) + ["dir", "help"]
    return sorted([m for m in set(methods) if not m.startswith("_")])


def _call_help(client, method_name, *args, **kwargs):
    """
    Helper function to return docstring for requested method

    :param method_name: (str) name of method or function to return docstring for
    """
    if f"_call_{method_name}" in globals():
        function_obj = globals()[f"_call_{method_name}"]
    else:
        function_obj = getattr(client, method_name)
    h = function_obj.__doc__ if hasattr(function_obj, "__doc__") else ""
    return h


@ValidateFuncArgs(model_puresnmp_call)
def puresnmp_call(task: Task, call: str, *args, **kwargs) -> Result:
    """
    Task to handle a call of puresnmp client object methods. This task
    attempts to normalize results produced by puresnmp library to a
    dictionary keyed by oid names with their values.

    :param call: (str) puresnmp client object method to call
    :param args: (list) any ``*args`` to use with call method
    :param kwargs: (dict) any ``**kwargs`` to use with call method
    """
    task.name = call

    # get PureSNMP connection object
    client = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    log.debug(
        f"nornir_salt:puresnmp_call calling '{call}' with args: '{args}'; kwargs: '{kwargs}'"
    )

    # check if oid(s) provided in host data
    if "oids" in task.host.data.get("__task__", {}):
        kwargs["oids"] = task.host.data["__task__"]["oids"]
    elif "oid" in task.host.data.get("__task__", {}):
        kwargs["oid"] = task.host.data["__task__"]["oid"]

    # preprocess set operation values
    if call == "set":
        kwargs["value"] = OctetString(str(kwargs["value"]).encode(encoding="utf-8"))
    elif call == "multiset":
        kwargs["mappings"] = {
            k: OctetString(str(v).encode(encoding="utf-8"))
            for k, v in kwargs["mappings"].items()
        }

    # check if need to call one of helper functions
    if "_call_{}".format(call) in globals():
        result = globals()[f"_call_{call}"](client, *args, **kwargs)

        return Result(host=task.host, result=result)
    # call client object method otherwise
    else:
        result = getattr(client, call)(*args, **kwargs)
        if isinstance(result, AsyncGenerator):

            # helper function to obtain results from AsyncGenerator
            # returned by puresnmp walk methods
            async def _run_gen():
                output = []
                async for row in result:
                    output.append(row)
                return output

            result = asyncio.run(_run_gen())
        else:
            result = asyncio.run(result)

        return Result(host=task.host, **_form_result(result, kwargs))
