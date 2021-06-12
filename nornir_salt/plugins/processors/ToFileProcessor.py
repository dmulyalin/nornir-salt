"""
ToFileProcessor Plugin
######################

Processor plugin to save task execution results to file.

ToFileProcessor Sample Usage
============================

Code to demonstrate how to use ``ToFileProcessor`` plugin::

    from nornir import InitNornir
    from nornir_netmiko import netmiko_send_command
    from nornir_salt import ToFileProcessor
    
    nr = InitNornir(config_file="config.yaml")
    
    nr_with_processor = nr.with_processors([
        ToFileProcessor(
            tf="/tmp/31/{host_name}/cfg-%B_%d_%H_%M_%S.txt"
        )
    ])
    
    nr_with_processor.run(
        task=netmiko_send_command,
        command_string="show run"
    )

ToFileProcessor reference
=========================

.. autofunction:: nornir_salt.plugins.processors.ToFileProcessor.ToFileProcessor
"""
import logging
import time
import os
import json
import pprint
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from nornir_salt.plugins.functions import ResultSerializer


log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------
# formatters helper functions
# --------------------------------------------------------------------------------


def _to_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(",", ": "))

def _to_pprint(data):
    return pprint.pformat(data, indent=4)

def _to_yaml(data):
    if HAS_YAML:
        return yaml.dump(data, default_flow_style=False)
    else:
        return _to_pprint(data)

def _to_raw(data):
    return str(data)

# formats dispatcher dictionary
formatters = {
    "raw": _to_raw,
    "json": _to_json,
    "pprint": _to_pprint,
    "yaml": _to_yaml    
}


# --------------------------------------------------------------------------------
# main ToFile function
# --------------------------------------------------------------------------------


def _write(f, data, tf_format):
    """
    Helper function mainly to re-use code
    """
    try:
        f.write(formatters[tf_format](data)  + "\n")
    except KeyError:
        log.error("ToFile, unsupported format '{}'; supported '{}'".format(
                tf_format, list(formatters.keys())
            )
        )        
    
    
class ToFileProcessor:
    """
    ToFileProcessor can save task execution results to file.
    
    :param tf: (str) OS path to file where to save results
    :param tf_format: (str) formatter name to use on results before saving them
    :param add_details: (bool) maps to `ResultSerializer`` ``add_details`` attribute
    :param to_dict: (bool) maps to `ResultSerializer`` ``to_dict`` attribute
    :param base_url: (str) OS path to folder where to save files, concatenates with 
        ``tf`` attribute to form full path, default is "/var/nornir-salt/"
    :param tf_alias: (str) descriptive name of the file to reference it using diff processor
    
    ``tf`` attribute supports ``time.strftime`` directives, supports ``host_name`` 
    directive as well, for example::
        
        /path/to/dir/output_%B_%d_%H_%M_%S.txt
        /path/to/dir/output_{host_name}-%B_%d_%H_%M_%S.txt
        /path/to/{host_name}/output_%B_%d_%H_%M_%S.txt
    
    If ``{host_name}`` string present in ``tf`` attribute, results saved on 
    a per-host basis. Otherwise, results saved as is using provided ``tf_format`` 
    formatter after serializing results with ``ResultSerializer``.
    
    Supported ``tf_format`` values:
    
    * ``raw`` - (default) converts data to string appending newline to the end
    * ``pprint`` - uses ``pprint.pformat`` function to format data to string
    * ``json`` - formats data to JSON format
    * ``yaml`` - formats data to YAML format
    """
    
    def __init__(
        self, 
        tf, 
        tf_format="json", 
        add_details=True, 
        to_dict=True, 
        base_url="/var/nornir-salt/",
        tf_alias=None
    ):
        self.tf = tf if tf.startswith("/") else os.path.join(base_url, tf)
        self.aliases_file = os.path.join(base_url, "tf_aliases.json")
        self.aliases_data = {}
        self.tf_format = tf_format
        self.add_details = add_details
        self.to_dict = to_dict
        self.tf_alias = tf_alias
        
        if self.tf_alias:
            self._load_aliases()
        
    def _load_aliases(self):
        # create aliases file if does not exist
        if not os.path.exists(self.aliases_file):
            os.makedirs(os.path.dirname(self.aliases_file), exist_ok=True)
            with open(self.aliases_file, mode="w", encoding="utf-8") as f:
                f.write(json.dumps({}))
        
        # load aliases data
        with open(self.aliases_file, mode="r", encoding="utf-8") as f:
            self.aliases_data = json.loads(f.read())
            
    def _dump_aliases(self):
        # save aliases data
        with open(self.aliases_file, mode="w", encoding="utf-8") as f:
            _write(f, self.aliases_data, "json")      
    
    def task_started(self, task: Task) -> None:
        pass # ignore

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass # ignore

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """ save to file on a per-host basis """

        if "{host_name}" in self.tf:
            host_filename = time.strftime(self.tf).format(host_name=host.name)
            os.makedirs(os.path.dirname(host_filename), exist_ok=True)            
            with open(host_filename, mode="w", encoding="utf-8") as f:
                for i in result:
                    exception = str(i.exception) if i.exception != None else i.host.get("exception", None)
                    # check if need to skip this task results
                    if hasattr(i, "skip_results") and i.skip_results is True and not exception:
                        continue
                    else:
                        _write(f, i.result, self.tf_format)
            # save alias
            if self.tf_alias:
                self.aliases_data.setdefault(self.tf_alias, {})
                self.aliases_data[self.tf_alias].setdefault(host.name, [])
                if not host_filename in self.aliases_data[self.tf_alias][host.name]:
                    self.aliases_data[self.tf_alias][host.name].insert(0, host_filename)
                
    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore subtasks

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass  # ignore subtasks
        
    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """ save content of all hosts tasks to file """                
               
        if "{host_name}" not in self.tf:
            data = ResultSerializer(result, add_details=self.add_details, to_dict=self.to_dict)
            filename = time.strftime(self.tf)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, mode="w", encoding="utf-8") as f:
                _write(f, data, self.tf_format)
                
            # save alias
            if self.tf_alias:
                self.aliases_data.setdefault(self.tf_alias, {"all": []})
                if not filename in self.aliases_data[self.tf_alias]["all"]:
                    self.aliases_data[self.tf_alias]["all"].insert(0, filename)
                
        # save alises to the file after task completion
        if self.tf_alias:
            self._dump_aliases()
