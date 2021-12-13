import yaml
import pprint
from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir_netmiko import netmiko_send_command
from nornir_salt.plugins.functions import ResultSerializer

inventory_data = """
hosts:
  R1:
    hostname: 192.168.1.151
    platform: ios
    groups: [lab]
  R2:
    hostname: 192.168.1.153
    platform: ios
    groups: [lab]
  R3:
    hostname: 192.168.1.154
    platform: ios
    groups: [lab]

groups:
  lab:
    username: cisco
    password: cisco
"""

inventory_dict = yaml.safe_load(inventory_data)

NornirObj = InitNornir(
    runner={"plugin": "QueueRunner", "options": {"num_workers": 100}},
    inventory={
        "plugin": "DictInventory",
        "options": {
            "hosts": inventory_dict["hosts"],
            "groups": inventory_dict["groups"],
            "defaults": inventory_dict.get("defaults", {}),
        },
    },
)


def _task_group_netmiko_send_commands(task: Task, commands):
    # run commands
    for command in commands:
        task.run(task=netmiko_send_command, command_string=command, name=command)
    return Result(host=task.host)


# run single task
result1 = NornirObj.run(task=netmiko_send_command, command_string="show clock")

# run grouped tasks
result2 = NornirObj.run(
    task=_task_group_netmiko_send_commands,
    commands=["show clock", "show run | inc hostname"],
)

# run another single task
result3 = NornirObj.run(
    task=netmiko_send_command, command_string="show run | inc hostname"
)

NornirObj.close_connections()

# Print results
formed_result1 = ResultSerializer(result1, add_details=True)
pprint.pprint(formed_result1, width=100)

formed_result2 = ResultSerializer(result2, add_details=True)
pprint.pprint(formed_result2, width=100)

formed_result3 = ResultSerializer(result3, add_details=True)
pprint.pprint(formed_result3, width=100)
