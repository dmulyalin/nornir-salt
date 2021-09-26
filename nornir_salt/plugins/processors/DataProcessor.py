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
                {"fun": "match", "pattern": "interface.*"}
            ]
        )
    ])

    nr_with_processor.run(
        task=netmiko_send_command,
        command_string="show run"
    )

Filtering mini-query-language specification
===========================================

``lod_filter``, ``key_filter`` and ``find`` key name may be appended with check type
specifier suffix to instruct what type of check to execute with criteria against key
value. For example ``key_name__glob`` would use glob pattern matching.

+------------+-----------------------------------------------------------+------------------------------+
| Check Type |  Description                                              | Functions                    |
+------------+-----------------------------------------------------------+------------------------------+
| ``__glob`` | Glob case sensitive pattern matching                      | find, lod_filter, key_filter |
+------------+-----------------------------------------------------------+------------------------------+
| ``__re``   | Regular Expression pattern matching                       | find, lod_filter, key_filter |
+------------+-----------------------------------------------------------+------------------------------+

DataProcessor Class reference
=============================

.. autofunction:: nornir_salt.plugins.processors.DataProcessor.DataProcessor

DataProcessor Functions reference
=================================

DataProcessor Functions help to process results after task completed.

.. list-table:: DataProcessor Functions
   :widths: 15 85
   :header-rows: 1

   * - Reference Name
     - Description
   * - `find`_
     - Function to dispatch data to one of the filtering functions.
   * - `flake`_
     - Flattens python dictionary and filters its keys using ``key_filter``
   * - `flatten`_
     - Turn a nested structure into a flattened dictionary
   * - `key_filter`_
     - Filter data dictionary top keys using provided patterns.
   * - `load_json`_
     - Load JSON string into python dictionary structure
   * - `load_xml`_
     - Load XML string into python dictionary structure
   * - `lod_filter`_
     - List of Dictionaries (LOD) filter function
   * - `match`_
     - Search for regex pattern in devices output
   * - `parse_ttp`_
     - Parses text output from device into structured data
   * - `path`_
     - Retrieves content from nested structured data at given path
   * - `run_ttp`_
     - Parse text output from device sorting results across TTP inputs
   * - `to_json`_
     - Transform Python structure to JSON formatted string
   * - `to_pprint`_
     - Transform Python structure to pprint formatted string
   * - `to_str`_
     - Transform Python structure to string without doing any formatting
   * - `to_yaml`_
     - Transform Python structure to YAML formatted string
   * - `unflatten`_
     - Turn flat dictionary produced by `flatten`_ function to a nested structure
   * - `xml_flake`_
     - Transform XML in a flattened dictionary and filter keys using `key_filter`_
   * - `xml_flatten`_
     - Transform XML in a flattened python dictionary
   * - `xml_rm_ns`_
     - Removes all namespace information from an XML Element tree
   * - `xml_to_json`_
     - Transform XML string to JSON string
   * - `xpath`_
     - Perform xpath search/filtering of XML string using LXML library

Formatter functions
-------------------

Format structured data to json, yaml etc. text string

to_str
++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.to_str

to_json
+++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.to_json

to_pprint
+++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.to_pprint

to_yaml
+++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.to_yaml

Loader functions
----------------

Load json, yaml etc. text into python structured data

load_xml
++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.load_xml

load_json
+++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.load_json

Transform functions
-------------------

Take structured data and return transformed structured data

flatten
+++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.flatten

unflatten
+++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.unflatten

xml_to_json
+++++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xml_to_json

xml_flatten
+++++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xml_flatten

xml_rm_ns
+++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xml_rm_ns

path
++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.path_

Filter functions
----------------

Filter structured or text data

xpath
+++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xpath

key_filter
++++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.key_filter

flake
+++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.flake

xml_flake
+++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.xml_flake

match
+++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.match

lod_filter
++++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.lod_filter

find
++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.find

Parse functions
---------------

parse_ttp
+++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.parse_ttp

run_ttp
+++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.run_ttp

Misc functions
--------------

add_commands_from_ttp_template
++++++++++++++++++++++++++++++
.. autofunction:: nornir_salt.plugins.processors.DataProcessor.add_commands_from_ttp_template
"""
import logging
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
    log.error(
        "nornir_salt:DataProcessor failed import TTP library, install: pip install ttp"
    )
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
    Reference Name ``load_xml``

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
    Reference Name ``load_json``

    Load JSON string into python dictionary structure using json library.

    :param data: (str) JSON formatted string
    :param kwargs: (dict) any additional ``**kwargs`` for ``json.loads`` method
    :returns: python dictionary
    """
    return json.loads(data, **kwargs)


# --------------------------------------------------------------------------------
# transform functions: take structured data and return processes structured data
# --------------------------------------------------------------------------------


def flatten(data, parent_key="", separator=".", **kwargs):
    """
    Reference Name ``flatten``

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


def unflatten(data, separator=".", **kwargs):
    """
    Reference Name ``unflatten``

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
    return to_json(data=load_xml(data, py_dict=False), **kwargs)


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
    return flatten(data=load_xml(data, py_dict=False), **kwargs)


def xml_rm_ns(data, recover=True, ret_xml=True, **kwargs):
    """
    Reference Name ``xml_rm_ns``

    Namespace clean up code taken from:
    https://github.com/jeremyschulman/xml-tutorial/blob/master/strip-namespaces.md

    This function removes all namespace information from an XML Element tree
    so that a Caller can then use the `xpath` function without having
    to deal with the complexities of namespaces.

    Dependencies: requires LXML library - ``pip install lxml``

    :param data: (str) XML formatted string
    :param recover: (bool) if True (default) uses ``etree.XMLParser(recover=True)`` to
        parse XML, can help to recover bad XML
    :param ret_xml: (bool) indicates what to return, default is True
    :param kwargs: (dict) any additional ``**kwargs`` are ignored
    :returns: XML string with no namespaces if ret_xml is True, ``etree.Element`` otherwise
    """
    if recover:
        tree = etree.fromstring(data, parser=etree.XMLParser(recover=True))
    else:
        tree = etree.fromstring(data)

    # first we visit each node in the tree and set the tag name to its localname
    # value; thus removing its namespace prefix

    for elem in tree.getiterator():
        elem.tag = etree.QName(elem).localname

    # at this point there are no tags with namespaces, so we run the cleanup
    # process to remove the namespace definitions from within the tree.

    etree.cleanup_namespaces(tree)

    if ret_xml:
        return etree.tostring(tree, pretty_print=True, encoding="utf-8").decode()
    else:
        return tree


def path_(data, path, **kwargs):
    """
    Reference name ``path_``

    Function to retrieve content from nested structured data at given path.

    :param path: (str, list) dot separated path to result or list of path items
    :param data: (dict) data to get results from
    :return: results at given path

    Sample data::

        {
            "VIP_cfg": {
                "1.1.1.1": {
                    "config_state": "dis",
                    "services": {
                        "443": {
                            "https": [
                                {"real_port": "443"}
                            ],
                        }
                    }
                }
            }
        }

    With ``path`` ``"VIP_cfg.'1.1.1.1'.services.443.https.0.real_port"``
    will return ``443``
    """
    ret = data

    # form path list
    if isinstance(path, str):
        # perform path split accounting for quotes inside path
        path_list = [""]
        inside_quotes = False
        for char in path:
            if char == "." and not inside_quotes:
                path_list.append("")
            elif char in ["'", '"']:
                inside_quotes = not inside_quotes
            else:
                path_list[-1] += char
    elif isinstance(path, list):
        path_list = path
    else:
        raise TypeError(
            "nornir-salt:DataProcessor:path unsupported path type {}".format(type(path))
        )

    # descend down the data path
    for item in path_list:
        if item in ret or isinstance(item, int):
            ret = ret[item]
        elif item.isdigit():
            ret = ret[int(item)]

    return ret


# --------------------------------------------------------------------------------
# filtering functions: filter structured/text data
# --------------------------------------------------------------------------------


# check functions
def _check_glob(value, criteria):
    # returns True if glob pattern matches value
    return fnmatchcase(str(value), criteria)


def _check_regex(value, criteria):
    # returns True if regex pattern matches value
    return True if re.search(criteria, value) else False


check_fun_dispatcher = {
    "glob": _check_glob,
    "re": _check_regex,
}


def _form_check_list(checks_dictionary):
    """
    Helper function to form a list of filtering checks.

    :param checks_dictionary: (dict) dictionary where keys used to indicate
        check type and value is the criteria to check. Default check type is
        glob case sensitive pattern matching.
    :return: list of dictionaries

    ``checks_dictionary`` keys can use filtering mini-query-language specifiers
    to indicate check type.

    Returns list of dictionaries::

        [
            {
                "fun": _check_fun_reference,
                "key": checks_dictionary_key_name,
                "criteria": checks_dictionary_key_value,
            }
        ]
    """
    checks = []
    for key_name, criteria in checks_dictionary.items():
        if key_name.split("__")[-1] in check_fun_dispatcher:
            check_type = key_name.split("__")[-1]
            # account for cases when pattern contains other __
            key_name = "__".join(key_name.split("__")[:-1])
        else:
            check_type, key_name = (
                "glob",
                key_name,
            )
        checks.append(
            {
                "fun": check_fun_dispatcher[check_type],
                "key": key_name,
                "criteria": criteria,
            }
        )
    return checks


def xpath(data, expr, rm_ns=False, recover=False, **kwargs):
    """
    Reference Name ``xpath``

    Function to perform xpath search/filtering of XML string using LXML library.

    Dependencies: requires LXML library - ``pip install lxml``

    :param data: (str) XML formatted string
    :param expr: (str) xpath expression to use
    :param rm_ns: (bool) if True removes namespace from XML string using
        ``xml_rm_ns`` function, default is False
    :param kwarg: (dict) ``**kwargs`` to use for LXML etree.xpath method
    :return: XML filtered string
    """
    if not HAS_LXML:
        return data

    if rm_ns:
        tree = xml_rm_ns(data, ret_xml=False, recover=recover)
    elif recover:
        tree = etree.fromstring(data, parser=etree.XMLParser(recover=True))
    else:
        tree = etree.fromstring(data)

    filtered = tree.xpath(expr, **kwargs)

    if isinstance(filtered, list):
        res = [
            etree.tostring(i, pretty_print=True, encoding="utf-8").decode()
            for i in filtered
        ]
        return "\n".join(res)

    return etree.tostring(filtered, pretty_print=True, encoding="utf-8").decode()


def key_filter(data, pattern=None, **kwargs):
    """
    Reference Name ``key_filter``

    Function to filter data dictionary top keys using provided patterns.

    :param data: (dictionary) Python dictionary
    :param kwargs: (dict) any additional kwargs are key and value pairs, where key name
        is arbitrary and used to indicate check type following `Filtering mini-query-language specification`_
        and value is the criteria to check. Default check type is glob case sensitive
        pattern matching.
    :param pattern: (str) pattern to use for filtering
    :return: filtered python dictionary

    Default logic is key name must pass **any** of the criteria provided.

    Sample usage::

        key_filter(
            data=data_dictionary,
            pattern="1234*",
            pattern__glob="abc*",
            pattern2__glob="*abc*",
            pattern__re="abc.*",
        )

    Filtered dictionary key name must satisfy at least one of the matching criteria.
    """
    if not isinstance(data, dict):
        log.warning(
            "nornir_salt:DataProcessor:key_filter skipping, data is not dictionary but {}".format(
                type(data)
            )
        )
        return data

    if pattern:
        kwargs["pattern"] = pattern

    checks = _form_check_list(kwargs)
    log.debug(
        "nornir_salt:DataProcessor:key_filter running filter checks {}".format(checks)
    )

    return {
        k: data[k]
        for k in data.keys()
        if any([c["fun"](k, c["criteria"]) for c in checks])
    }


def lod_filter(data, pass_all=True, strict=True, **kwargs):
    """
    Reference Name ``lod_filter``

    List of Dictionaries (LOD) filter function.

    Iterates over list of dictionaries and returns dictionary items that have
    value of key matched by glob pattern.

    Patterns are case sensitive.

    Key value converted to string to perform match check.

    :param data: (list) list of dictionaries to search in
    :param kwargs: (dict) any additional kwargs are key and value pairs, where key is a name
        of the dictionary key to search for and value is the criteria to check. Default check
        type is glob case sensitive pattern matching.
    :param pass_all: (bool) if True (default) logic is AND - dictionary must pass ALL
        checks, if False logic is ANY
    :param strict: (bool) if True (default) invalidates list dictionary item
        if no criteria key found in dictionary
    :return: filtered list of dictionaries
    """
    if not isinstance(data, list):
        log.warning(
            "nornir_salt:DataProcessor:lod_filter skipping, data is not list but {}".format(
                type(data)
            )
        )
        return data

    checks = _form_check_list(kwargs)
    log.debug(
        "nornir_salt:DataProcessor:lod_filter running filter checks {}".format(checks)
    )

    # run filtering
    if pass_all:
        return [
            i
            for i in data
            if all(
                [
                    c["fun"](i[c["key"]], c["criteria"])
                    if c["key"] in i
                    else not strict
                    for c in checks
                ]
            )
        ]
    else:
        return [
            i
            for i in data
            if any(
                [
                    c["fun"](i[c["key"]], c["criteria"])
                    if c["key"] in i
                    else not strict
                    for c in checks
                ]
            )
        ]


def match(data, pattern, before=0, **kwargs):
    """
    Reference name ``match``

    Function to search for regex pattern in devices output, similar to network
    devices ``include/match`` pipe statements.

    :param data: multiline string to search in
    :param pattern: pattern to search for, glob (default) or regex
    :param before: number of lines before match to include in results
    :return: filtered string
    """
    # do sanity check
    if not isinstance(data, str):
        return data

    regex = re.compile(str(pattern))
    searched_result = []
    lines_before = deque([], abs(before))

    # iterate over results and search for matches
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
    return key_filter(flatten(data), **kwargs)


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
    return key_filter(xml_flatten(data), pattern=pattern, **kwargs)


def find(data, path=None, **kwargs):
    """
    Reference name ``find``

    Function to dispatch data to one of the filtering functions.

    :param data: (list, dict, str) data to search in
    :param path: (str) dot separated path or list of path items to results
        within data to search in
    :return: filtered results

    Dispatching process happens after evaluating ``path`` and retrieving
    results to process from overall data.

    ``path`` only evaluated if provided data is a dictionary.

    Dispatch rules:

    * if result type is list uses ``lod_filter``
    * if result type is dictionary uses ``key_filter``
    * if result type is string uses ``match`` function
    """
    result = data

    if path:
        result = path_(data, path)

    if isinstance(result, list):
        return lod_filter(result, **kwargs)
    elif isinstance(result, dict):
        return key_filter(result, **kwargs)
    elif isinstance(result, str):
        return match(result, **kwargs)


# --------------------------------------------------------------------------------
# parsing functions: parse text data - return structured data
# --------------------------------------------------------------------------------


def parse_ttp(data: str, template: str, ttp_kwargs={}, res_kwargs={}, **kwargs):
    """
    Reference name ``parse_ttp``

    Dependencies: requires TTP library - ``pip install ttp``

    Function to parse text output from device and return structured data

    :param data: (str) string to parse
    :param template: (str) TTP template string or reference to ``ttp://`` templates
    :param ttp_kwargs: (dict) dictionary to use while instantiating TTP parse object
    :param res_kwargs: (dict) dictionary to use with ``result`` method
    :return: parsed structure
    """
    if not HAS_TTP:
        log.warning("nornir_salt:DataProcessor:parse_ttp failed import TTP library")
        return data

    if isinstance(data, str):
        # do parsing
        parser = ttp(data, template, **ttp_kwargs)
        parser.parse(one=True)

        return parser.result(**res_kwargs)
    else:
        log.warning(
            "nornir_salt:DataProcessor:parse_ttp skipping, data is not string but {}".format(
                type(data)
            )
        )
        return data


def run_ttp(
    data, template, ttp_kwargs={}, res_kwargs={}, task=None, remove_tasks=True, **kwargs
):
    """
    Reference name ``run_ttp``

    Dependencies: requires TTP library - ``pip install ttp``

    Function to parse text output from device sorting results across TTP inputs
    based on commands values.

    :param data: (str) Nornir MultiResult object
    :param template: (str) TTP template string or reference to ``ttp://`` templates
    :param ttp_kwargs: (dict) dictionary to use while instantiating TTP parse object
    :param res_kwargs: (dict) dictionary to use with ``result`` method
    :param remove_tasks: (bool) if set to True and data is MultiResult object will remove
        other task results
    :param task: (obj) Nornir Task object, used to form parsing results when data is
        MultiResult object
    :return: parsed structure

    Provided Nornir MultiResult object processed by sorting task results across TTP
    Template inputs to parse. After parsing, all other tasks' results removed from
    MultiResult object and parsing results appended to it. If ``remove_tasks`` set to
    False, other tasks results not removed.
    """
    if not HAS_TTP:
        log.warning("nornir_salt:DataProcessor:parse_ttp failed import TTP library")
        return data

    if isinstance(data, MultiResult):
        parser = ttp(template=template, **ttp_kwargs)
        ttp_inputs_load = parser.get_input_load()

        # go over template's inputs and add output from devices
        for template_name, inputs in ttp_inputs_load.items():
            # if no inputs defined, add all to default input
            if not inputs:
                default_input_data = []
                for i in data:
                    # check if need to skip this task
                    if hasattr(i, "skip_results") and i.skip_results is True:
                        continue
                    if isinstance(i.result, str):
                        default_input_data.append(i.result)
                if default_input_data:
                    parser.add_input(
                        data="\n".join(default_input_data),
                        input_name="Default_Input",
                        template_name=template_name,
                    )
            # sort results across inputs with commands
            else:
                for input_name, input_params in inputs.items():
                    commands = input_params.get("commands", [])
                    input_data = []
                    for i in data:
                        # check if need to skip this task
                        if hasattr(i, "skip_results") and i.skip_results is True:
                            continue
                        if i.name in commands and isinstance(i.result, str):
                            input_data.append(i.result)
                    if input_data:
                        parser.add_input(
                            data="\n".join(input_data),
                            input_name=input_name,
                            template_name=template_name,
                        )

        # run parsing in single process
        parser.parse(one=True)

        # remove other task results
        if remove_tasks:
            while data:
                _ = data.pop()

        # add parsing results
        data.append(
            Result(host=task.host, result=parser.result(**res_kwargs), name="run_ttp")
        )
    else:
        log.warning(
            "nornir_salt:DataProcessor:parse_ttp skipping, data is not MultiResult but {}".format(
                type(data)
            )
        )
        return data


# --------------------------------------------------------------------------------
# misc
# --------------------------------------------------------------------------------


def add_commands_from_ttp_template(task, template, **kwargs):
    """
    Function to extract commands from TTP template and add them
    to task params. Used in conjunction with ``run_ttp`` parsing function.

    This function called at ``task_started`` point, allowing to update
    task's ``params`` dictionary with ``commands`` to collect from devices
    prior to further executing the task.

    Commands extracted from TTP Template inputs that may contain definitions
    of ``commands`` list.

    Dependencies: requires TTP library - ``pip install ttp``.

    :param task: (obj) Nornir task object
    :param template: (str) TTP Template string
    """
    if not HAS_TTP:
        log.warning(
            "nornir_salt:DataProcessor:extract_commands_from_ttp failed import TTP library"
        )
        return

    task.params.setdefault("commands", [])
    parser = ttp(template=template)
    ttp_inputs_load = parser.get_input_load()

    # go over template's inputs and collect commands to get from devices
    for template_name, inputs in ttp_inputs_load.items():
        for input_name, input_params in inputs.items():
            for cmd in input_params.get("commands", []):
                if cmd not in task.params["commands"]:
                    task.params["commands"].append(cmd)


# --------------------------------------------------------------------------------
# functions dispatcher dictionary
# --------------------------------------------------------------------------------

task_instance_completed_dispatcher_per_task = {
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
    "flake": flake,  # flatten key filter
    "key_filter": key_filter,  # filter dictionary key using glob pattern
    "xpath": xpath,  # XML xpath
    "match": match,  # similar to include
    "xml_flake": xml_flake,  # XML flatten key filter
    "lod_filter": lod_filter,  # list of dictionaries filter
    "find": find,
    # transformers
    "xml_to_json": xml_to_json,
    "xml_flatten": xml_flatten,
    "xml_rm_ns": xml_rm_ns,
    "path": path_,
    # parsers
    "parse_ttp": parse_ttp,
}

task_instance_completed_dispatcher_multiresult = {
    # parsers
    "run_ttp": run_ttp,
}

task_started_dispatcher = {
    "run_ttp": add_commands_from_ttp_template,
}


class DataProcessor:
    """
    DataProcessor can process structured data obtained from devices. It is
    capable of:

    * loading data to Python structure from json, yaml, xml, csv or python format
    * serializing structured data to text in json, yaml, xml, csv or python format
    * filtering structured or string data
    * flattening and un-flattening nested data

    :param dp: (list) list of Data Processors function names to pass results through

    ``dp`` argument can be of one of these types:

    * comma separated string of function names
    * list of function name strings and/or dictionaries with function details

    Data processor function dictionary items should have this structure::

        {
            "fun": function name [str],
            "k1": "v1", ... "kN": "vN"
        }

    Where:

    * ``fun`` - Reference Name of DataProcessor function to run
    * ``kN`` - Any additional key-word arguments to use with function
    """

    def __init__(self, dp=[]):
        self.dp = []
        if isinstance(dp, list):
            for i in dp:
                if isinstance(i, str):
                    self.dp.append({"fun": i.strip()})
                elif isinstance(i, dict):
                    self.dp.append(i)
                else:
                    raise TypeError(
                        "nornir_salt:DataProcessor dp list items should be dictionary or string not '{}'".format(
                            type(i)
                        )
                    )
        elif isinstance(dp, str):
            self.dp = [{"fun": i.strip()} for i in dp.split(",")]
        else:
            raise TypeError(
                "nornir_salt:DataProcessor dp argument should be list or string not '{}'".format(
                    type(dp)
                )
            )

    def task_started(self, task: Task) -> None:
        """ Pre-Process Task details before executing it """
        for dp_dict in self.dp:
            dp_dict_copy = dp_dict.copy()
            try:
                fun = dp_dict_copy.pop("fun")
                if fun in task_started_dispatcher:
                    task_started_dispatcher[fun](task, **dp_dict_copy)
            except:
                log.error(
                    "nornir-salt:DataProcessor task pre-processing task {} dp '{}' error:\n{}".format(
                        task, dp_dict, traceback.format_exc()
                    )
                )

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        """ Process results from device once main task completed """
        # check if has failed tasks, do nothing in such a case
        if result.failed:
            log.error("nornir_salt:DataProcessor do nothing, return, has failed tasks")
            return

        # run DataProcessor function
        for dp_dict in self.dp:
            dp_dict_copy = dp_dict.copy()
            try:
                fun = dp_dict_copy.pop("fun")
                if fun in task_instance_completed_dispatcher_multiresult:
                    try:
                        task_instance_completed_dispatcher_multiresult[fun](
                            result, task=task, **dp_dict_copy
                        )
                    except:
                        log.error(
                            "nornir-salt:DataProcessor host {} function '{}' all-task error:\n{}".format(
                                host.name, fun, traceback.format_exc()
                            )
                        )
                elif fun in task_instance_completed_dispatcher_per_task:
                    for i in result:
                        try:
                            # check if need to skip this task
                            if hasattr(i, "skip_results") and i.skip_results is True:
                                continue
                            # pass task result through dp function
                            i.result = task_instance_completed_dispatcher_per_task[fun](
                                i.result, **dp_dict_copy
                            )
                        except:
                            i.exception = traceback.format_exc()
                            log.error(
                                "nornir-salt:DataProcessor host {} function '{}' per-task error:\n{}".format(
                                    host.name, fun, traceback.format_exc()
                                )
                            )
                else:
                    raise KeyError(fun)
            except:
                log.error(
                    "nornir-salt:DataProcessor host {} dp '{}' error:\n{}".format(
                        host.name, dp_dict, traceback.format_exc()
                    )
                )

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore subtasks

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        pass  # ignore subtasks

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        pass  # ignore final results
