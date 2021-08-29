"""
Nornir Files Task Plugin
########################

Collection of task plugins to work with files saved by ``TofileProcessor``.

Sample usage
============

Code to invoke ``files`` task plugins::

    TBD

API reference
=============

.. autofunction:: nornir_salt.plugins.tasks.files.file_read
.. autofunction:: nornir_salt.plugins.tasks.files.file_list
.. autofunction:: nornir_salt.plugins.tasks.files.file_remove
.. autofunction:: nornir_salt.plugins.tasks.files.file_find
"""
import os
import json

from nornir.core.task import Result

def _read_content(task, task_name:str, task_details:dict, data:str, timestamp:str, group:str) -> None:
    """
    Helper function to re-use code. Gets subset of task results from 
    overall data and adds it to task.results
    
    :param task: (obj) Nornir task object
    :param task_name: (str) Name of the task to process
    :param task_details: (dict) details of task from ToFileProcessor index file
    :param data: (str) content of file with previous results
    :param group: (str) ``tf`` files group name
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
            timestamp=timestamp,
            filegroup=group,
        )
    )
       
def _load_index_data(base_url, index):
    """
    Helper function to load json index file and return python dictionary.
    
    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"       
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Dictionary of index data
    """
    index_file = os.path.join(base_url, "tf_index_{}.json".format(index))
    with open(index_file, mode="r", encoding="utf-8") as f:
        index_data = json.loads(f.read())
    return index_data
        
        
def file_read(
    task,
    filegroup: [str, list],
    base_url: str = "/var/nornir-salt/",
    task_name: str = None,
    last: int = 1,
    index:str = "common",
):
    """
    Function to read text files content saved by ``ToFileProcessor``.
    
    This task reconstructs previously saved results and returns Nornir
    Result objects.

    :param filegroup: (str or list) ``tf`` group or list of ``tf`` file group names of files to load
    :param base_url: (str) OS path to folder with saved files, default "/var/nornir-salt/"  
    :param last: (int) what file to read, default is 1 - the most current one
    :param task_name: (str) name of task to read previous results for, returns all results
        if ``task_name`` is empty.
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Result object with file read content
    """
    # load index data
    index_data = _load_index_data(base_url, index)
    
    filegrous = [filegroup] if isinstance(filegroup, str) else filegroup
    
    for group in filegrous:
        # do sanity check
        if group not in index_data:
            task.results.append(
                Result(
                    host=task.host, 
                    result=None, 
                    exception="nornir-salt:file_read '{}' files not found" .format(group)
                )
            )
            continue
        
        # get previous results metadata
        res_index = min(last - 1, len(index_data[group][task.host.name]) - 1)
        prev_res_details = index_data[group][task.host.name][res_index]
        timestamp = prev_res_details["timestamp"]
        
        # load file content
        with open(prev_res_details["filename"], mode="r", encoding="utf-8") as f:
            data = f.read()
                
        # check if need to load results for certain task only
        if task_name:
            task_details = prev_res_details["tasks"][task_name]
            _read_content(task, task_name, task_details, data, timestamp, group)
        # load content of all tasks reconstructing them in Nornir result objects
        else:
            for _task_name, task_details in prev_res_details["tasks"].items():
                _read_content(task, _task_name, task_details, data, timestamp, group)
            
    return Result(host=task.host, skip_results=True)


def file_list(
    task,
    filegroup: [str, list] = [],
    base_url: str = "/var/nornir-salt/",
    index:str = "common",
):
    """
    Function to produce a list of text files saved by ``ToFileProcessor``

    :param filegroup: (str or list) ``tf`` group or list of ``tf`` file group names of files to list
    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"    
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Nornir Result object with files list
    """
    ret = []
    
    # load index data
    index_data = _load_index_data(base_url, index)
    
    filegroups = [filegroup] if isinstance(filegroup, str) else filegroup
    filegroups = filegroups if filegroups else list(index_data.keys())
    
    for group in filegroups:
        # do sanity check
        if group not in index_data:
            task.results.append(
                Result(
                    host=task.host, 
                    result=None, 
                    exception="nornir-salt:file_list '{}' files group not found" .format(group)
                )
            )
            continue
        
        # iterate over previous results
        for index, file_details in enumerate(index_data[group].get(task.host.name, [])):
            tasks = file_details.pop("tasks")
            ret.append(
                {
                    "host": task.host.name,
                    "filegroup": group,
                    "last": index + 1,
                    "tasks": "\n".join(list(tasks.keys())),
                    **file_details,
                }
            )
            
    return Result(host=task.host, result=ret)
    
    
def file_remove(
    task,
    filegroup: [str, list] = None,
    base_url: str = "/var/nornir-salt/",
    index:str = "common",
):
    """
    Function to remove files saved by ``ToFileProcessor`` 
    
    :param filegroup: (str or list) ``tf`` group or list of ``tf`` file group names of files 
        to remove, by default removes all filegroups.
    :param base_url: (str) OS path to folder with saved files, default "/var/nornir-salt/"    
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Result object with removed files summary
    """
    ret = []
    
    # load index data
    index_data = _load_index_data(base_url, index)
    
    filegroups = filegroup if isinstance(filegroup, list) else [filegroup]
    filegroups = filegroups if all(filegroups) else list(index_data.keys())

    for group in filegroups:
        # do sanity check
        if group not in index_data:
            task.results.append(
                Result(
                    host=task.host, 
                    result=None, 
                    exception="nornir-salt:file_remove '{}' files group not found" .format(group)
                )
            )
            continue
        
        # iterate over previous results
        for file_details in index_data[group][task.host.name]:
            filename = file_details["filename"]
            tasks = file_details.pop("tasks")
            if os.path.exists(filename):
                os.remove(filename)
                ret.append(
                    {
                        "host": task.host.name,
                        "filegroup": group,
                        "tasks": "\n".join(list(tasks.keys())),
                        **file_details,
                    }
                )
                
        # clean up index data
        _ = index_data[group].pop(task.host.name)

    # save new index data
    index_file = os.path.join(base_url, "tf_index_{}.json".format(index))
    with open(index_file, mode="w", encoding="utf-8") as f:
       f.write(json.dumps(index_data, sort_keys=True, indent=4, separators=(",", ": ")))
        
    return Result(host=task.host, result=ret) 
