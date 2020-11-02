# nornir-salt
Collection of Nornir plugins used with SALTSTACK Nornir modules - proxy, execution. 

All plugins and functions can be used with Nornir directly as well.

# Installation

```
pip install nornir_salt
```

# Plugins

## Runner plugins

- **QueueRunner** - simple queue runner
- **RetryRunner** - runner that implements retry logic for connections and tasks, supports connecting to devices behind jumphost

## Inventory plugins

- **DictInventory** - Inventory plugin that accepts dictionary structure to populate hosts' inventory

## Functions

- **ResultSerializer** - helper function to transform AggregatedResult object in Python dictionary

# Details

Additional details about how it works and usage samples

## QueueRunner, DictInventory and ResultSerializer example

**Architecture**
<img src="assets/QueueRunner_v0.png">  

Sample code to use QueueRunner, DictInventory and ResultSerializer

<details><summary>Code</summary>

```python
import yaml
import pprint
from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir_netmiko import netmiko_send_command, netmiko_send_config
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
    runner={
        "plugin": "QueueRunner",
        "options": {
            "num_workers": 100
        }
    },
    inventory={
        "plugin": "DictInventory",
        "options": {
            "hosts": inventory_dict["hosts"],
            "groups": inventory_dict["groups"],
            "defaults": inventory_dict.get("defaults", {})
        }
    },
)

def _task_group_netmiko_send_commands(task, commands):
    # run commands
    for command in commands:
        task.run(
            task=netmiko_send_command,
            command_string=command,
            name=command
        )
    return Result(host=task.host)
    
# run single task
result1 = NornirObj.run(
    task=netmiko_send_command, 
    command_string="show clock"
)

# run grouped tasks
result2 = NornirObj.run(
    task=_task_group_netmiko_send_commands, 
    commands=["show clock", "show run | inc hostname"]
)

# run another single task
result3 = NornirObj.run(
    task=netmiko_send_command, 
    command_string="show run | inc hostname"
)

NornirObj.close_connections()

# Print results
formed_result1 = ResultSerializer(result1, add_details=True)
pprint.pprint(formed_result1, width=100)

formed_result2 = ResultSerializer(result2, add_details=True)
pprint.pprint(formed_result2, width=100)

formed_result3 = ResultSerializer(result3, add_details=True)
pprint.pprint(formed_result3, width=100)
```
</details>

## RetryRunner, DictInventory and ResultSerializer example

> For grouped tasks need to explicitly provide `connection_name` attribute such as `netmik`, `napalm`, `scrapli`. Specifying `connection_name` attribute for standalone tasks not required. Lack of `connection_name` attribute will resultin skipping connection retry logic and connections to all hosts will be initiated simultaneously up to a number of `num_workers`

**Architecture**
<img src="assets/RetryRunner_v0.png">  

Sample code to use RetryRunner, DictInventory and ResultSerializer

<details><summary>Code</summary>

```python
import yaml
import pprint
from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir_netmiko import netmiko_send_command, netmiko_send_config
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
    runner={
        "plugin": "RetryRunner",
        "options": {
            "num_workers": 100,
            "num_connectors": 10,
            "connect_retry": 3,
            "connect_backoff": 1000,
            "connect_splay": 100,
            "task_retry": 3,
            "task_backoff": 1000,
            "task_splay": 100
        }
    },
    inventory={
        "plugin": "DictInventory",
        "options": {
            "hosts": inventory_dict["hosts"],
            "groups": inventory_dict["groups"],
            "defaults": inventory_dict.get("defaults", {})
        }
    },
)

def _task_group_netmiko_send_commands(task, commands):
    # run commands
    for command in commands:
        task.run(
            task=netmiko_send_command,
            command_string=command,
            name=command
        )
    return Result(host=task.host)
    
# run single task
result1 = NornirObj.run(
    task=netmiko_send_command, 
    command_string="show clock"
)

# run grouped tasks
result2 = NornirObj.run(
    task=_task_group_netmiko_send_commands, 
    commands=["show clock", "show run | inc hostname"],
    connection_name="netmiko"
)

# run another single task
result3 = NornirObj.run(
    task=netmiko_send_command, 
    command_string="show run | inc hostname"
)

NornirObj.close_connections()

# Print results
formed_result1 = ResultSerializer(result1, add_details=True)
pprint.pprint(formed_result1, width=100)

formed_result2 = ResultSerializer(result2, add_details=True)
pprint.pprint(formed_result2, width=100)

formed_result3 = ResultSerializer(result3, add_details=True)
pprint.pprint(formed_result3, width=100)
```
</details>

## Connect to hosts behind jumphost

Only Netmiko connections, `connection_name="netmiko"`, supports connecting via Jumphosts.

To connect to devices behind jumphost, need to define jumphost parameters in host's inventory data:

<details><summary>Code</summary>

```python
inventory_data = """
hosts:
  R1:
    hostname: 192.168.1.151
    platform: ios
    groups: [lab]
    data: 
      jumphost:
        hostname: 10.1.1.1
        port: 22
        password: jump_host_password
        username: jump_host_user
"""
```
</details>