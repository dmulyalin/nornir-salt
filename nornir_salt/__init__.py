"""
Overview
########

Nornir-salt package is a collection of plugins and functions to use together with Nornir framework. 

Primary reason for developing nornir-salt is a need to extend Nornir functionality for the 
sake of salt-nornir proxy minion module. However, all plugins included in nornir-salt can
be used standalone.

While it was possible to include all the plugins into salt-nornir proxy module, decision was made
that many of the features developed can be useful outside of salt-nornir proxy module scope.
"""
from .plugins.functions import ResultSerializer
from .plugins.functions import FFun
from .plugins.functions import FindString
from .plugins.inventory import DictInventory
from .plugins.runners import QueueRunner
from .plugins.runners import RetryRunner
from .plugins.tasks import tcp_ping

__all__ = (
    "ResultSerializer",
    "FFun",
    "FindString",
    "DictInventory",
    "QueueRunner",
    "RetryRunner",
    "tcp_ping"
)