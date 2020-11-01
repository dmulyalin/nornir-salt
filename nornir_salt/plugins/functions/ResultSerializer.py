def ResultSerializer(nr_results, add_details=False):
    """
    Helper function to transform Nornir results in dictionary

    :parap add_details: boolean to indicate if results should contain more info
    """
    ret = {}
    for hostname, results in nr_results.items():
        ret[hostname] = {}
        for i in results:
            # skip task groups such as _task_foo_bar
            if i.name.startswith("_"):
                continue
            # handle errors info passed from within tasks
            elif i.host.get("exception"):
                ret[hostname][i.name] = {"exception": i.host["exception"]}
            # add results details if requested to do so
            elif add_details:
                ret[hostname][i.name] = {
                    "diff": i.diff,
                    "changed": i.changed,
                    "result": i.result,
                    "failed": i.failed,
                    "exception": str(i.exception),
                }
            # form results for the rest of tasks
            else:
                ret[hostname][i.name] = (
                    {"exception": i.exception} if i.failed else i.result
                )
    return ret