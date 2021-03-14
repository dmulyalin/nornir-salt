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
         for ``nornir_netmiko.tasks.netmiko_send_command`` method
    :param config: (list) commands list to send to device(s)
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
