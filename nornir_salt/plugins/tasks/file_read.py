"""
file_read
#########

Function to read text files content saved by ``ToFileProcessor``.

This task reconstructs previously saved results and returns Nornir
Result objects.

file_read sample usage
======================

Code to invoke ``file_read`` task::

    TBD

file_read returns
=================

Returns content of previously saved tasks.

file_read reference
=================

.. autofunction:: nornir_salt.plugins.tasks.file_read.file_read
"""
import os
import json

from nornir.core.task import Result

def _read_content(task, task_name:str, task_details:dict, data:str, timestamp:str) -> None:
    """
    Helper function to re-use code. Gets subset of task results from 
    overall data and adds it to task.results
    
    :param task: (obj) Nornir task object
    :param task_name: (str) Name of the task to process
    :param task_details: (dict) details of task from ToFileProcessor index file
    :param data: (str) content of file with previous results
    :returns: None
    """
    start, end = task_details["span"]
    # "end - 1" to account for ToFileProcessor adds "+\n" to the end 
    content = data[start:end-1]
    if task_details["content_type"] == "json":
        content = json.loads(content)
    task.results.append(
        Result(
            host=task.host, 
            result=content, 
            name=task_name,
            timestamp=timestamp
        )
    )
        
def file_read(
    task,
    filename: [str, list],
    base_url: str = "/var/nornir-salt/",
    task_name: str = None,
    last: int = 1,
    index:str = "common",
):
    """
    Read content of files saved by ``ToFileProcessor``

    :param filename: (str or list) alias name or list of alias names of the files to load
    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"    
    :param last: (int) what file to read, default is 1 - the most current one
    :param task_name: (str) name of task to read previous results for, returns all results
        if ``task_name`` is empty.
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Result object with file read content
    """
    # load aliases data
    aliases_file = os.path.join(base_url, "tf_index_{}.json".format(index))
    with open(aliases_file, mode="r", encoding="utf-8") as f:
        aliases_data = json.loads(f.read())
    
    filenames = [filename] if isinstance(filename, str) else filename
    
    for file_name in filenames:
        # do sanity check
        if file_name not in aliases_data:
            task.results.append(
                Result(
                    host=task.host, 
                    result=None, 
                    exception="nornir-salt:file_read '{}' files not found" .format(file_name)
                )
            )
            continue
        
        # get previous results metadata
        res_index = min(last - 1, len(aliases_data[file_name][task.host.name]) - 1)
        prev_res_details = aliases_data[file_name][task.host.name][res_index]
        timestamp = prev_res_details["timestamp"]
        
        # load file content
        with open(prev_res_details["filename"], mode="r", encoding="utf-8") as f:
            data = f.read()
                
        # check if need to load results for certain task only
        if task_name:
            task_details = prev_res_details["tasks"][task_name]
            _read_content(task, task_name, task_details, data, timestamp)
        # load content of all tasks reconstructing them in Nornir result objects
        else:
            for _task_name, task_details in prev_res_details["tasks"].items():
                _read_content(task, _task_name, task_details, data, timestamp)
            
    return Result(host=task.host, skip_results=True)
