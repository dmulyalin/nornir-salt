"""
ResultSerializer
################

Helper function to transform Nornir results object in python dictionary to
ease programmatic consumption or further transformation in other formats 
such as JSON or YAML

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

If ``add_details`` is False returns dictionary::

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
              
If ``add_details`` is True returns dictionary with additional details::

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
                                          
ResultSerializer reference
==========================

.. autofunction:: nornir_salt.plugins.functions.ResultSerializer.ResultSerializer
"""

# list of known group tasks to skip them
skip_tasks = [
    "netmiko_send_commands"
]

def ResultSerializer(nr_results, add_details=False):
    """    
    :param nr_results: Nornir AggregatedResult results object
    :param add_details: boolean to indicate if results should contain more info, default
        is False
    """
    ret = {}
    for hostname, results in nr_results.items():
        ret[hostname] = {}
        for i in results:
            # skip group tasks such as _task_foo_bar
            if i.name.startswith("_"):
                continue
            # skip known group tasks as they do not contain results
            elif i.name in skip_tasks:
                continue
            # handle errors info passed from within tasks
            elif i.host.get("exception"):
                ret[hostname][i.name] = {"exception": i.host["exception"]}
            # add results details if requested to do so
            elif add_details:
                ret[hostname][i.name] = {
                    "diff": i.diff,
                    "changed": i.changed,
                    "result": i.result,
                    "failed": True if i.exception else i.failed,
                    "exception": str(i.exception),
                }
            # form results for the rest of tasks
            else:
                ret[hostname][i.name] = i.result
    return ret