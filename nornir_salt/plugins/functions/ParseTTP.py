"""
TTP Parser
##########

TTP (Template Text Parser) is a module for parsing semi-structured 
text. This function can iterate over and parse results text output,
transforming them in structured data.

Dependencies:

* `TTP module <https://pypi.org/project/ttp/>`_ to perform text parsing

Sample usage::

    from nornir_salt import ParseTTP
    
    
    
.. autofunction:: nornir_salt.plugins.functions.ParseTTP.ParseTTP
"""
import logging
import traceback

log = logging.getLogger(__name__)

try:
    from ttp import ttp

    HAS_TTP = True
except ImportError:
    log.error("Failed to import TTP library, install: pip install ttp")
    HAS_TTP = False


def ParseTTP(
    ttp_template, result=None, nornir=None, task=-1, ttp_kwargs={}, res_kwargs={}
):
    """
    This function takes task results object and parse individual task
    results.

    :param ttp_template: (str) TTP template text
    :param result: ``nornir.core.task.AggregatedResult`` object with
        task's results
    :param nornir: reference to Nornir object
    :param task: (str) name or index of task to parse results for
    :param ttp_kwargs: (dict) arguments to pass onto TTP object instantiation
    :param res_kwargs: (dict) arguments to use with TTP parser object
        ``result`` method

    .. warning:: ParseTTP takes result object and substitutes task's output
        with parsing results, original output discarded.
    """
    if not HAS_TTP:
        log.error("ParseTTP error - seems failed to import TTP library")
        return result

    if result:
        # iterate over hosts results and run parsing
        for hostname, results in result.items():

            # get task results by task name
            if isinstance(task, str):
                for index, i in enumerate(results):
                    if i.name == task:
                        task_result = i.result
                        task_index = index
                        break
            # get task results by task index
            elif isinstance(task, int):
                task_result = results[task].result
                task_index = task

            # run sanity checks
            if not isinstance(task_result, str):
                log.error(
                    "ParseTTP host '{}', task '{}', result not string but '{}' type".format(
                        hostname, task, type(task_result)
                    )
                )
                continue

            # run parsing
            try:
                parser = ttp(task_result, ttp_template, **ttp_kwargs)
                parser.parse(one=True)
                results[task_index].result = parser.result(**res_kwargs)
            except:
                tb = traceback.format_exc()
                log.error("ParseTTP error: {}".format(tb))

    return result
