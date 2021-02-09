"""
FindString
##########

Function to search for regex pattern in hosts' output, similar to network devices include/match pipe statements.

FindString Sample Usage
=======================

Example invoking FindString function::

    import pprint
    from nornir import InitNornir
    from nornir_netmiko import netmiko_send_command
    from nornir_salt.plugins.functions import ResultSerializer, FindString
    
    nr = InitNornir(config_file="config.yaml")
    
    result = NornirObj.run(
        task=netmiko_send_command,
        command_string="show run"
    )
    
    result_dictionary = ResultSerializer(result)
    
    filtered_result = FindString(result_dictionary, pattern="interface \S+")
    
    pprint.pprint(filtered_result)
    
    # prints:
    #
    # {'IOL1': {'show run': 'interface Loopback0\\n'
    #                       'interface Loopback100\\n'
    #                       'interface Ethernet0/0\\n'
    #                       'interface Ethernet0/0.102\\n'
    #                       'interface Ethernet0/0.107\\n'
    #                       'interface Ethernet0/0.2000\\n'
    #                       'interface Ethernet0/1\\n'
    #                       'interface Ethernet0/2\\n'
    #                       'interface Ethernet0/3'},
    #  'IOL2': {'show run': 'interface Loopback0\\n'
    #                       'interface Ethernet0/0\\n'
    #                       'interface Ethernet0/0.27\\n'
    #                       'interface Ethernet0/0.37\\n'
    #                       'interface Ethernet0/0.107\\n'
    #                       'interface Ethernet0/0.117\\n'
    #                       'interface Ethernet0/0.2000\\n'
    #                       'interface Ethernet0/1\\n'
    #                       'interface Ethernet0/2\\n'
    #                       'interface Ethernet0/3'}}

FindString returns
==================

Returns updated ResultSerializer dictionary, where result fields contains
only lines matched by pattern.

FindString reference
====================

.. autofunction:: nornir_salt.plugins.functions.FindString.FindString
"""

from typing import Dict
from collections import deque
import re

def FindString(nr_results: Dict, pattern: str, before: int = 0):
    """
    :param nr_results: Dictionary produced by ResultSerializer function.
    :param pattern: regular expression pattern to search for
    :param before: number of lines before match to include in results
    """
    regex = re.compile(str(pattern))

    # iterate over results and search for matches
    for hostname, results in nr_results.items():
        for task, result in results.items():
            searched_result = []
            lines_before = deque([], abs(before))
            data_to_search = None

            # get data to search in
            if isinstance(result, dict) and "result" in result:
                data_to_search = result["result"]
            elif isinstance(result, str):
                data_to_search = result

            # search for pattern in lines
            for line in iter(data_to_search.splitlines()):
                if regex.search(line):
                    searched_result.append(
                        line if before == 0 else "--\n{}\n{}".format("\n".join(lines_before), line)
                    )
                lines_before.append(line)

            # add searched result in task result
            if isinstance(result, dict) and "result" in result:
                nr_results[hostname][task]["result"] = "\n".join(searched_result)
            elif isinstance(result, str):
                nr_results[hostname][task] = "\n".join(searched_result)

    return nr_results