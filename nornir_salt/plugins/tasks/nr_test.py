"""
nr_test
#######

Function to test Nornir operation and produce valid results
without the need to interact with devices directly.

nr_test sample usage
====================

Code to invoke ``nr_test`` task::

    from nornir_salt import nr_test

    output = nr.run(task=nr_test, abc=123)

nr_test returns
=============================

Returns Nornir results object with task results populated
in accordance with arguments supplied to task call.

nr_test reference
=================

.. autofunction:: nornir_salt.plugins.tasks.nr_test.nr_test
"""
from nornir.core.task import Result


def nr_test(
    task,
    ret_data_per_host=None,
    ret_data="__undefined_value__",
    excpt=None,
    excpt_msg="",
    **kwargs
):
    """
    Dummy task that echoes data passed to it. Useful to debug and
    verification of Nornir object operation.

    :param ret_data_per_host: (dict) Dictionary keyed by host name with
        values to include in results
    :param ret_data: Any data to include in results, same for each host
    :param kwargs: Any key-value pair to include in results, same for each host
    :return result: ``ret_data`` or ``**kwargs`` passed to the task
    :param excpt: (obj or True) exception object to raise; if True, raises ``RuntimeError``
    :param excpt_msg: (str) message to use with exception

    Order of preference of return data:

    1. If ``ret_data_per_host`` present, it is used to form results
    2. If ``excpt`` object supplied, it is raised
    3. If ``ret_data`` present, it is included in results
    4. If ``**kwargs`` supplied, they are included in results
    """
    ret_data_per_host = ret_data_per_host or {}

    if ret_data_per_host:
        return Result(
            host=task.host, result=ret_data_per_host.get(task.host.name, None)
        )
    elif excpt is True:
        raise RuntimeError(excpt_msg)
    elif excpt is not None:
        raise excpt(excpt_msg)
    elif ret_data != "__undefined_value__":
        return Result(host=task.host, result=ret_data)
    else:
        return Result(host=task.host, result=kwargs)
