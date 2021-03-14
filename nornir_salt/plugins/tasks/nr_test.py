from nornir.core.task import Result

def nr_test(task, ret_data_per_host={}, ret_data="__undefined_value__", **kwargs):
    """
    Dummy task that echoes data passed to it. Useful to debug and
    verify Nornir object operation

    :param ret_data_per_host: (dict) Dictionary keyed by host name with
        values to include in results
    :param ret_data: Any data to include in results
    :param kwargs: Any key-value pair to include in results
    :return result: ``ret_data`` or ``**kwargs`` passed to the task
    
    Order of preference of return data:
    
    1. ``ret_data_per_host`` included in results 
    2. ``ret_data`` included in results 
    3. ``**kwargs`` included in results 
    """
    if ret_data_per_host:
        return Result(host=task.host, result=ret_data_per_host.get(task.host.name, None))
    elif ret_data != "__undefined_value__":
        return Result(host=task.host, result=ret_data)
    else:
        return Result(host=task.host, result=kwargs)