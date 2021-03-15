"""
netmiko_send_commands
#####################

This test plugin uses ``nornir-netmiko`` ``netmiko_send_command`` task 
to send multiple commands to devices.

Dependencies:

* `nornir-netmiko module <https://pypi.org/project/nornir-netmiko/>`_ required

netmiko_send_commands sample usage
==================================

Code to invoke ``netmiko_send_commands`` task::

    from nornir_salt import netmiko_send_commands
    
    output = nr.run(
        task=netmiko_send_commands,
        commands=["show run", "show clock"],
        netmiko_kwargs={}
    )
	
netmiko_send_commands returns
=============================

Returns Nornir results object with individual tasks names set
equal to commands sent to device.

netmiko_send_commands reference
===============================

.. autofunction:: nornir_salt.plugins.tasks.netmiko_send_commands.netmiko_send_commands
"""
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "netmiko"

def netmiko_send_commands(task, commands, **kwargs):
    """
    Nornir Task function to send show commands to devices using
    ``nornir_netmiko.tasks.netmiko_send_command`` plugin

    :param kwargs: might contain ``netmiko_kwargs`` argument dictionary
        with parameters for ``nornir_netmiko.tasks.netmiko_send_command`` 
        method
    :param commands: (list) commands to send to device
    :return result: Nornir result object with task execution results
    """
    for command in commands:
        task.run(
            task=netmiko_send_command,
            command_string=command,
            name=command,
            **kwargs.get("netmiko_kwargs", {})
        )
    return Result(host=task.host)
