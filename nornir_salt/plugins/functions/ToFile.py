"""
ToFile
######

Function to save provided data to file.

``tf`` attribute supports ``time.strftime`` directives, supports ``host_name``
directive as well, for example::

    /path/to/dir/output_%B_%d_%H_%M_%S.txt
    /path/to/dir/output_{host_name}-%B_%d_%H_%M_%S.txt
    /path/to/{host_name}/output_%B_%d_%H_%M_%S.txt

If ``{host_name}`` string present in ``tf`` attribute, results saved on
a per-host basis. Otherwise, results saved as is using provided ``tf_format``
formatter.

Supported ``tf_format`` values:

* ``raw`` - (default) converts data to string appending newline, does
  not do any formatting
* ``pprint`` - uses ``pprint.pformat`` function to format data to string
* ``json`` - formats data to JSON format
* ``yaml`` - formats data to YAML format

ToFile Sample Usage
===================

Code to demonstrate how to invoke ``ToFile`` function::

    from nornir import InitNornir
    from nornir_netmiko import netmiko_send_command
    from nornir_salt.plugins.functions import ResultSerializer, ToFile

    nr = InitNornir(config_file="config.yaml")

    result = NornirObj.run(
        task=netmiko_send_command,
        command_string="show run"
    )

    result_dictionary = ResultSerializer(result, add_details=True)

    # save to file
    ToFile(
        result_dictionary,
        tf="/tmp/31/{host_name}/cfg-%B_%d_%H_%M_%S.txt"
    )

ToFile returns
==============

ToFile function returns None

ToFile reference
================

.. autofunction:: nornir_salt.plugins.functions.ToFile.ToFile
"""
import logging
import time
import os
import json
import pprint

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------
# formatters helper functions
# --------------------------------------------------------------------------------


def _to_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(",", ": "))


def _to_pprint(data):
    return pprint.pformat(data, indent=4)


def _to_yaml(data):
    if HAS_YAML:
        return yaml.dump(data, default_flow_style=False)
    else:
        return _to_pprint(data)


def _to_raw(data):
    return str(data)


# formats dispatcher dictionary
formatters = {"raw": _to_raw, "json": _to_json, "pprint": _to_pprint, "yaml": _to_yaml}


# --------------------------------------------------------------------------------
# main ToFile function
# --------------------------------------------------------------------------------


def _write(f, data, tf_format):
    """
    Helper function mainly to re-use code
    """
    try:
        f.write(formatters[tf_format](data) + "\n")
    except KeyError:
        log.error(
            "ToFile, unsupported format '{}'; supported '{}'".format(
                tf_format.list(formatters.keys())
            )
        )


def ToFile(data, tf, tf_format="raw", **kwargs):
    """
    :param data: any arbitrary data to save in fail
    :param tf: str, OS path to file where to save output,
    :param tf_format: str, format to use e.g. yaml, json, pprint, default is raw

    If ``tf`` attribute contains ``{host_name}``, data saved on a per-host basis replacing
    ``{hos_name}`` with name of the host.
    """
    # save to file on a per-host, per-task basis
    if "{host_name}" in tf:
        for host_name, host_results in data.items():
            host_filename = time.strftime(tf).format(host_name=host_name)
            os.makedirs(os.path.dirname(host_filename), exist_ok=True)
            with open(host_filename, mode="w", encoding="utf-8") as f:
                for task_name, task_result in host_results.items():
                    if isinstance(task_result, dict) and "result" in task_result:
                        content = task_result["result"]
                    else:
                        content = str(task_result)
                    _write(f, content, tf_format)
    # dump whole data to file
    else:
        filename = time.strftime(tf)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, mode="w", encoding="utf-8") as f:
            _write(f, data, tf_format)
