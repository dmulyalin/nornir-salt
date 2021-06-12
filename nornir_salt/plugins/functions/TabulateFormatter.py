"""
TabulateFormatter function
##########################

Function to transform results in a text table format using Tabulate module.

Dependencies:

* Nornir 3.0 and beyond
* `Tabulate module <https://pypi.org/project/tabulate/>`_ for results table formatting

Sample code to use TabulateFormatter::

    TBD

Reference
=========

.. autofunction:: nornir_salt.plugins.functions.TabulateFormatter.TabulateFormatter
"""
import logging
import traceback
from nornir.core.task import AggregatedResult
from .ResultSerializer import ResultSerializer

log = logging.getLogger(__name__)

try:
    import tabulate as tabulate_lib
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False
    log.error("Failed to import tabulate library, install it: pip install tabulate")

def TabulateFormatter(result, tabulate=True, headers="keys"):
    """
    Function to format results in a text table.

    :param result: list of dictionaries or ``nornir.core.task.AggregatedResult`` object
    :param tabulate: (dict or str or bool) controls tabulate behaviour
    :param headers: (list) list of table headers, comma-sepated string of headers or
        one of tabulate supported values, e.g. ``keys``

    Supported values for ``tabulate`` attribute:

    * ``brief`` - uses tablefmt grid, showindex True and headers - host, name, result, exception to form table
    * ``True`` - uses headers provided or keys by default, no other formatting
    * ``dict`` - ``**tabulate`` passed on to ``tabulate.tabulate`` method
    """
    if not HAS_TABULATE:
        log.error("nornir-salt:TabulateFormatter failed import tabulate library, install: pip install tabulate")
        return result

    # decide on results to tabulate
    if isinstance(result, AggregatedResult):
        result_to_tabulate = ResultSerializer(result, add_details=True, to_dict=False)
    elif isinstance(result, list):
        result_to_tabulate = result
    else:
        log.error("nornir-salt:TabulateFormatter unsupported results type '{}', supported - list or AggregatedResult".format(type(result)))
        return result

    # check headers
    if isinstance(headers, str) and "," in headers:
        headers = [i.strip() for i in headers.split(",")]

    # form tabulate parameters
    if tabulate == "brief":
        tabulate = {"tablefmt": "grid", "showindex": True, "headers": ["host", "name", "result", "exception"]}
    elif tabulate == True:
        tabulate = {"headers": headers}
    elif isinstance(tabulate, dict):
        tabulate.setdefault("headers", headers)
    else:
        log.error("nornir-salt:TabulateFormatter unsupported tabulate argument type '{}', supported - 'brief', bool, dict".format(type(tabulate)))
        return result

    # transform result_to_tabulate to list of lists
    if isinstance(tabulate["headers"], list):
        result_to_tabulate = [
            [item.get(i, "") for i in tabulate["headers"]]
            for item in result_to_tabulate
        ]

    return tabulate_lib.tabulate(result_to_tabulate, **tabulate)