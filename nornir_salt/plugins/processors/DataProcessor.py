"""
DataProcessor Plugin
####################

Processor plugin to process structured results data obtained from devices

DataProcessor Sample Usage
==========================

Code to demonstrate how to use ``DataProcessor`` plugin::

    from nornir import InitNornir
    from nornir_netmiko import netmiko_send_command
    from nornir_salt import DataProcessor

    nr = InitNornir(config_file="config.yaml")

    nr_with_processor = nr.with_processors([
        DataProcessor(
            [
                "flatten",
                "filter": "*isis*",
                "unflatten",
                "to_json"
            ]
        )
    ])

    nr_with_processor.run(
        task=netmiko_send_command,
        command_string="show run"
    )

DataProcessor Functions reference
=================================

.. autofunction:: nornir_salt.plugins.processors.DataProcessor.to_str
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.to_json
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.to_pprint
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.to_yaml
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.load_xml
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.load_json
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.flatten
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.unflatten
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xpath
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.key_filter
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.match
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.flake
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xml_flake
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xml_to_json
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xml_flatten
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.parse_ttp

DataProcessor reference
=======================

.. autofunction:: nornir_salt.plugins.processors.DataProcessor.DataProcessor
"""
import logging
import os
import json
import pprint
import traceback
import re

from fnmatch import fnmatchcase
from collections import deque
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

log = logging.getLogger(__name__)

try:
    import yaml

    HAS_YAML = True
except ImportError:
    log.warning(
        "nornir_salt:DataProcessor failed import YAML library, install: pip install pyyaml"
    )
    HAS_YAML = False

try:
    import xmltodict

    HAS_XMLTODICT = True
except ImportError:
    log.warning(
        "nornir_salt:DataProcessor failed import xmltodict library, install: pip install xmltodict"
    )
    HAS_XMLTODICT = False
 
try:
    from lxml import etree

    HAS_LXML = True
except ImportError:
    log.warning(
        "nornir_salt:DataProcessor failed import LXML library, install: pip install lxml"
    )
    HAS_LXML = False

try:
    from ttp import ttp

    HAS_TTP = True
except ImportError:
    log.error("nornir_salt:DataProcessor failed import TTP library, install: pip install ttp")
    HAS_TTP = False


# --------------------------------------------------------------------------------
# formatters functions: transform structured data to json, yaml etc. text
# --------------------------------------------------------------------------------


def to_str(data, **kwargs):
    """
    Reference Name ``to_str``
    
    Function to transform Python structure to string without applying any formatting
    
    :param data: (structure) Python structure to transform
    :param kwargs: (dict) ignored
    :return: string
    """
    return str(data)

    
def to_json(data, **kwargs):
    """
    Reference Name ``to_json``
    
    Function to transform Python structure to JSON formatted string.
    
    :param data: (structure) Python structure to transform
    :param kwargs: (dict) additional kwargs for ``json.dumps`` method
    :return: JSON formatted string
    """
    kwargs = {"sort_keys": True, "indent": 4, "separators": (",", ": "), **kwargs}
    return json.dumps(data, **kwargs)


def to_pprint(data, **kwargs):
    """
    Reference Name ``to_pprint``
    
    Function to transform Python structure to pretty print string using
    ``pprint`` module
    
    :param data: (structure) Python structure to transform
    :param kwargs: (dict) additional kwargs for ``pprint.pformat`` method
    :return: pretty print formatted string
    """
    kwargs = {"indent": 4, **kwargs}
    return pprint.pformat(data, **kwargs)


def to_yaml(data, **kwargs):
    """
    Reference Name ``to_yaml``
    
    Function to transform Python structure to YAML formatted string
    
    Dependencies: requires PyYAML library - ``pip install pyyaml``
    
    :param data: (structure) Python structure to transform
    :param kwargs: (dict) additional kwargs for ``yaml.dump`` method
    :return: pretty print formatted string
    """
    kwargs = {"default_flow_style": False, **kwargs}
    if HAS_YAML:
        return yaml.dump(data, **kwargs)
    else:
        return to_pprint(data)
    

# --------------------------------------------------------------------------------
# loader functions: load json, yaml etc. text into python structured data
# --------------------------------------------------------------------------------


def load_xml(data, py_dict=True, **kwargs):
    """
    Load XML string into python dictionary structure using xmltodict library.
    
    Dependencies: requires LXML library - ``pip install lxml``
    
    :param data: (str) XML formatted string
    :param py_dict: (bool) if True (default), will transform structure returned
      by ``xmltodict`` to normal dictionary instead of ``OrderedDict``
    :param kwargs: (dict) any additional ``**kwargs`` for ``xmltodict.parse`` method 
    :returns: python dictionary 
    """
    parsed = xmltodict.parse(data, **kwargs)
    # pass parsed results through json to get rid of ordered dictionary
    if py_dict:
        parsed = json.loads(json.dumps(parsed))
    return parsed
    

def load_json(data, **kwargs):
    """
    Load JSON string into python dictionary structure using json library.
    
    :param data: (str) JSON formatted string
    :param kwargs: (dict) any additional ``**kwargs`` for ``json.loads`` method 
    :returns: python dictionary 
    """
    return json.loads(data, **kwargs)
    
    
# --------------------------------------------------------------------------------
# transform functions: take structured data and return processes structured data
# --------------------------------------------------------------------------------
    

def flatten(data, parent_key="", separator='.'):
    """
    Turn a nested structure (combination of lists/dictionaries) into a 
    flattened dictionary.
    
    This function is useful to explore deeply nested structures such as XML
    output obtained from devices over NETCONF.
    
    Another usecase is filtering of the keys in resulted dictionary, as
    they are the strings, glob or regex matching can be applied on them.
    
    :param data: nested data to flatten
    :param parent_key: string to prepend to dictionary's keys, used by recursion
    :param separator: string to separate flattened keys
    :return: flattened structure
    
    Based on Stackoverflow answer:
    https://stackoverflow.com/a/62186053/12300761
    
    All credits for the idea to https://github.com/ScriptSmith
    
    Sample usage::
    
        flatten({'a': 1, 'c': {'a': 2, 'b': {'x': 5, 'y' : 10}}, 'd': [1, 2, 3] })
        
        >> {'a': 1, 'c.a': 2, 'c.b.x': 5, 'c.b.y': 10, 'd.0': 1, 'd.1': 2, 'd.2': 3}
    """
    items = []
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = "{}{}{}".format(parent_key, separator, key) if parent_key else key
            items.extend(flatten(value, new_key, separator).items())
    elif isinstance(data, list):
        for k, v in enumerate(data):
            new_key = "{}{}{}".format(parent_key, separator, k) if parent_key else k
            items.extend(flatten({str(new_key): v}).items())
    else:
        items.append((parent_key, data))        
    return dict(items)
    
    
def unflatten(data, separator='.'):
    """
    Turn flat dictionary produced by flatten function to a nested structure
        
    :param data: flattened dictionary
    :param separator: string to split flattened keys
    :return: nested structure    
    
    List indexes must follow in order, for example this flattened dictionary::
    
        {
            "5.a.b.0.c": 1,
            "5.a.b.1.c": 2,
            "10.a.b.0.c": 3,
            "10.a.b.1": 4,
        }
    
    Will produce unexpected results due to indexes not following numerical order::
    
        [{'a': {'b': [{'c': 1}]}},
         {'a': {'b': [{'c': 2}]}},
         {'a': {'b': [{'c': 3}]}},
         {'a': {'b': [4]}}]}
    """
    # decide if overall structure should be a list or a dictionary
    first_path_item = list(data.keys())[0].split(separator)[0]
    if first_path_item.isdigit():
        res = []
    else:
        res = {}
    # un-flatten data structure
    for key, value in data.items():
        tracker = res
        path = key.split(separator)
        for index, item in enumerate(path[:-1]):
            if isinstance(tracker, dict):
                # if next level is a list
                if path[index + 1].isdigit():
                    tracker.setdefault(item, [])
                else:
                    tracker.setdefault(item, {})
                tracker = tracker[item]
            elif isinstance(tracker, list):
                try:
                    tracker = tracker[int(item)]
                except IndexError:
                    # if next level is a list
                    if path[index + 1].isdigit():
                        tracker.append([])
                    else:
                        tracker.append({})        
                    tracker = tracker[-1]
        if isinstance(tracker, dict):
            tracker[path[-1]] = value
        elif isinstance(tracker, list):
            tracker.append(value)            
              
    return res
    

# --------------------------------------------------------------------------------
# filtering functions: filter structured/text data
# --------------------------------------------------------------------------------


def xpath(data, expr, **kwargs):
    """
    Function to perform xpath search/filtering of XML string using LXML library
    
    :param data: (str) XML formatted string
    :param expr: (str) xpath expression to use
    :param kwarg: (dict) **kwargs to use for LXML etree.xpath method
    :return: XML filtered string
    """
    if not HAS_LXML:
        return data
        
    tree = etree.fromstring(data)
    
    filtered = tree.xpath(expr, **kwargs)
    
    if isinstance(filtered, list):
        res = [
            etree.tostring(i, pretty_print=True, encoding="utf-8").decode()
            for i in filtered
        ]
        return "\n".join(res)
        
    return etree.tostring(filtered, pretty_print=True, encoding="utf-8")
    
    
def key_filter(data, pattern, **kwargs):
    """
    Reference Name ``key_filter`` 
    
    Function to filter data dictionary top keys using provided glob 
    patterns.
    
    :param data: (dictionary) Python dictionary
    :param pattern: (str or list) comma separated string or list of glob patterns
    :return: filtered python dictionary
    """
    pattern = [i.strip() for i in pattern.split(",")] if isinstance(pattern, str) else pattern
    if isinstance(data, dict):
        return {
            k: v for k, v in data.items() if any([fnmatchcase(k, p) for p in pattern])
        }
    else:
        return data
    

def match(data, pattern, before=0, **kwargs):
    """
    Reference name ``match``
    
    Function to search for regex pattern in devices output, similar to network 
    devices ``include/match`` pipe statements.
    
    :param data: multiline string to search in
    :param pattern: regular expression pattern to search for
    :param before: number of lines before match to include in results
    :return: filtered string
    """    
    # do sanity check
    if not isinstance(data, str):
        return data
        
    regex = re.compile(str(pattern))

    # iterate over results and search for matches
    searched_result = []
    lines_before = deque([], abs(before))
    
    # search for pattern in lines
    for line in iter(data.splitlines()):
        if regex.search(line):
            searched_result.append(
                line
                if before == 0
                else "--\n{}\n{}".format("\n".join(lines_before), line)
            )
        lines_before.append(line)

    return "\n".join(searched_result)
    

def flake(data, **kwargs):
    """
    Reference name ``flake``
    
    FLAKE - Flattened Key Filter
    
    Function to transform Python structure in a flattened python dictionary 
    representation and filter its keys using ``key_filter`` function.

    Steps are:
    
    1. Transform data to flattened Python dictionary using ``flatten`` function
    2. Filter Python dictionary keys using ``key_filter`` function
    
    :param data: (dict or list) structured data
    :param kwargs: (dict) kwargs to use with ``key_filter`` function
    :return: flattened and filtered python dictionary    
    """    
    return key_filter(
        flatten(data),
        pattern=pattern,
        **kwargs
    )
    
    
def xml_flake(data, pattern, **kwargs):
    """
    Reference name ``xml_flake``
    
    XML FLAKE - XML Flattened Key Filter
    
    Function to transform XML in a flattened python dictionary representation and
    filter its keys using ``key_filter`` function

    Steps are:
    
    1. Transform XML to flattened Python dictionary using ``xml_flatten`` function
    2. Filter Python dictionary keys using ``key_filter`` function
    
    :param data: (str) XML formatted string
    :param kwargs: (dict) kwargs to use with ``key_filter`` function
    :return: flattened and filtered python dictionary    
    """    
    return key_filter(
        xml_flatten(data),
        pattern=pattern,
        **kwargs
    )


# --------------------------------------------------------------------------------
# transformer functions: transform data, e.g. xml string to json string
# --------------------------------------------------------------------------------


def xml_to_json(data, **kwargs):
    """
    Reference name ``xml_to_json``
    
    Dependencies: requires LXML library - ``pip install lxml``
    
    Function to transform XML string to JSON string. 
    
    Steps are:
    
    1. Transform XML to Python dictionary using xmltodict by calling ``load_xml`` function
    2. Serialize Python dictionary to JSON string by calling ``to_json`` function
    
    :param data: (str) XML formatted string
    :param kwargs: (dict) kwargs to use with ``to_json`` function
    :return: JSON formatted string
    """
    return to_json(
        data=load_xml(data, py_dict=False),
        **kwargs
    )


def xml_flatten(data, **kwargs):
    """
    Reference name ``xml_flatten``

    Dependencies: requires LXML library - ``pip install lxml``
    
    Function to transform XML in a flattened python dictionary representation

    Steps are:
    
    1. Transform XML to Python dictionary using xmltodict by calling ``load_xml`` function
    2. Flatten python dictionary calling ``flatten`` function
    
    :param data: (str) XML formatted string
    :param kwargs: (dict) kwargs to use with ``flatten`` function
    :return: flattened python dictionary    
    """
    return flatten(
        data=load_xml(data, py_dict=False),
        **kwargs
    )    

 
# --------------------------------------------------------------------------------
# parsing functions: parse text data - return structured data
# --------------------------------------------------------------------------------


def parse_ttp(data, ttp_template, ttp_kwargs={}, ttp_res_kwargs={}):
    """
    Reference name ``parse_ttp``

    Dependencies: requires TTP library - ``pip install ttp``
    
    Function to parse text output from device and return structured data
    
    :param data: (str) string to parse
    :param kwargs: (dict) kwargs to use with ``flatten`` function
    :return: flattened python dictionary    
    """
    # run sanity checks
    if not isinstance(data, str):
        return data
    if not HAS_TTP:
        log.warning("nornir_salt:DataProcessor:parse_ttp failed import TTP library")
        return data
        
    # do parsing
    parser = ttp(data, ttp_template, **ttp_kwargs)
    parser.parse(one=True)
    
    return parser.result(**ttp_res_kwargs)
                

# --------------------------------------------------------------------------------
# functions dispatcher dictionary
# --------------------------------------------------------------------------------

dispatcher = {
    # formatters - structured data to text
    "to_str": to_str, 
    "to_json": to_json, 
    "to_pprint": to_pprint, 
    "to_yaml": to_yaml,
    # loaders - text to structured data
    "load_xml": load_xml,
    "load_json": load_json,
    # processors/transformers
    "flatten": flatten,
    "unflatten": unflatten,
    # filters
    "flake": flake, # flatten key filter
    "key_filter": key_filter, # filter dictionary key using glob pattern 
    "xpath": xpath, # XML xpath
    "match": match, # similar to include
    "xml_flake": xml_flake, # XML flatten key filter
    # tranformers
    "xml_to_json": xml_to_json,
    "xml_flatten": xml_flatten,
    # parsers
    "parse_ttp": parse_ttp,
}


class DataProcessor:
    """
    DataProcessor can process structured data obtained from devices. It is
    capable of:
    
    * loading data to Python structure from json, yaml, xml, csv or python format
    * serializing structured data to text in json, yaml, xml, csv or python format
    * filtering structured or string data
    * flattening and un-flattening nested data

    :param dp: (list) list of Data Processors names to pass results through
    :param kwargs: (dict) dictionary keyed by Data Processors function names, with 
      values set to dictionaries - ``**kwargs`` - to use with Data Processors functions
    """

    def __init__(self, dp=[], **kwargs):
        self.dp = dp if dp else list(kwargs.keys())
        self.dp_kwargs = kwargs

    def task_started(self, task: Task) -> None:
        pass  # ignore

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        """ Process results from device once main task completed """
        try:
            for i in result:
                try:
                    for dp_fun in self.dp:
                        i.result = dispatcher[dp_fun](
                            i.result, 
                            **self.dp_kwargs.get(dp_fun, self.dp_kwargs)
                        )
                except:
                    i.exception = traceback.format_exc()
                    log.error("nornir-salt:DataProcessor host {} result error:\n{}".format(host.name, traceback.format_exc()))
        except:
            log.error("nornir-salt:DataProcessor host {} error:\n{}".format(host.name, traceback.format_exc()))            

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore subtasks

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        pass  # ignore subtasks

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        pass # ignore final results
