"""
Test Functions
##############

It is often required to validate network devices state against certain
criteria, test functions designed to address most common use cases in 
that area.

Majority of available checks help to implement simple approach of 
"if this then that" logic, for instance: if output contains this 
pattern then test failed.

Dependencies:

* Nornir 3.0 and beyond
* `Tabulate module <https://pypi.org/project/tabulate/>`_ for results table formatting 
* `Cerberus module <https://pypi.org/project/Cerberus/>`_ for ``CerberusTest`` function
* `Colorama module <https://pypi.org/project/colorama/>`_ for ``RunTestSuite`` results printing

All test functions return list of dictionaries where each dictionary 
contains::

    {
        "host": name of host,
        "test_name": descriptive name of the test,
        "task": name of task results of which used for test,
        "result": PASS or FAIL,
        "success": True or False,
        "error": None or Error description,
        "test_type": Type of test performed,
        "criteria": Validation criteria used
    }

Return results could be formatted in a table using
`tabulate module <https://pypi.org/project/tabulate/>`_  
by supplying ``tabulate`` argument to test functions call.


Contains Test
=============

This function checks if output contains certain string or pattern.

Example::

    from nornir_salt import ContainsTest, nr_test
    
    output = nr.run(
        task=nr_test,
        ret_data='''
    ntp server 7.7.7.8
    ntp server 7.7.7.7
        '''
        name="check ntp config"
    )
    check_result = ContainsTest(
        output, 
        task="check ntp config",
        test_name="Test NTP config",
        pattern="ntp server 7.7.7.8"
    )
    pprint.pprint(check_result)
    
    # [{'criteria': 'ntp server 7.7.7.8',
    #   'error': None,
    #   'host': 'IOL1',
    #   'result': 'PASS',
    #   'success': True,
    #   'task': 'check ntp config',
    #   'test_name': 'Test NTP config',
    #   'test_type': 'contains'}]

.. autofunction:: nornir_salt.plugins.functions.TestFuncs.ContainsTest

Contains Lines Test
===================

This function checks if lines or patterns provided contained in output. 
Each pattern checked individually.

Example::

    from nornir_salt import ContainsLinesTest, nr_test
    
    output = nr.run(
        task=nr_test,
        ret_data='''
    ntp server 7.7.7.8
    ntp server 7.7.7.7
        '''
        name="check ntp config"
    )
    check_result = ContainsLinesTest(
        output, 
        test_name="check ntp config", 
        lines="ntp server 7.7.7.7\\nntp server 7.7.7.8"
    )
    pprint.pprint(check_result)
    
    # [{'criteria': '',
    #   'error': None,
    #   'host': 'IOL1',
    #   'result': 'PASS',
    #   'success': True,
    #   'task': -1,
    #   'test_name': 'check ntp config',
    #   'test_type': 'contains lines'}]

.. autofunction:: nornir_salt.plugins.functions.TestFuncs.ContainsLinesTest

Equality Testing
================

Test results for equality.

Example::

    from nornir_salt import EqualTest, nr_test
    
    output = nr.run(
        task=nr_test,
        ret_data='''ntp server 7.7.7.8
    ntp server 7.7.7.7'''
        name="check ntp config"
    )
    check_result = EqualTest(
        output, 
        test_name="check ntp config", 
        pattern'''ntp server 7.7.7.7
    ntp server 1.1.1.1'''
    )
    pprint.pprint(check_result)
    
    # [{'criteria': 'ntp server 7.7.7.7\\nntp s',
    #   'error': 'Criteria pattern and output not equal',
    #   'host': 'IOL2',
    #   'result': 'FAIL',
    #   'success': False,
    #   'task': -1,
    #   'test_name': 'check ntp config',
    #   'test_type': 'equal'}]

.. autofunction:: nornir_salt.plugins.functions.TestFuncs.EqualTest

Cerberus Validation
===================

Uses Cerberus library to validate results output.

Example::

    from nornir_salt import CerberusTest, nr_test
    
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": [
                {"interface": "Gi1", "mtu": 1200},
                {"interface": "Gi2", "mtu": 1500}
            ],
            "IOL2": [
                {"interface": "Gi6", "mtu": 9600}
            ]
        },
        name="interfaces MTU"
    )    
    test_schema = {
        "mtu": {"type": "integer", "allowed": [1500]} 
    }
    check_result = CerberusTest(
        output, 
        schema=test_schema,
        task="interfaces MTU",
        test_name="check MTU using cerberus"
    )
    pprint.pprint(check_result)
    
    # [{'criteria': None,
    #   'error': {'mtu': ['unallowed value 1200']},
    #   'host': 'IOL1',
    #   'result': 'FAIL',
    #   'success': False,
    #   'task': 'interfaces MTU',
    #   'test_name': 'check MTU using cerberus',
    #   'test_type': 'cerberus'},
    #  {'criteria': None,
    #   'error': {'mtu': ['unallowed value 9600']},
    #   'host': 'IOL2',
    #   'result': 'FAIL',
    #   'success': False,
    #   'task': 'interfaces MTU',
    #   'test_name': 'check MTU using cerberus',
    #   'test_type': 'cerberus'}]

.. autofunction:: nornir_salt.plugins.functions.TestFuncs.CerberusTest

Custom Test Function
====================

This test type allows to call custom function for results checking.

Example::

    from nornir_salt import CustomFunctionTest, nr_test
    
    def check_ntp_config(result):
        ret =[]
        if "7.7.7.8" not in result.result:
            ret.append({
                "error": "Server 7.7.7.8 not in config",
                "result": "FAIL",
                "success": False
            })
        return ret
    
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": '''
        ntp server 7.7.7.8
        ntp server 7.7.7.7
            '''
            "IOL2": '''
        ntp server 7.7.7.7
            '''
        },
        name="check ntp config"
    )
    
    check_result = CustomFunctionTest(
        output, 
        function_call=check_ntp_config,
        task="check ntp config",
        test_name="Check NTP cfg using custom fun"
    )
    pprint.pprint(check_result)
    
    # [{'criteria': None,
    #   'error': None,
    #   'host': 'IOL1',
    #   'result': 'PASS',
    #   'success': True,
    #   'task': 'check ntp config',
    #   'test_name': 'Check NTP cfg using custom fun',
    #   'test_type': 'custom'},
    #  {'criteria': None,
    #   'error': 'Server 7.7.7.8 not in config',
    #   'host': 'IOL2',
    #   'result': 'FAIL',
    #   'success': False,
    #   'task': 'check ntp config',
    #   'test_name': 'Check NTP cfg using custom fun',
    #   'test_type': 'custom'}]

.. autofunction:: nornir_salt.plugins.functions.TestFuncs.CustomFunctionTest

Run Tests Suite
===============

Function to perform a list of tests.

Example::

    from nornir_salt import RunTestSuite, nr_test
    
    main_output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": '''ntp server 7.7.7.8
    ntp server 7.7.7.7''',
            "IOL2": '''
    ntp server 7.7.7.7
        '''
        },
        name="check ntp config"
    )
    
    output_2 = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": '''
    logging host 1.1.1.1
    logging host 2.2.2.2
            ''',
            "IOL2": '''
    logging host 3.3.3.3
        '''
        },
        name="check syslog config"
    )
    
    test_suite = [
        {
            "test": "contains",
            "test_name": "check configuration of NTP",
            "pattern": "7.7.7.8"
        },
        {
            "test": "contains_re",
            "test_name": "check configuration of NTP using RE",
            "pattern": "7\.7\.7.+",
            "task": "check ntp config"
        },
        {
            "test": "contains_lines",
            "test_name": "check configuration of logging",
            "lines": ["1.1.1.1", "2.2.2.2"],
            "task": "check syslog config",
            "result": output_2
        },    
        {
            "test": "custom",
            "test_name": "check NTP cfg custom fun",
            "function_file": "./assets/custom_check_function_fun_1.txt",
            "function_name": "fun_1",
            "result": main_output
        }
    ]
    
    check_result = RunTestSuite(
        main_output, 
        test_suite, 
        tabulate={
            "headers": ["host", "test_name", "task", "result", "success", "error", "test_type", "criteria"],
            "tablefmt": "fancy_grid"
        },
        print_results=True
    )
    
    # prints to terminal:
    ╒════════╤═════════════════════════════════════╤═════════════════════╤══════════╤═══════════╤════════════════════════════════╤════════════════╤════════════╕
    │ host   │ test_name                           │ task                │ result   │ success   │ error                          │ test_type      │ criteria   │
    ╞════════╪═════════════════════════════════════╪═════════════════════╪══════════╪═══════════╪════════════════════════════════╪════════════════╪════════════╡
    │ IOL1   │ check configuration of NTP          │ -1                  │ PASS     │ True      │                                │ contains       │ 7.7.7.8    │
    ├────────┼─────────────────────────────────────┼─────────────────────┼──────────┼───────────┼────────────────────────────────┼────────────────┼────────────┤
    │ IOL2   │ check configuration of NTP          │ -1                  │ FAIL     │ False     │ Criteria pattern not in output │ contains       │ 7.7.7.8    │
    ├────────┼─────────────────────────────────────┼─────────────────────┼──────────┼───────────┼────────────────────────────────┼────────────────┼────────────┤
    │ IOL1   │ check configuration of NTP using RE │ check ntp config    │ PASS     │ True      │                                │ contains       │ 7\.7\.7.+  │
    ├────────┼─────────────────────────────────────┼─────────────────────┼──────────┼───────────┼────────────────────────────────┼────────────────┼────────────┤
    │ IOL2   │ check configuration of NTP using RE │ check ntp config    │ PASS     │ True      │                                │ contains       │ 7\.7\.7.+  │
    ├────────┼─────────────────────────────────────┼─────────────────────┼──────────┼───────────┼────────────────────────────────┼────────────────┼────────────┤
    │ IOL1   │ check configuration of logging      │ check syslog config │ PASS     │ True      │                                │ contains lines │            │
    ├────────┼─────────────────────────────────────┼─────────────────────┼──────────┼───────────┼────────────────────────────────┼────────────────┼────────────┤
    │ IOL2   │ check configuration of logging      │ check syslog config │ FAIL     │ False     │ Line not in output             │ contains lines │ 1.1.1.1    │
    ├────────┼─────────────────────────────────────┼─────────────────────┼──────────┼───────────┼────────────────────────────────┼────────────────┼────────────┤
    │ IOL1   │ check NTP cfg custom fun            │ -1                  │ PASS     │ True      │                                │ custom         │            │
    ├────────┼─────────────────────────────────────┼─────────────────────┼──────────┼───────────┼────────────────────────────────┼────────────────┼────────────┤
    │ IOL2   │ check NTP cfg custom fun            │ -1                  │ FAIL     │ False     │ Server 7.7.7.8 not in config   │ custom         │            │
    ╘════════╧═════════════════════════════════════╧═════════════════════╧══════════╧═══════════╧════════════════════════════════╧════════════════╧════════════╛

.. autofunction:: nornir_salt.plugins.functions.TestFuncs.RunTestSuite
"""
import logging
import re
import traceback
from .ResultSerializer import ResultSerializer

log = logging.getLogger(__name__)

try:
    import tabulate as tabulate_lib
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False
    log.error("Failed to import tabulate library, install it: pip install tabulate")

try:
    from cerberus import Validator
    HAS_CERBERUS = True
except ImportError:
    log.error("Failed to import Cerberus library, make sure it is installed")
    HAS_CERBERUS = False

# return datum template dictionary
ret_datum_template = {
    "host": "",
    "test_name": "",
    "task": "",
    "result": "PASS",
    "success": True,
    "error": None ,
    "test_type": None,
    "criteria": None
}


def tabulate_formatter(data, tabulate):
    """
    Helper function to format data - list of dictionaries -
    in a table using tabulate module.
    
    :param data: list of dictionaries to make a table from
    :param tabulate: dictionary with ``**kwargs`` for 
        ``tabulate.tabulate`` method or boolean
        
    If ``tabulate`` is boolean, tabulate called with default 
    arguments.
    """
    data_to_tabulate = data
    
    # check if need to filter headers
    if isinstance(tabulate, dict):
        if isinstance(tabulate.get("headers"), list):
            try:
                data_to_tabulate = [
                    [item[i] for i in tabulate["headers"]]  
                    for item in data
                ]
            except KeyError:
                tabulate["headers"] = "keys"
        elif "headers" not in tabulate:
            tabulate["headers"] = "keys"            
    elif isinstance(tabulate, bool):
        tabulate = {"headers": "keys"}
    
    return tabulate_lib.tabulate(data_to_tabulate, **tabulate)    


def _run_test(
        result, 
        test_name,
        tabulate,
        test_function,
        test_type,
        task=None,
        per_task=True,
        serialize=False,
        **kwargs
    ):
    """
    Helper function to avoid code repetition. 
    
    This function takes Nornir ``result`` object, iterates over it 
    and runs ``test_function`` against given ``task`` results.
    
    :param result: ``nornir.core.task.AggregatedResult`` object
    :param task: (str) name of task to test results for
    :param test_name: (str) descriptive name of test
    :param tabulate: (dict or bool) tabulate module parameters
    :test_function: callable function to use for testing
    :param test_type: (str) type of test running
    :param per_task: (bool) default is True, runs on all host's 
        results if False
    :param serialize: (bool) default False, if True will serialize 
        results to dictionary using ``ResultSerializer`` function 
        before processing results with test function
    :return: list of dictionaries with test results
    """
    ret = []
    
    # check if need to serialize results to dictionary
    if serialize:
        result = ResultSerializer(result, add_details=True)
        
    # iterate over hosts results and run check
    for hostname, results in result.items():     
        task_result = "_not_found_"
        
        # check if should use host's results as is
        if not per_task:
            task_result = results
        # get task results by task name
        elif isinstance(task, str):
            if serialize:
                task_result = results[task]
            else:
                for i in results:
                    if i.name == task:
                        task_result = i
                        break
        # get task results by task index
        elif isinstance(task, int):
            if serialize:
                # this will only work with python3.6 and higher
                # as it depends on insertion-order preservation 
                # nature of dictionary objects
                key = list(results.keys())[task]
                task_result = results[key]
            else:
                task_result=results[task]
                
        # form return datum dictionary
        ret_datum = ret_datum_template.copy()
        ret_datum["host"] = hostname
        ret_datum["test_name"] = test_name if test_name else task
        ret_datum["task"] = task    
        ret_datum["test_type"] = test_type

        # check if has results
        if task_result == "_not_found_" :
            ret_datum["success"] = False
            ret_datum["error"] = "Failed to get result, is task name correct?" 
            ret_datum["result"] = "FAIL"
            ret.append(ret_datum)
            continue
            
        # perform check
        try:
            test_res = test_function(task_result, **kwargs)
            if isinstance(test_res, dict):
                ret_datum.update(test_res)
                ret.append(ret_datum) 
            elif isinstance(test_res, list):
                if test_res == []:
                    ret.append(ret_datum)
                else:
                    for item in test_res:
                        ret_datum_copy = ret_datum.copy()
                        ret_datum_copy.update(item)
                        ret.append(ret_datum_copy)
        except:
            tb = traceback.format_exc()
            log.error("Nornir Tests _run_test error: {}".format(tb))
            ret_datum["success"] = False
            ret_datum["error"] = str(tb)    
            ret_datum["result"] = "FAIL"
            ret.append(ret_datum)
           
    
    # check if need to use tabulate to format return results
    if tabulate and HAS_TABULATE:
        return tabulate_formatter(ret, tabulate)
        
    return ret
    
    
def ContainsTest(
        result, 
        pattern,
        task=-1,
        test_name=None,
        tabulate={},
        revert=False,
        use_re=False
    ):
    """
    Function to check if pattern contained in output of given
    ``task``'s result.
    
    :param result: ``nornir.core.task.AggregatedResult`` object
    :param pattern: (str) pattern to check containment for
    :param task: (str or int) name of task to check results for, 
        can be list index instead, default is ``-1``, last task's results
    :param test_name: (str) descriptive name of the test
    :param tabulate: (dict or bool), if set to True, will use ``tabulate`` module
        to format results, or can be a dictionary of ``**kwargs`` to pass
        on to ``tabulate.tabulate`` method.
    :param revert: (bool) if True flips the logic to opposite - check if pattern
        not contained in results
    :param use_re: (bool) if True uses re.search to check for pattern in output
    :return: list of dictionaries with check results
    """
    # form criteria and include in in results for ease of debugging
    criteria = pattern if len(pattern) < 25 else pattern[0:24]
    criteria = criteria.replace("\n", "\\n")
    
    def _contains(task_result, pattern, use_re, criteria, **kwargs):
        ret = {"criteria": criteria}
        if use_re:
            if not re.search(pattern, task_result["result"]):
                ret["result"] = "FAIL"
                ret["success"] = False
                ret["error"] = "Criteria regex not in output"    
        elif pattern not in task_result["result"]:
            ret["result"] = "FAIL"
            ret["success"] = False        
            ret["error"] = "Criteria pattern not in output"
        return ret

    def _not_contains(task_result, pattern, use_re, criteria, **kwargs):
        ret = {"criteria": criteria}
        if use_re:
            if re.search(pattern, task_result["result"]):
                ret["result"] = "FAIL"
                ret["success"] = False        
                ret["error"] = "Criteria regex in output"    
        elif pattern in task_result["result"]:
            ret["result"] = "FAIL"
            ret["success"] = False        
            ret["error"] = "Criteria pattern in output"
        return ret
    
    return _run_test(
        result=result, 
        pattern=pattern,
        task=task,
        test_name=test_name,
        tabulate=tabulate,
        test_function=_not_contains if revert else _contains,
        test_type="not contains" if revert else "contains",
        use_re=use_re,
        criteria=criteria,
        serialize=True
    )


def ContainsLinesTest(
        result,
        lines,
        task=-1,
        test_name=None,
        tabulate={},
        revert=False
    ):
    """
    Function to check that all lines contained in output.
    
    Tests each line one by one, this is the key difference compared to
    ``ContainsTest`` function, where whole pattern checked for presence in 
    output from device.
    
    :param result: ``nornir.core.task.AggregatedResult`` object
    :param lines: (str or list) lines to check, if string, lines can be
        separated using ``\\n`` newline, e.g.: "line1\\nline2\\nline3"
    :param task: (str or int) name of task to check results for,
        can be list index instead, default is ``-1``, last task's results
    :param test_name: (str) descriptive name of the test
    :param tabulate: (dict or bool), if set to True, will use ``tabulate`` module
        to format results, or can be a dictionary of ``**kwargs`` to pass
        on to ``tabulate.tabulate`` method.
    :param revert: (bool) if True flips the logic to opposite - check if lines
        not contained in results
    """    
    def _contains_lines(task_result, lines, **kwargs):
        ret = {"criteria": ""}
        lines_list = lines.splitlines() if isinstance(lines, str) else lines
        for line in lines_list:
            if not line.strip():
                continue
            if line not in task_result["result"]:
                ret["result"] = "FAIL"
                ret["success"] = False    
                ret["error"] = "Line not in output"
                ret["criteria"] = line if len(line) < 25 else line[0:24]
                break
        return ret
                
    def _not_contains_lines(task_result, lines, **kwargs):
        ret = {"criteria": ""}
        lines_list = lines.splitlines() if isinstance(lines, str) else lines
        for line in lines_list:
            if not line.strip():
                continue
            if line in task_result["result"]:
                ret["result"] = "FAIL"
                ret["success"] = False    
                ret["error"] = "Line in output"
                ret["criteria"] = line if len(line) < 25 else line[0:24]
                break
        return ret
        
    return _run_test(
        result=result, 
        lines=lines,
        task=task,
        test_name=test_name,
        tabulate=tabulate,
        test_function=_not_contains_lines if revert else _contains_lines,
        test_type="not contains lines" if revert else "contains lines",
        serialize=True
    )
    
    
def EqualTest(
        result,
        pattern,
        task=-1,
        test_name=None,
        tabulate={},
        revert=False
    ):
    """
    Function to check that pattern equal to output from device. 
    
    Pattern can be of any type - string, list, dictionary, boolean etc.
    
    :param result: ``nornir.core.task.AggregatedResult`` object
    :param pattern: (any) any object to check equality for
    :param task: (str or int) name of task to check results for,
        can be list index instead, default is ``-1``, last task's results
    :param test_name: (str) descriptive name of the test
    :param tabulate: (dict or bool), if set to True, will use ``tabulate`` module
        to format results, or can be a dictionary of ``**kwargs`` to pass
        on to ``tabulate.tabulate`` method.
    :param revert: (bool) if True flips the logic to opposite - check if pattern
        not equal to results
    """    
    # form criteria and include in in results for ease of debugging
    criteria = pattern if len(pattern) < 25 else pattern[0:24]
    criteria = criteria.replace("\n", "\\n")
    
    def _equal(task_result, pattern, criteria, **kwargs):
        ret = {"criteria": criteria}
        if pattern != task_result["result"]:
            ret["result"] = "FAIL"
            ret["success"] = False    
            ret["error"] = "Criteria pattern and output not equal"
        return ret

    def _not_equal(task_result, pattern, criteria, **kwargs):
        ret = {"criteria": criteria}
        if pattern == task_result["result"]:
            ret["result"] = "FAIL"
            ret["success"] = False    
            ret["error"] = "Criteria pattern and output are equal"
        return ret
            
    return _run_test(
        result=result, 
        pattern=pattern,
        task=task,
        test_name=test_name,
        tabulate=tabulate,
        test_function=_not_equal if revert else _equal,
        test_type="not equal" if revert else "equal",
        criteria=criteria,
        serialize=True
    )
    

def CerberusTest(
        result,
        schema,
        task=-1,
        test_name=None,
        tabulate={},
        allow_unknown=True
    ):
    """
    Function to check results using ``Cerberus`` module schema. 
        
    :param result: ``nornir.core.task.AggregatedResult`` object
    :param schema: (dictionary) Cerberus schema definition to us for validation
    :param task: (str or int) name of task to check results for,
        can be list index instead, default is ``-1``, last task's results
    :param test_name: (str) descriptive name of the test
    :param tabulate: (dict or bool), if set to True, will use ``tabulate`` module
        to format results, or can be a dictionary of ``**kwargs`` to pass
        on to ``tabulate.tabulate`` method.
    :param allow_uncknown: (bool) Cerberus allow unknown parameter, default is True
    
    Cerberus itself can only run validation against dictionary structure,
    while nested elements could be lists. If task results is a list of dictionaries,
    ``CerberusTest`` function will iterate and test each individual list item
    """ 
    ret = []
    
    # run check
    if not HAS_CERBERUS:
        ret.append(
            {
                "host": "N/A",
                "test_name": test_name,
                "task": task,
                "result": "FAIL",
                "success": False,
                "error": "Cerberus lib not installed",
                "test_type": "Cerberus",
                "criteria": None
            }
        )        
        return ret
    
    validator_engine = Validator()
    validator_engine.allow_unknown = allow_unknown
        
    def _cerberus_test(task_result, schema, validator_engine, **kwargs):
        ret = {}
        # validate results as is if they are dictionary
        if isinstance(task_result["result"], dict):
            res = validator_engine.validate(document=task_result["result"], schema=schema)
            if not res:
                ret["result"] = "FAIL"
                ret["success"] = False    
                ret["error"] = validator_engine.errors
        # iterate over result items
        elif isinstance(task_result["result"], list):
            ret = []
            for item in task_result["result"]:
                if not isinstance(item, dict):
                    continue
                res = validator_engine.validate(document=item, schema=schema)
                if not res:
                    ret.append({
                        "result": "FAIL",
                        "success": False,    
                        "error": validator_engine.errors 
                    })
        return ret
            
    return _run_test(
        result=result, 
        schema=schema,
        task=task,
        test_name=test_name,
        tabulate=tabulate,
        test_function=_cerberus_test,
        test_type="cerberus",
        validator_engine=validator_engine,
        serialize=True
    )    
 

def _load_custom_fun_from_text(function_text, function_name):
    """
    Helper function to load custom function code from text using
    Python ``exec`` built-in function
    """
    assert function_name in function_text
        
    data = {}
    globals_dict = {
        "__builtins__": __builtins__,
        "False": False,
        "True": True,
        "None": None,
    }
    
    # load function by running exec
    exec(compile(function_text, "<string>", "exec"), globals_dict, data)
    
    # add extracted functions to globals for recursion to work
    globals_dict.update(data) 
    
    return data[function_name]
    
       
def CustomFunctionTest(        
        result,
        function_file=None,
        function_name="run",
        function_text=None,
        function_call=None,
        task=-1,
        test_name=None,
        tabulate={},
        test_type="custom",
        per_task=True,
        serialize=False,
        **kwargs
    ):
    """
    Wrapper around calling custom function to perform results checks.
    
    :param result: ``nornir.core.task.AggregatedResult`` object
    :param function_name: (str) function name, default is ``run``
    :param function_file: (str) OS path to file with ``function_name`` function
    :param function_text: (str) Python code text with ``function_name`` function
    :param function_call: (callable) reference to callable python function
    :param task: (str or int) name of task results of which should be checked,
        can be index of results instead, default is ``-1``, last task's results
    :param test_name: (str) name of the test
    :param tabulate: (dict or bool), if set to True, will use ``tabulate`` module
        to format results, alternatively can be a dictionary of ``**kwargs`` to pass
        on to ``tabulate.tabulate`` method.
    :param test_type: (str) description of check type performed
    :param per_task: (bool) default is True, runs on all host's results if False
    :param kwargs: additional ``**kwargs`` to pass on to custom function 
    :param serialize: (bool) default False, if True will serialize 
        results to dictionary using ``ResultSerializer`` function 
        before passing results to test function
    
    .. warning:: ``function_file`` and ``function_text`` uses ``exec`` function 
        to compile python code, using test functions from untrusted sources can 
        be dangerous.
        
    Custom functions should accept one positional argument to contain results
    to work with, any additional arguments can be accepted and passed using 
    ``CustomFunctionTest`` function call. If ``serialize`` argument was False,
    ``result`` will contain ``nornir.core.task.Result`` object, if ``serialize`` 
    was True, ``result`` will contain dictionary with task results produced
    by ``ResultSerializer`` function.
    
    Notes on ``per_task`` argument. If ``per_task`` set to True (default),
    only results (``nornir.core.task.Result`` object) for ``task`` specified 
    passed to test function, if ``per_task`` is False all host's results 
    (``nornir.core.task.MultiResult`` object) passed to test function. That 
    is useful when access to all host's results required.
    
    Custom function should return either a dictionary or a list of dictionaries, 
    in latter case, each list item added to overall results individually.
    
    Results dictionary should contain ``error``, ``result`` and ``success`` keys, 
    other keys can be included as well.
    
    Sample custom function::
    
        def fun_1(result):
            # result is nornir.core.task.Result object 
            # containing result for individual task
            if "7.7.7.8" not in result.result:
                return {
                    "error": "Server 7.7.7.8 not in config",
                    "result": "FAIL",
                    "success": False
                }
    """    
    ret = []
    test_function = None
    
    try:
        if function_text:
            test_function = _load_custom_fun_from_text(function_text, function_name)
        elif function_file:
            with open(function_file, encoding="utf-8") as f:
                test_function = _load_custom_fun_from_text(f.read(), function_name)
        elif function_call:
            test_function = function_call
    except:
        tb = traceback.format_exc()
        log.error("CustomFunctionTest error: {}".format(tb))
        return [
            {
                "host": "N/A",
                "test_name": test_name,
                "task": task,
                "result": "FAIL",
                "success": False,
                "error": str(tb),
                "test_type": "N/A",
                "criteria": "N/A"
            }
        ]
        
    return _run_test(
        result=result, 
        task=task,
        test_name=test_name,
        tabulate=tabulate,
        test_function=test_function,
        test_type=test_type,
        per_task=per_task,
        serialize=serialize,
        **kwargs
    )    
    

def _print_results(data):
    """
    Helper function to add coloring to tabulate output for 
    RunTestSuite function.
    """
    try:
        from colorama import init
        
        init()
    except ImportError:
        log.error("_print_results failed importing colorama, install it to have output colorized")
        
    if not isinstance(data, str):
        return 
        
    R = "\033[0;31;40m" # RED
    G = "\033[0;32;40m" # GREEN
    N = "\033[0m" # Reset
    fttr = "{}{}{}" # formatter
    green_words = ["True", "PASS"]
    red_words = ["False", "FAIL"]
    
    # add coloring to output
    for red_word in red_words:
        data = data.replace(red_word, fttr.format(R, red_word, N))
    for green_word in green_words:
        data = data.replace(green_word, fttr.format(G, green_word, N))
        
    print(data)
    

def RunTestSuite(
        result,
        suite,
        tabulate={},
        print_results=False,
        failed_only=False
    ):
    """
    Function that iterates over test cases defined in a test suite.
    
    :param result: ``nornir.core.task.AggregatedResult`` object
    :param suite: (list) list of dictionaries, where each dictionary 
        describes individual test
    :param tabulate: (dict or bool), if set to True, will use ``tabulate`` module
        to format results, alternatively can be a dictionary of ``**kwargs`` to pass
        on to ``tabulate.tabulate`` method.
    :param print_results: (bool), default is False, if True will print results
        to terminal screen using ``Colorama`` to colorize them
    :param failed_only: (bool) default is False, if True will return failed tests only
    
    Suite dictionary arguments::
    
        {
            "test": (mandatory) name of test to do, reference list below for valid names,
            "task": (optional) name or index of results task to test,
            "test_name": (optional) descriptive name of test,
            "result": (optional) nornir.core.task.AggregatedResult object reference
            "**kwargs": any additional arguments supported by "test" function
        }
        
    To simplify functions calls, ``RunTestSuite`` implements these set of aliases
    for ``test`` argument:
    
    * ``contains`` calls ``ContainsTest``
    * ``!contains`` calls ``ContainsTest`` with  kwargs: ``{"revert": True}``
    * ``contains_lines`` calls ``ContainsLinesTest``
    * ``!contains_lines`` calls ``ContainsLinesTest`` with kwargs: ``{"revert": True}``
    * ``contains_re`` calls ``ContainsTest`` with kwargs: ``{"use_re": True}``
    * ``!contains_re`` calls ``ContainsTest`` with kwargs: ``{"revert": True, "use_re": True}``
    * ``equal`` calls ``EqualTest``
    * ``!equal`` calls  ``EqualTest`` with kwargs: ``{"revert": True}``
    * ``cerberus`` calls ``CerberusTest``   
    * ``custom`` calls ``CustomFunctionTest``
    
    In addition to aliases, ``test`` argument can reference actual functions names:
    
    * ``ContainsTest`` calls ``ContainsTest``
    * ``ContainsLinesTest`` calls ``ContainsLinesTest``
    * ``EqualTest`` calls ``EqualTest``
    * ``CerberusTest`` calls ``CerberusTest``
    * ``CustomFunctionTest`` calls ``CustomFunctionTest``
    """
    ret = []
    
    # dictionary with check functions convenience names
    test_funcs_dispatcher = {
        "contains": {"fun": ContainsTest},
        "!contains": {"fun": ContainsTest, "kwargs": {"revert": True}},
        "contains_lines": {"fun": ContainsLinesTest},
        "!contains_lines": {"fun": ContainsLinesTest, "kwargs": {"revert": True}},
        "contains_re": {"fun": ContainsTest, "kwargs": {"use_re": True}},
        "!contains_re": {"fun": ContainsTest, "kwargs": {"revert": True, "use_re": True}},
        "equal": {"fun": EqualTest},
        "!equal": {"fun": EqualTest, "kwargs": {"revert": True}},
        "cerberus": {"fun": CerberusTest},   
        "custom": {"fun": CustomFunctionTest},
    }
    
    # run checks
    for test_case in suite:
        # add results data to test to test_case dictionary
        test_case.setdefault("result", result)
        try:
            _ = test_case.pop("tabulate", None)
            test_func_name = test_case.pop("test")
            # get check function reference
            if test_func_name in globals():
                ret += globals()[test_func_name](**test_case)
            elif test_func_name in test_funcs_dispatcher:
                test_func = test_funcs_dispatcher[test_func_name]["fun"]
                fun_kwargs = test_funcs_dispatcher[test_func_name].get("kwargs", {})
                test_case.update(fun_kwargs)
                ret += test_func(**test_case)
        except:
            tb = traceback.format_exc()
            log.error("Nornir Tests RunTestSuite error: {}".format(tb))
            ret.append(
                {
                    "host": "N/A",
                    "test_name": "N/A",
                    "task": "N/A",
                    "result": "FAIL",
                    "success": False,
                    "error": str(tb),
                    "test_type": "N/A",
                    "criteria": str(test_case)
                }
            )
    
    # check of only need to return results for failed tests
    if failed_only:
        ret = [i for i in ret if i["success"] == False]
        
    # check if need to use tabulate to format return results
    if tabulate and HAS_TABULATE:
        ret = tabulate_formatter(ret, tabulate)
        # print results if requested to do so
        if print_results:
            _print_results(ret)
        
    return ret