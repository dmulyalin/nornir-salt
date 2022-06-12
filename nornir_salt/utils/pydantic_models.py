"""
File to contain pydantic models for plugins input/output data validation
"""
from nornir.core.task import Task
from nornir.core.inventory import Host
from enum import Enum
from pydantic import (
    BaseModel,
    StrictBool,
    StrictInt,
    StrictFloat,
    StrictStr,
    conlist,
    root_validator,
    Field,
)
from typing import Union, Optional, List, Any, Dict, Callable, Tuple


class model_ffun_fx_filters(BaseModel):
    FO: Optional[Union[Dict, List[Dict]]] = Field(None, title="Filter Object")
    FB: Optional[Union[List[str], str]] = Field(None, title="Filter gloB")
    FH: Optional[Union[List[StrictStr], StrictStr]] = Field(
        None, title="Filter Hostname"
    )
    FC: Optional[Union[List[str], str]] = Field(None, title="Filter Contains")
    FR: Optional[Union[List[str], str]] = Field(None, title="Filter Regex")
    FG: Optional[StrictStr] = Field(None, title="Filter Group")
    FP: Optional[Union[List[StrictStr], StrictStr]] = Field(None, title="Filter Prefix")
    FL: Optional[Union[List[StrictStr], StrictStr]] = Field(None, title="Filter List")
    FM: Optional[Union[List[StrictStr], StrictStr]] = Field(
        None, title="Filter platforM"
    )
    FX: Optional[Union[List[str], str]] = Field(None, title="Filter eXclude")
    FN: Optional[StrictBool] = Field(
        None, title="Filter Negate", description="Negate the match"
    )


class model_netmiko_send_commands(BaseModel):
    """Model for nornir_salt.plugins.tasks.netmiko_send_commands plugin arguments"""

    task: Task
    commands: Optional[Union[List[StrictStr], StrictStr]]
    interval: Optional[Union[StrictFloat, StrictInt]]
    use_ps: Optional[StrictBool]
    split_lines: Optional[StrictBool]
    new_line_char: Optional[StrictStr]
    repeat: Optional[StrictInt]
    stop_pattern: Optional[StrictStr]
    repeat_interval: Optional[StrictInt]
    return_last: Optional[StrictInt]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_nr_test(BaseModel):
    """Model for nornir_salt.plugins.tasks.nr_test plugin arguments"""

    task: Task
    ret_data_per_host: Optional[Dict[StrictStr, Any]]
    ret_data: Optional[Any]
    excpt: Optional[Union[StrictBool, Callable]]
    excpt_msg: Optional[StrictStr]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_napalm_send_commands(BaseModel):
    """Model for nornir_salt.plugins.tasks.netmiko_send_commands plugin arguments"""

    task: Task
    commands: Optional[Union[List[StrictStr], StrictStr]]
    interval: Optional[Union[StrictFloat, StrictInt]]
    new_line_char: Optional[StrictStr]
    split_lines: Optional[StrictBool]

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_conn_list(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.conn_list plugin arguments"""

    task: Task
    conn_name: Optional[StrictStr]

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_conn_close(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.conn_close plugin arguments"""

    task: Task
    conn_name: Optional[StrictStr]

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_conn_open(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.conn_open plugin arguments"""

    task: Task
    conn_name: StrictStr
    host: Optional[Host]
    hostname: Optional[StrictStr]
    username: Optional[StrictStr]
    password: Optional[StrictStr]
    port: Optional[StrictInt]
    platform: Optional[StrictStr]
    extras: Optional[Dict[StrictStr, Any]]
    default_to_host_attributes: Optional[StrictBool]
    close_open: Optional[StrictBool]
    reconnect: Optional[List]
    raise_on_error: Optional[StrictBool]

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class ConnectionsCallsEnum(str, Enum):
    connections_list = "ls"
    connections_open = "open"
    connections_close = "close"


class model_connections(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.connections plugin arguments"""

    task: Task
    call: ConnectionsCallsEnum

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_scrapli_send_commands(BaseModel):
    """Model for nornir_salt.plugins.tasks.scrapli_send_commands plugin arguments"""

    task: Task
    commands: Optional[Union[List[StrictStr], StrictStr]]
    interval: Optional[Union[StrictFloat, StrictInt]]
    split_lines: Optional[StrictBool]
    new_line_char: Optional[StrictStr]
    repeat: Optional[StrictInt]
    stop_pattern: Optional[StrictStr]
    repeat_interval: Optional[StrictInt]
    return_last: Optional[StrictInt]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_pyats_send_commands(BaseModel):
    """Model for nornir_salt.plugins.tasks.pyats_send_commands plugin arguments"""

    task: Task
    commands: Optional[Union[List[StrictStr], StrictStr]]
    interval: Optional[Union[StrictFloat, StrictInt]]
    new_line_char: Optional[StrictStr]
    split_lines: Optional[StrictBool]
    via: Optional[StrictStr]
    parse: Optional[StrictBool]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_pyats_genie_api(BaseModel):
    """Model for nornir_salt.plugins.tasks.pyats_genie_api plugin arguments"""

    task: Task
    api: StrictStr

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_salt_cfg_gen(BaseModel):
    """Model for nornir_salt.plugins.tasks.salt_cfg_gen plugin arguments"""

    task: Task
    config: Optional[StrictStr]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_file_read(BaseModel):
    """Model for nornir_salt.plugins.tasks.file_read plugin arguments"""

    task: Task
    filegroup: Union[StrictStr, List[StrictStr]]
    base_url: Optional[StrictStr] = "/var/nornir-salt/"
    task_name: Optional[StrictStr] = None
    last: Optional[StrictInt] = 1
    index: Optional[StrictStr] = "common"

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_file_list(BaseModel):
    """Model for nornir_salt.plugins.tasks.file_list plugin arguments"""

    task: Task
    filegroup: Optional[Union[StrictStr, List[StrictStr]]]
    base_url: Optional[StrictStr] = "/var/nornir-salt/"
    index: Optional[StrictStr] = "common"

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_file_remove(BaseModel):
    """Model for nornir_salt.plugins.tasks.file_remove plugin arguments"""

    task: Task
    filegroup: Union[StrictStr, List[StrictStr], StrictBool]
    base_url: Optional[StrictStr] = "/var/nornir-salt/"
    index: Optional[StrictStr] = "common"
    tf_index_lock: Optional[Any]

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_file_diff(BaseModel):
    """Model for nornir_salt.plugins.tasks.file_diff plugin arguments"""

    task: Task
    filegroup: Union[StrictStr, List[StrictStr]]
    base_url: Optional[StrictStr] = "/var/nornir-salt/"
    task_name: Optional[StrictStr]
    last: Optional[Union[StrictInt, List[StrictInt], StrictStr]]
    index: Optional[StrictStr] = "common"

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class FilesCallsEnum(str, Enum):
    files_ls = "ls"
    files_list = "list"
    files_rm = "rm"
    files_remove = "remove"
    files_delete = "delete"
    files_read = "read"
    files_diff = "diff"


class model_files(BaseModel):
    """Model for nornir_salt.plugins.tasks.files plugin arguments"""

    task: Task
    call: FilesCallsEnum

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_http_call(BaseModel):
    """Model for nornir_salt.plugins.tasks.http_call plugin arguments"""

    task: Task
    method: StrictStr
    url: Optional[StrictStr]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_napalm_configure(BaseModel):
    """Model for nornir_salt.plugins.tasks.napalm_configure plugin arguments"""

    task: Task
    config: Optional[Union[StrictStr, List[StrictStr]]]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_ncclient_call(BaseModel):
    """Model for nornir_salt.plugins.tasks.ncclient_call plugin arguments"""

    task: Task
    call: StrictStr

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_netmiko_send_config(BaseModel):
    """Model for nornir_salt.plugins.tasks.netmiko_send_config plugin arguments"""

    task: Task
    config: Optional[Union[StrictStr, List[StrictStr]]]
    commit: Optional[Union[Dict, StrictBool]]
    commit_final_delay: Optional[StrictInt]
    batch: Optional[StrictInt]
    enable: Optional[StrictBool]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_pyats_send_config(BaseModel):
    """Model for nornir_salt.plugins.tasks.pyats_send_config plugin arguments"""

    task: Task
    config: Optional[Union[StrictStr, List[StrictStr]]]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_pygnmi_call(BaseModel):
    """Model for nornir_salt.plugins.tasks.pygnmi_call plugin arguments"""

    task: Task
    call: StrictStr
    name_arg: Optional[StrictStr]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_pygnmi_call_delete(BaseModel):
    """Model for nornir_salt.plugins.tasks.pygnmi_call._call_delete plugin arguments"""

    path: List[StrictStr]

    class Config:
        extra = "allow"


class model_pygnmi_call_replace(BaseModel):
    """Model for nornir_salt.plugins.tasks.pygnmi_call._call_replace plugin arguments"""

    path: List[StrictStr]

    class Config:
        extra = "allow"


class model_pygnmi_call_update(BaseModel):
    """Model for nornir_salt.plugins.tasks.pygnmi_call._call_update plugin arguments"""

    path: List[StrictStr]

    class Config:
        extra = "allow"


class model_salt_clear_hcache(BaseModel):
    """Model for nornir_salt.plugins.tasks.salt_clear_hcache plugin arguments"""

    task: Task
    cache_keys: Optional[List[StrictStr]]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_scrapli_netconf_call(BaseModel):
    """Model for nornir_salt.plugins.tasks.scrapli_netconf_call plugin arguments"""

    task: Task
    call: StrictStr

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_scrapli_send_config(BaseModel):
    """Model for nornir_salt.plugins.tasks.scrapli_send_config plugin arguments"""

    task: Task
    config: Optional[Union[StrictStr, List[StrictStr]]]

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_sleep(BaseModel):
    """Model for nornir_salt.plugins.tasks.sleep plugin arguments"""

    task: Task
    sleep_for: Optional[StrictInt]
    sleep_random: Optional[Union[StrictInt, List[StrictInt], Tuple[StrictInt]]]

    class Config:
        arbitrary_types_allowed = True


class TestsProcessorTestFunctions(str, Enum):
    contains = "contains"
    not_contains = "!contains"
    ncontains = "ncontains"
    contains_lines = "contains_lines"
    not_contains_lines = "!contains_lines"
    ncontains_lines = "ncontains_lines"
    contains_re = "contains_re"
    not_contains_re = "!contains_re"
    ncontains_re = "ncontains_re"
    contains_lines_re = "contains_lines_re"
    not_contains_lines_re = "!contains_lines_re"
    ncontains_lines_re = "ncontains_lines_re"
    equal = "equal"
    not_equal = "!equal"
    nequal = "nequal"
    cerberus = "cerberus"
    custom = "custom"
    eval_fun = "eval"
    ContainsTest = "ContainsTest"
    ContainsLinesTest = "ContainsLinesTest"
    EqualTest = "EqualTest"
    CerberusTest = "CerberusTest"
    CustomFunctionTest = "CustomFunctionTest"
    EvalTest = "EvalTest"


class modelTestsProcessorTest(BaseModel):
    """Model for TestsProcessor single test dictionary item"""

    test: TestsProcessorTestFunctions
    name: Optional[StrictStr]
    task: Optional[Union[StrictStr, List[StrictStr]]]
    err_msg: Optional[StrictStr]
    path: Optional[StrictStr]
    report_all: Optional[StrictBool]
    use_all_tasks: Optional[StrictBool]
    # Contains and Equal tests parameters
    pattern: Optional[Union[StrictStr, Any]]
    use_re: Optional[StrictBool]
    count: Optional[StrictInt]
    count_ge: Optional[StrictInt]
    count_le: Optional[StrictInt]
    revert: Optional[StrictBool]
    # CustomFunctionTest parameters
    function_file: Optional[StrictStr]
    function_text: Optional[StrictStr]
    function_call: Optional[Callable]
    function_name: Optional[StrictStr]
    function_kwargs: Optional[Dict]
    globals_dictionary: Optional[Dict]
    add_host: Optional[StrictBool]
    # CerberusTest parameters
    _schema: Optional[StrictStr] = Field(alias="schema")
    allow_unknown: Optional[StrictBool]
    # EvalTest parameters
    expr: Optional[StrictStr]
    globs: Optional[Dict]

    class Config:
        extra = "allow"

    @root_validator(pre=True)
    def check_commands_given(cls, values):
        test = values["test"]
        # verify that test has task defined except for when use_all_tasks is True
        if not values.get("use_all_tasks"):
            assert values.get("task"), f"No task defined for test '{test}'"
        # iterate over test types and verify required parameters provided
        if any(i in test.lower() for i in ["contains", "equal"]):
            assert "pattern" in values, f"No pattern provided for test '{test}'"
        elif any(i in test.lower() for i in ["custom"]):
            assert any(  # nosec
                i in values for i in ["function_file", "function_text", "function_call"]
            ), f"No function provided for test '{test}'"
        elif any(i in test.lower() for i in ["cerberus"]):
            assert values.get("schema"), f"No schema provided for test '{test}'"
        elif any(i in test.lower() for i in ["eval"]):
            assert values.get(
                "expr"
            ), f"No evaluate expression provided for test '{test}'"
        return values


class modelTestsProcessorSuite(BaseModel):
    """Model for TestsProcessor tests suite list"""

    tests: List[
        Union[modelTestsProcessorTest, conlist(StrictStr, min_items=3, max_items=4)]
    ]
