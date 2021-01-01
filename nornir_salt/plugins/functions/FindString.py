from typing import Dict
from collections import deque
import re

def FindString(nr_results: Dict, pattern: str, before: int = 0):
    """
    Function to search for regex pattern in hosts' output.

    :param nr_results: Dictionary produced by ResultSerializer function.
    :param pattern: regular expression pattern to search for
    :param before: number of lines before match to include in results

    Returns updated results dictionary, where results field contains
    only lines matched by pattern.
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