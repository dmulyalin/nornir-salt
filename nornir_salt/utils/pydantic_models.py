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
    #    root_validator,
    model_validator,
    Field,
    ConfigDict,
)
from typing import Union, Optional, List, Any, Dict, Callable, Tuple


class model_ffun_fx_filters(BaseModel):
    FO: Optional[Union[Dict, List[Dict]]] = Field(
        None, title="Filter Object", description="Filter hosts using Filter Object"
    )
    FB: Optional[Union[List[str], str]] = Field(
        None,
        title="Filter gloB",
        description="Filter hosts by name using Glob Patterns",
    )
    FH: Optional[Union[List[StrictStr], StrictStr]] = Field(
        None, title="Filter Hostname", description="Filter hosts by hostname"
    )
    FC: Optional[Union[List[str], str]] = Field(
        None,
        title="Filter Contains",
        description="Filter hosts by name contains patterns",
    )
    FR: Optional[Union[List[str], str]] = Field(
        None,
        title="Filter Regex",
        description="Filter hosts by name using Regular Expressions",
    )
    FG: Optional[StrictStr] = Field(
        None, title="Filter Group", description="Filter hosts by group"
    )
    FP: Optional[Union[List[StrictStr], StrictStr]] = Field(
        None,
        title="Filter Prefix",
        description="Filter hosts by hostname using IP Prefix",
    )
    FL: Optional[Union[List[StrictStr], StrictStr]] = Field(
        None, title="Filter List", description="Filter hosts by names list"
    )
    FM: Optional[Union[List[StrictStr], StrictStr]] = Field(
        None, title="Filter platforM", description="Filter hosts by platform"
    )
    FX: Optional[Union[List[str], str]] = Field(
        None, title="Filter eXclude", description="Filter hosts excluding them by name"
    )
    FN: Optional[StrictBool] = Field(
        None, title="Filter Negate", description="Negate the match"
    )


class model_netmiko_send_commands(BaseModel):
    """Model for nornir_salt.plugins.tasks.netmiko_send_commands plugin arguments"""

    task: Task
    commands: Optional[Union[List[StrictStr], StrictStr]] = None
    interval: Optional[Union[StrictFloat, StrictInt]] = None
    use_ps: Optional[StrictBool] = None
    split_lines: Optional[StrictBool] = None
    new_line_char: Optional[StrictStr] = None
    repeat: Optional[StrictInt] = None
    stop_pattern: Optional[StrictStr] = None
    repeat_interval: Optional[StrictInt] = None
    return_last: Optional[StrictInt] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


class model_nr_test(BaseModel):
    """Model for nornir_salt.plugins.tasks.nr_test plugin arguments"""

    task: Task
    ret_data_per_host: Optional[Dict[StrictStr, Any]] = None
    ret_data: Optional[Any] = None
    excpt: Optional[Union[StrictBool, Callable]] = None
    excpt_msg: Optional[StrictStr] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_napalm_send_commands(BaseModel):
    """Model for nornir_salt.plugins.tasks.napalm_send_commands plugin arguments"""

    task: Task
    commands: Optional[Union[List[StrictStr], StrictStr]] = None
    interval: Optional[Union[StrictFloat, StrictInt]] = None
    new_line_char: Optional[StrictStr] = None
    split_lines: Optional[StrictBool] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_conn_list(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.conn_list plugin arguments"""

    task: Task
    conn_name: Optional[StrictStr] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_conn_close(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.conn_close plugin arguments"""

    task: Task
    conn_name: Optional[StrictStr] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_conn_open(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.conn_open plugin arguments"""

    task: Task
    conn_name: StrictStr
    host: Optional[Host] = None
    hostname: Optional[StrictStr] = None
    username: Optional[StrictStr] = None
    password: Optional[StrictStr] = None
    port: Optional[StrictInt] = None
    platform: Optional[StrictStr] = None
    extras: Optional[Dict[StrictStr, Any]] = None
    default_to_host_attributes: Optional[StrictBool] = None
    close_open: Optional[StrictBool] = None
    reconnect: Optional[List] = None
    raise_on_error: Optional[StrictBool] = None
    via: Optional[StrictStr] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class ConnectionsCallsEnum(str, Enum):
    connections_list = "ls"
    connections_open = "open"
    connections_close = "close"
    connection_check = "check"


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
    commands: Optional[Union[List[StrictStr], StrictStr]] = None
    interval: Optional[Union[StrictFloat, StrictInt]] = None
    split_lines: Optional[StrictBool] = None
    new_line_char: Optional[StrictStr] = None
    repeat: Optional[StrictInt] = None
    stop_pattern: Optional[StrictStr] = None
    repeat_interval: Optional[StrictInt] = None
    return_last: Optional[StrictInt] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_pyats_send_commands(BaseModel):
    """Model for nornir_salt.plugins.tasks.pyats_send_commands plugin arguments"""

    task: Task
    commands: Optional[Union[List[StrictStr], StrictStr]] = None
    interval: Optional[Union[StrictFloat, StrictInt]] = None
    new_line_char: Optional[StrictStr] = None
    split_lines: Optional[StrictBool] = None
    via: Optional[StrictStr] = None
    parse: Optional[StrictBool] = None

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
    config: Optional[StrictStr] = None
    multiline: Optional[StrictBool] = None

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
    filegroup: Optional[Union[StrictStr, List[StrictStr]]] = None
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
    tf_index_lock: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class model_file_diff(BaseModel):
    """Model for nornir_salt.plugins.tasks.file_diff plugin arguments"""

    task: Task
    filegroup: Union[StrictStr, List[StrictStr]]
    base_url: Optional[StrictStr] = "/var/nornir-salt/"
    task_name: Optional[StrictStr] = None
    last: Optional[Union[StrictInt, List[StrictInt], StrictStr]] = None
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
    url: Optional[StrictStr] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_napalm_configure(BaseModel):
    """Model for nornir_salt.plugins.tasks.napalm_configure plugin arguments"""

    task: Task
    config: Optional[Union[StrictStr, List[StrictStr]]] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class NclientEditRPCnames(str, Enum):
    files_ls = "edit_config"
    files_list = "load_configuration"


class model_ncclient_call(BaseModel):
    """Model for nornir_salt.plugins.tasks.ncclient_call plugin arguments"""

    task: Task
    call: StrictStr
    edit_rpc: Optional[NclientEditRPCnames] = None
    confirm_delay: Optional[StrictInt] = None
    target: Optional[StrictStr] = None
    config: Optional[Union[StrictStr, List[StrictStr]]] = None
    format_: Optional[StrictStr] = Field(None, alias="format")
    confirmed: Optional[StrictBool] = None
    commit_final_delay: Optional[StrictInt] = None
    confirm_delay: Optional[StrictInt] = None
    validate_: Optional[StrictBool] = Field(None, alias="validate")
    edit_rpc: Optional[StrictStr] = None
    edit_arg: Optional[Dict] = None
    commit_arg: Optional[Dict] = None
    capab_filter: Optional[StrictStr] = None
    method_name: Optional[StrictStr] = None
    rpc: Optional[StrictStr] = None
    filter_: Optional[StrictStr] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_puresnmp_call(BaseModel):
    """Model for nornir_salt.plugins.tasks.puresnmp_call plugin arguments"""

    task: Task
    call: StrictStr
    oid: Optional[StrictStr] = None
    oids: Optional[List[StrictStr]] = None
    mappings: Optional[Dict[StrictStr, Any]] = None
    value: Optional[Union[StrictStr]] = None
    bulk_size: Optional[StrictInt] = None
    scalar_oids: Optional[List[StrictStr]] = None
    repeating_oids: Optional[List[StrictStr]] = None
    method_name: Optional[StrictStr] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_netmiko_send_config(BaseModel):
    """Model for nornir_salt.plugins.tasks.netmiko_send_config plugin arguments"""

    task: Task
    config: Optional[Union[StrictStr, List[StrictStr]]] = None
    commit: Optional[Union[Dict, StrictBool]] = None
    commit_final_delay: Optional[StrictInt] = None
    batch: Optional[StrictInt] = None
    enable: Optional[StrictBool] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_pyats_send_config(BaseModel):
    """Model for nornir_salt.plugins.tasks.pyats_send_config plugin arguments"""

    task: Task
    config: Optional[Union[StrictStr, List[StrictStr]]] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_pygnmi_call(BaseModel):
    """Model for nornir_salt.plugins.tasks.pygnmi_call plugin arguments"""

    task: Task
    call: StrictStr
    name_arg: Optional[StrictStr] = None

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
    cache_keys: Optional[List[StrictStr]] = None

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
    config: Optional[Union[StrictStr, List[StrictStr]]] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_sleep(BaseModel):
    """Model for nornir_salt.plugins.tasks.sleep plugin arguments"""

    task: Task
    sleep_for: Optional[StrictInt] = None
    sleep_random: Optional[Union[StrictInt, List[StrictInt], Tuple[StrictInt]]] = None

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


class EnumSaltTestAllowedExecFunctions(str, Enum):
    nr_cli = "nr.cli"
    nr_tping = "nr.tping"
    nr_task = "nr.task"
    nr_hrrp = "nr.http"
    nr_nc = "nr.nc"
    nr_gnmi = "nr.gnmi"
    nr_network = "nr.network"
    nr_file = "nr.file"
    nr_snmp = "nr.snmp"


class modelSaltTestsArgs(BaseModel):
    function: Optional[EnumSaltTestAllowedExecFunctions] = None

    class Config:
        extra = "allow"


class modelTestsProcessorTest(BaseModel):
    """Model for TestsProcessor single test dictionary item"""

    test: TestsProcessorTestFunctions
    name: Optional[StrictStr] = None
    task: Optional[Union[StrictStr, List[StrictStr]]] = None
    err_msg: Optional[StrictStr] = None
    path: Optional[StrictStr] = None
    report_all: Optional[StrictBool] = None
    use_all_tasks: Optional[StrictBool] = None
    # Contains and Equal tests parameters
    pattern: Optional[Union[StrictStr, Any]] = None
    use_re: Optional[StrictBool] = None
    count: Optional[StrictInt] = None
    count_ge: Optional[StrictInt] = None
    count_le: Optional[StrictInt] = None
    revert: Optional[StrictBool] = None
    # CustomFunctionTest parameters
    function_file: Optional[StrictStr] = None
    function_text: Optional[StrictStr] = None
    function_call: Optional[Callable] = None
    function_name: Optional[StrictStr] = None
    function_kwargs: Optional[Dict] = None
    globals_dictionary: Optional[Dict] = None
    add_host: Optional[StrictBool] = None
    # CerberusTest parameters
    cerberus_schema: Optional[Union[StrictStr, Dict]] = Field(None, alias="schema")
    allow_unknown: Optional[StrictBool] = None
    # EvalTest parameters
    expr: Optional[StrictStr] = None
    globs: Optional[Dict] = None
    # SALT related argumetns
    salt: Optional[modelSaltTestsArgs] = None

    class Config:
        extra = "allow"

    @model_validator(mode="before")
    @classmethod
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


class modelTestsProcessorTests(BaseModel):
    tests: Union[
        List[List[StrictStr]], List[Dict], List[StrictStr], Dict[StrictStr, List[Dict]]
    ]


class modelTestsProcessorSuite(BaseModel):
    """Model for TestsProcessor tests suite"""

    tests: Union[
        List[
            Union[
                modelTestsProcessorTest,
                List[StrictStr],
                StrictStr,
            ]
        ],
        Dict[
            StrictStr,
            List[
                Union[
                    modelTestsProcessorTest,
                    List[StrictStr],
                    StrictStr,
                ]
            ],
        ],
    ]


class NornirInventoryConnection(BaseModel):
    """Nornir Inventory Connection Options Model"""

    hostname: Optional[StrictStr] = None
    port: Optional[
        Union[None, int]
    ] = None  # using Union[None, StrictInt] throws error if port is None
    username: Optional[StrictStr] = None
    password: Optional[StrictStr] = None
    platform: Optional[StrictStr] = None
    extras: Optional[Dict] = None


class NornirInventoryHost(BaseModel):
    """Model for Nornir Inventory Host, Groups and Defaults"""

    hostname: Optional[StrictStr] = None
    port: Optional[Union[None, int]] = None
    username: Optional[StrictStr] = None
    password: Optional[StrictStr] = None
    platform: Optional[StrictStr] = None
    connection_options: Optional[Dict[StrictStr, NornirInventoryConnection]] = None
    groups: Optional[List[StrictStr]] = None
    data: Optional[Dict] = None


class NornirInventory(BaseModel):
    """Model for Nornir Inventory"""

    hosts: Optional[Dict[StrictStr, NornirInventoryHost]] = None
    groups: Optional[Dict[StrictStr, NornirInventoryHost]] = None
    defaults: Optional[NornirInventoryHost] = None


class model_network(BaseModel):
    """Model for Nornir network task plugin"""

    task: Task
    call: Optional[StrictStr] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class model_network_resolve_dns(BaseModel):
    """Model for Nornir network resolve_dns task plugin"""

    task: Task
    servers: Optional[Union[List[StrictStr], StrictStr]] = None
    use_host_name: Optional[StrictBool] = None
    timeout: Optional[StrictFloat] = None
    ipv4: Optional[StrictBool] = None
    ipv6: Optional[StrictBool] = None

    class Config:
        arbitrary_types_allowed = True
