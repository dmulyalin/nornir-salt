"""
ResultSerializer
################

Helper function to transform Nornir results object in python dictionary to
ease programmatic consumption or further transformation in other formats
such as JSON or YAML

ResultSerializer supports serialization of results of these object types::

    list, tuple, dict, str, int, bool, set, type(None)

If task result is not one of above types, it is converted to string.

Exception object transformed to string.

ResultSerializer Sample Usage
=============================

Code to demonstrate how to invoke ResultSerializer::

    from nornir import InitNornir
    from nornir_netmiko import netmiko_send_command
    from nornir_salt.plugins.functions import ResultSerializer

    nr = InitNornir(config_file="config.yaml")

    result = NornirObj.run(
        task=netmiko_send_command,
        command_string="show clock"
    )

    result_dictionary = ResultSerializer(result, add_details=True)

    # work further with result_dictionary
    # ...

ResultSerializer returns
========================

ResultSerializer capable of returning two different structures, each one
can contain additional task details. The difference between structures is
in the way how tasks are represented.

First structure uses dictionary keyed by task name, where values are
task's results.

Second structure type uses list to store task results.

If ``add_details`` is False and ``to_dict`` is True returns dictionary::

    {
        "hostname_1": {
            "task_name_1": result,
            "task_name_2": result
        },
        "hostname_2": {
            "task_name_1": result,
            "task_name_2": result
        }
    }

For instance::

    {'IOL1': {'show clock': '*00:55:21.236 EET Tue Feb 9 2021',
               'show run | inc hostname': 'hostname IOL1'},
     'IOL2': {'show clock': '*00:55:21.234 EET Tue Feb 9 2021',
               'show run | inc hostname': 'hostname IOL2'}}

If ``add_details`` is True and ``to_dict`` is True returns dictionary
with additional details::

    {
        "hostname_1": {
            "task_name_1": {
                "changed": False,
                "diff: "",
                "exception": None,
                "failed": False,
                "result": "result string"
            },
            "task_name_2": {
                "changed": False,
                "diff: "",
                "exception": None,
                "failed": False,
                "result": "result string"
            }
        },
        "hostname_2": {
            "task_name_1": {
                "changed": False,
                "diff}: "",
                "exception": None,
                "failed": False,
                "result": "result string"
            }
        }
    }

For example::

    {'IOL1': {'show clock': {'changed': False,
                             'diff': '',
                             'exception': 'None',
                             'failed': False,
                             'result': '*00:57:45.398 EET Tue Feb 9 2021'},
              'show run | inc hostname': {'changed': False,
                                          'diff': '',
                                          'exception': 'None',
                                          'failed': False,
                                          'result': 'hostname IOL1'}},
     'IOL2': {'show clock': {'changed': False,
                             'diff': '',
                             'exception': 'None',
                             'failed': False,
                             'result': '*00:57:45.489 EET Tue Feb 9 2021'},
              'show run | inc hostname': {'changed': False,
                                          'diff': '',
                                          'exception': 'None',
                                          'failed': False,
                                          'result': 'hostname IOL2'}}}

If ``add_details`` is False and ``to_dict`` is False returns dictionary::

    {
        "hostname_1": [
            {"name": "task_name_1", "result": result},
            {"name": "task_name_2", "result": result}
        ],
        "hostname_2": [
            {"name": "task_name_1", "result": result},
            {"name": "task_name_2", "result": result}
        ]
    }

If ``add_details`` is True and ``to_dict`` is False returns dictionary::

    {
        "hostname_1": [
            {
                "name": "task_name_1",
                "changed": False,
                "diff: "",
                "exception": None,
                "failed": False,
                "result": "result string"
            },
            {
                "name": "task_name_2",
                "changed": False,
                "diff: "",
                "exception": None,
                "failed": False,
                "result": "result string"
            }
        ],
        "hostname_2": [
            {
                "name": "task_name_1",
                "changed": False,
                "diff: "",
                "exception": None,
                "failed": False,
                "result": "result string"
            }
        ]
    }

Skipping results
================

ResultSerializer by default skips all tasks with name starting with
underscore ``_``, in addition results skipped if ``Result`` object
contains ``skip_results`` attribute and it set to ``True``.

Above skip logic ignored if ``Result`` object exception is not empty.

ResultSerializer reference
==========================

.. autofunction:: nornir_salt.plugins.functions.ResultSerializer.ResultSerializer
"""
import logging
from nornir.core.task import AggregatedResult

log = logging.getLogger(__name__)

supported_types = [list, tuple, dict, str, int, bool, set, type(None)]


def ResultSerializer(nr_results, add_details=False, to_dict=True, skip=None):
    """
    :param nr_results: ``nornir.core.task.AggregatedResult`` object
    :param add_details: boolean to indicate if results should contain more info, default
        is False
    :param to_dict: (bool) default is True, forms nested dictionary structure, if False
        forms results in a list.
    :param skip: (list) list of Result object attributes names to omit, default is
        "severity_level", "stderr", "stdout", "host"
    """
    skip = skip or ["severity_level", "stderr", "stdout", "host"]
    # run check
    if not isinstance(nr_results, AggregatedResult):
        return nr_results

    # form nested dictionary structure
    if to_dict:
        ret = {}
        for hostname, results in nr_results.items():
            for i in results:
                exception = (
                    str(i.exception)
                    if i.exception is not None
                    else i.host.get("exception", None)
                )
                # skip tasks such as _task_foo_bar unless exception
                if i.name and i.name.startswith("_") and not exception:
                    continue
                # skip tasks if signaled to do so
                elif (
                    hasattr(i, "skip_results")
                    and i.skip_results is True
                    and not exception
                ):
                    continue
                # add hostname to results
                ret.setdefault(hostname, {})
                # add results details if requested to do so
                if add_details:
                    ret[hostname][i.name] = {
                        k: v
                        for k, v in vars(i).items()
                        if k not in skip and type(v) in supported_types
                    }
                    ret[hostname][i.name].setdefault("result", str(i.result))
                    ret[hostname][i.name]["failed"] = True if exception else i.failed
                    ret[hostname][i.name]["exception"] = exception
                    ret[hostname][i.name].pop("name")
                # form results for the rest of tasks
                else:
                    ret[hostname][i.name] = (
                        i.result if type(i.result) in supported_types else str(i.result)
                    )

    # form plain list of results
    else:
        ret = []
        for hostname, results in nr_results.items():
            for i in results:
                exception = (
                    str(i.exception)
                    if i.exception is not None
                    else i.host.get("exception", None)
                )
                # skip group tasks such as _task_foo_bar unless exception
                if i.name and i.name.startswith("_") and not exception:
                    continue
                # skip tasks if signalled to do so
                elif (
                    hasattr(i, "skip_results")
                    and i.skip_results is True
                    and not exception
                ):
                    continue
                # add results details if requested to do so
                elif add_details:
                    ret.append(
                        {
                            k: v
                            for k, v in vars(i).items()
                            if k not in skip and type(v) in supported_types
                        }
                    )
                    ret[-1].setdefault("result", str(i.result))
                    ret[-1]["failed"] = True if exception else i.failed
                    ret[-1]["exception"] = exception
                    ret[-1]["host"] = i.host.name
                # form results for the rest of tasks
                else:
                    ret.append(
                        {
                            "host": hostname,
                            "name": i.name,
                            "result": i.result
                            if type(i.result) in supported_types
                            else str(i.result),
                        }
                    )

    return ret
