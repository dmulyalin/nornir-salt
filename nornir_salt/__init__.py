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
from .plugins.functions import TabulateFormatter
from .plugins.functions import DumpResults
from .plugins.functions import InventoryFun

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
from .plugins.tasks import http_call
from .plugins.tasks import file_read, file_list, file_remove, file_diff, files
from .plugins.tasks import connections, conn_close, conn_list
from .plugins.tasks import ncclient_call
from .plugins.tasks import scrapli_netconf_call
from .plugins.tasks import pygnmi_call
from .plugins.tasks import salt_clear_hcache
from .plugins.tasks import napalm_send_commands
from .plugins.tasks import sleep
from .plugins.tasks import pyats_send_commands
from .plugins.tasks import pyats_send_config
from .plugins.tasks import pyats_genie_api

# connections plugins
from .plugins.connections import NcclientPlugin
from .plugins.connections import HTTPPlugin
from .plugins.connections import PyGNMIPlugin
from .plugins.connections import ConnectionsPool
from .plugins.connections import PyATSUnicon

# processors plugins
from .plugins.processors import ToFileProcessor
from .plugins.processors import TestsProcessor
from .plugins.processors import DiffProcessor
from .plugins.processors import DataProcessor
from .plugins.processors import SaltEventProcessor

__all__ = (
    "ResultSerializer",
    "FFun",
    "DictInventory",
    "QueueRunner",
    "RetryRunner",
    "tcp_ping",
    "netmiko_send_commands",
    "netmiko_send_command_ps",
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
    "HTTPPlugin",
    "http_call",
    "file_read",
    "file_list",
    "file_remove",
    "file_diff",
    "files",
    "DumpResults",
    "connections",
    "conn_close",
    "conn_list",
    "PyGNMIPlugin",
    "pygnmi_call",
    "DataProcessor",
    "salt_clear_hcache",
    "napalm_send_commands",
    "ConnectionsPool",
    "sleep",
    "SaltEventProcessor",
    "PyATSUnicon",
    "pyats_send_commands",
    "pyats_send_config",
    "InventoryFun",
    "pyats_genie_api",
)
