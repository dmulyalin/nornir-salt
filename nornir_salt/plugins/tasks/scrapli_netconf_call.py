import logging
import json
import pprint
import traceback
from nornir.core.task import Result, Task

log = logging.getLogger(__name__)

try:
    import xmltodict

    HAS_XMLTODICT = True
except ImportError:
    log.warning("nornir_salt:scrapli_netconf_call failed to import xmltodict library, install it: pip install xmltodict")
    HAS_XMLTODICT = False

try:
    import yaml

    HAS_YAML = True
except ImportError:
    log.warning("nornir_salt:scrapli_netconf_call failed to import yaml library, install it: pip install pyyaml")
    HAS_YAML = False


def _call_dir(conn, *args, **kwargs):
    """ Helper function to return a list of supported tasks """
    methods = [
        m for m in dir(conn)
        if not m.startswith("_")
    ] + ["dir", "connected", "locked"]
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
    """ Helper function to return connection status """
    return conn.isalive(), False

def _call_locked(conn, *args, **kwargs):
    """
    Module: nornir_salt
    Task plugin: scrapli_netconf_call
    Plugin function: locked

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
        r = conn.edit_config(
            config=kwargs["config"],
            target=kwargs["target"]
        )
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
    """ Helper function to return server capabilities """
    return conn.server_capabilities, False


def scrapli_netconf_call(task: Task, call: str, fmt: str = "xml", *args, **kwargs) -> Result:
    """
    Discpatcher function to call one of the supported scrapli_netconf methods
    or one of helper functions.
    """
    log.debug("nornir_salt:scrapli_netconf_call calling '{}' with args: '{}'; kwargs: '{}'".format(
            call, args, kwargs
        )
    )
    result = None
    failed = False

    conn = task.host.get_connection("scrapli_netconf", task.nornir.config)

    # check if need to call one of helper function
    if "_call_{}".format(call) in globals():
        result, failed = globals()["_call_{}".format(call)](conn, *args, **kwargs)
    # call conn object method
    else:
        result = getattr(conn, call)(*args, **kwargs)

    # format results
    if hasattr(result, "result"):
        if fmt == "xml":
            result = result.result
        elif fmt == "raw_xml":
            result = result.result
        elif fmt == "json" and HAS_XMLTODICT:
            parsed_data = xmltodict.parse(result.result)
            result = json.dumps(parsed_data, sort_keys=True, indent=4)
        elif fmt == "yaml" and HAS_XMLTODICT and HAS_YAML:
            parsed_data = xmltodict.parse(result.result)
            result = yaml.dump(parsed_data, default_flow_style=False)
        elif fmt == "pprint" and HAS_XMLTODICT:
            parsed_data = xmltodict.parse(result.result)
            result = pprint.pformat(parsed_data, indent=4)
        elif fmt == "py" and HAS_XMLTODICT:
            result = xmltodict.parse(result.result)
        else:
            result = etree.tostring(result._root, pretty_print=True).decode()
    elif isinstance(result, (list, dict, bool)):
        pass
    else:
        result = str(result)

    return Result(host=task.host, result=result, failed=failed)