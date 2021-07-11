"""
Overview
########

Nornir-salt package is a collection of plugins and functions to use together with Nornir framework.

Primary reason for developing nornir-salt is a need to extend Nornir functionality for the 
sake of salt-nornir proxy minion module. However, all plugins included in nornir-salt can
be used standalone unless stated otherwise.

While it was possible to include all the plugins into salt-nornir proxy module, decision was made
that many of the plugins developed can be useful outside of salt-nornir proxy module scope.
"""
# misc functions
from .plugins.functions import ResultSerializer
from .plugins.functions import FFun
from .plugins.functions import FindString
from .plugins.functions import ParseTTP
from .plugins.functions import TabulateFormatter

# check functions
from .plugins.functions import ContainsTest
from .plugins.functions import ContainsLinesTest
from .plugins.functions import EqualTest
from .plugins.functions import CerberusTest
from .plugins.functions import RunTestSuite
from .plugins.functions import CustomFunctionTest

# inventory plugins
from .plugins.inventory import DictInventory

# runner plugins
from .plugins.runners import QueueRunner
from .plugins.runners import RetryRunner

# task plugins
from .plugins.tasks import tcp_ping
from .plugins.tasks import netmiko_send_commands
from .plugins.tasks import netmiko_send_command_ps
from .plugins.tasks import nr_test
from .plugins.tasks import salt_cfg_gen
from .plugins.tasks import scrapli_send_commands
from .plugins.tasks import netmiko_send_config
from .plugins.tasks import napalm_configure
from .plugins.tasks import scrapli_send_config

# NETCONF related plugins
from .plugins.tasks import ncclient_call
from .plugins.tasks import scrapli_netconf_call
from .plugins.connections import NcclientPlugin

# processors plugins
from .plugins.processors import ToFileProcessor
from .plugins.processors import TestsProcessor
from .plugins.processors import DiffProcessor

__all__ = (
    "ResultSerializer",
    "FFun",
    "FindString",
    "DictInventory",
    "QueueRunner",
    "RetryRunner",
    "tcp_ping",
    "ContainsTest",
    "EqualTest",
    "CerberusTest",
    "netmiko_send_commands",
    "netmiko_send_command_ps",
    "RunTestSuite",
    "CustomFunctionTest",
    "nr_test",
    "NcclientPlugin",
    "ncclient_call",
    "scrapli_netconf_call",
    "ToFileProcessor",
    "TestsProcessor",
    "TabulateFormatter",
    "DiffProcessor",
    "salt_cfg_gen",
    "scrapli_send_commands",
    "netmiko_send_config",
    "napalm_configure",
    "scrapli_send_config",
)
