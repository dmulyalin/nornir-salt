"""
MakePlugin
##########

Function to generate Nornir plugin boilerplate code.

Reference
=========

.. autofunction:: nornir_salt.utils.MakePlugin.MakePlugin
"""
from typing import Optional

template_nornir_task_plugin = '''import time
import logging

from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command

log = logging.getLogger(__name__)

# Define connection name for RetryRunner to properly detect it
CONNECTION_NAME = "netmiko"


def task(task: Task, commands: list, interval: int = 1, **kwargs) -> Result:
    """
    Sample Nornir Task function to send show commands to devices using
    ``nornir_netmiko.tasks.netmiko_send_command`` plugin.

    :param kwargs: Arguments for ``nornir_netmiko.tasks.netmiko_send_command`` plugin.
    :param commands: List of commands to send to the device.
    :param interval: Interval between sending commands, default is 1 second.
    :return: Nornir result object with task execution results named after commands.

    Sample Usage:

        salt nrp1 nr.task salt://path/to/task_file.py commands='["show clock", "show hostname"]'
    """
    task.name = "{name}"
    log.info("Starting '{}' task for host '{}'".format(task.name, task.host.name))

    for command in commands:
        task.run(
            task=netmiko_send_command,
            command_string=command,
            name=command,
            **kwargs
        )
        time.sleep(interval)

    # Skip_results is True for ResultSerializer to skip main task results which are empty
    return Result(host=task.host, skip_results=True)

'''

template_testsprocessor_custom_test_fun = '''from nornir.core.task import Result, MultiResult

def run(result: Result) -> list:
    """
    Custom test function to test device output.

    Sample usage:

        salt nrp1 nr.test suite="salt://tests/sample_suite.txt" table=brief

    Where sample_suite.txt content:

        - test: custom
          function_file: "salt://tests/{name}.py"
          name: test_cust_fun_various_inputs_list_of_result
          task:
            - show clock
            - show ip int brief
    """
    ret = []
    # Handle single result item
    if isinstance(result, Result):
        if "Clock source: NTP" not in result.result:
            ret.append(
                {
                    "exception": "NTP not synced",
                    "result": "FAIL",
                    "success": False
                }
            )
    # Handle list of Result objects or MultiResult object
    elif isinstance(result, (MultiResult, list)):
        for item in result:
            if item.name == "show clock":
                if "Clock source: NTP" not in item.result:
                    ret.append(
                        {
                            "exception": "NTP not synced cust fun 3",
                            "result": "FAIL",
                            "success": False,
                        }
                    )
            elif item.name == "show ip int brief":
                if "10.10.10.10" not in item.result:
                    ret.append(
                        {
                            "exception": "10. IP not configured",
                            "result": "FAIL",
                            "success": False,
                        }
                    )
    else:
        raise TypeError("Unsupported result type '{}'".format(type(result)))
    return ret

'''

template_testsprocessor_custom_fun_suite = """
- test: custom
  function_file: "salt://tests/{filename}"
  name: test_cust_fun_various_inputs_list_of_result
  task:
    - show clock
    - show ip int brief
- test: custom
  function_file: "salt://tests/{filename}"
  use_all_tasks: True
  name: test_cust_fun_various_inputs_multiresult
  task:
    - show clock
    - show ip int brief
- test: custom
  function_file: "salt://tests/{filename}"
  task: show clock
  name: test_cust_fun_various_inputs_single_result
"""


def MakePlugin(kind: str, name: Optional[str] = None) -> str:
    """
    Function to generate boilerplate code for Nornir plugins.

    :param kind: Plugin kind to generate code for.
    :param name: Plugin file name to use.
    :return: Message indicating the generated plugin.

    Supported plugin kinds:

    * ``task`` - Creates Nornir task plugin in the current directory.
    * ``test`` - Creates ``TestsProcessor`` custom test function in the current directory.

    Sample usage:

        salt-run nr.make_plugin dir
        salt-run nr.make_plugin ?
        salt-run nr.make_plugin task name=run_check_commands
    """
    supported_kinds = ["task", "test"]
    if kind in ["dir", "?"]:
        return "Can generate code for plugins: {}".format(", ".join(supported_kinds))
    elif kind == "task":
        name = name or "nornir_custom_task"
        filename = f"{name}.py"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(template_nornir_task_plugin.format(name=name))
        return f"Generated task plugin '{filename}'"
    elif kind == "test":
        name = name or "TestsProcessor_custom_test"
        filename = f"{name}.py"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(template_testsprocessor_custom_test_fun.format(name=name))
        return f"Generated test function '{filename}', sample tests suite:\n{template_testsprocessor_custom_fun_suite.format(filename=filename)}"
    else:
        raise ValueError(
            f"Unsupported kind '{kind}', supported: {', '.join(supported_kinds)}"
        )
