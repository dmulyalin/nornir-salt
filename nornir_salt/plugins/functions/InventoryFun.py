"""
InventoryFun
############

Function to interact with in memory Nornir Inventory data.

InventoryFun Sample Usage
===========================

Sample code to invoke ``InventoryFun`` function::

    TBD

InventoryFun reference
========================

.. autofunction:: nornir_salt.plugins.functions.InventoryFun.InventoryFun
"""
import logging
import traceback

log = logging.getLogger(__name__)

def _create_host(nr):
    pass

def _read_host(nr):
    pass

def _update_host(nr):
    pass

def _delete_host(nr):
    pass

def _load(nr):
    """
    Accept a list of items, where each item executed sequentially
    to perform one of the operations to create, update or delete.
    """
    pass

def InventoryFun(nr, call, **kwargs):
    """
    Dispatcher function to execute one of ``call`` functions.
    
    :param nr: (obj) Nornir object
    :param call: (str) name of function to call
    :param kwargs: (dict) arguments to pass on to call function
    :returns: None
    """
    pass
