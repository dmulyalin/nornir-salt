"""
salt_clear_hcache
#################

Task to clear hosts' task results cache stored  in data. This task
plugin does not have much practical applicability outside of
SaltStack environment.

salt_clear_hcache sample usage
==============================

Sample code to run ``salt_clear_hcache`` task::

    import pprint
    from nornir import InitNornir
    from nornir_salt.plugins.tasks import salt_clear_hcache

    nr = InitNornir(config_file="config.yaml")

    result = NornirObj.run(
        task=salt_clear_hcache,
        cache_keys=["cache_key1", "cache_key2"]
    )

    result_dictionary = ResultSerializer(result)

    pprint.pprint(result_dictionary)


salt_clear_cache returns dictionary of cleared cache keys with status

- True - cache key deleted
- False - cache key not found

salt_clear_cache reference
==========================

.. autofunction:: nornir_salt.plugins.tasks.salt_clear_hcache.salt_clear_hcache
"""
import logging
from typing import List

from nornir.core.task import Result, Task

log = logging.getLogger(__name__)


def salt_clear_hcache(task: Task, cache_keys: List = None, **kwargs) -> Result:
    """
    Function to iterate over provided cache keys and delete them from hosts's data.

    :param cache_keys: (list or str) list of cache keys to clean from host's data,
        if ``cache_keys`` argument not provided removes all cached data
    :returns: (dict) dictionary keyed by cache key and True/False status
    """
    result = {}

    if cache_keys is None:
        # need to itearete over a copy of the keys - list() makes a copy
        cache_keys = list(task.host.data.get("_hcache_keys_", []))

    log.debug(
        "nornir-salt:salt_clear_hcache removing hcache keys '{}'".format(cache_keys)
    )

    # iterate over given cache keys and clean them up from data
    for key in cache_keys:
        if key in task.host.data and key in task.host.data.get("_hcache_keys_", []):
            _ = task.host.data.pop(key)
            _ = task.host.data["_hcache_keys_"].remove(key)
            log.debug(
                "nornir-salt:salt_clear_hcache removed hcache key '{}'".format(key)
            )
            result[key] = True
        else:
            result[key] = False

    return Result(host=task.host, result=result)
