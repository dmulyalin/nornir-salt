"""
File to contain pydantic models for plugins input/output data validation
"""
from nornir.core.task import Result, Task
from nornir.core.inventory import Host
from enum import Enum
from pydantic import (
    BaseModel,
    StrictBool,
    StrictInt,
    StrictFloat,
    StrictStr,
)
from typing import (
    Union,
    Optional, 
    List,
    Any,
    Dict,
    Callable
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
        extra = 'allow'


class model_nr_test(BaseModel):
    """Model for nornir_salt.plugins.tasks.nr_test plugin arguments"""
    task: Task
    ret_data_per_host: Optional[Dict[StrictStr, Any]]
    ret_data: Optional[Any]
    excpt: Optional[Union[StrictBool, Callable]]
    excpt_msg: Optional[StrictStr]
    
    class Config:
        arbitrary_types_allowed = True
        extra = 'allow'


class model_napalm_send_commands(BaseModel):
    """Model for nornir_salt.plugins.tasks.netmiko_send_commands plugin arguments"""
    task: Task
    commands: Optional[Union[List[StrictStr], StrictStr]]
    interval: Optional[Union[StrictFloat, StrictInt]]
    new_line_char: Optional[StrictStr]
    split_lines: Optional[StrictBool]
    
    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'
        
class model_conn_list(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.conn_list plugin arguments"""
    task: Task
    conn_name: Optional[StrictStr]
        
    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'
        
class model_conn_close(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.conn_close plugin arguments"""
    task: Task
    conn_name: Optional[StrictStr]
        
    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'
        
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
        extra = 'forbid'
        
        
class ConnectionsCallsEnum(str, Enum):
    connections_list = 'ls'
    connections_open = 'open'
    connections_close = "close"
    
class model_connections(BaseModel):
    """Model for nornir_salt.plugins.tasks.connections.connections plugin arguments"""
    task: Task
    call: ConnectionsCallsEnum
        
    class Config:
        arbitrary_types_allowed = True
        extra = 'allow'
        
        
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
        extra = 'allow'
        
        
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
        extra = 'allow'
        
class model_pyats_genie_api(BaseModel):
    """Model for nornir_salt.plugins.tasks.pyats_genie_api plugin arguments"""
    task: Task
    api: StrictStr
        
    class Config:
        arbitrary_types_allowed = True
        extra = 'allow'

class model_salt_cfg_gen(BaseModel):
    """Model for nornir_salt.plugins.tasks.salt_cfg_gen plugin arguments"""
    task: Task
    config: Optional[StrictStr]
        
    class Config:
        arbitrary_types_allowed = True
        extra = 'allow'
        
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
        extra = 'forbid'
        
class model_file_list(BaseModel):
    """Model for nornir_salt.plugins.tasks.file_list plugin arguments"""
    task: Task    
    filegroup: Optional[Union[StrictStr, List[StrictStr]]]
    base_url: Optional[StrictStr] = "/var/nornir-salt/"
    index: Optional[StrictStr] = "common"
    
    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'
        
class model_file_remove(BaseModel):
    """Model for nornir_salt.plugins.tasks.file_remove plugin arguments"""
    task: Task    
    filegroup: Union[StrictStr, List[StrictStr], StrictBool]
    base_url: Optional[StrictStr] = "/var/nornir-salt/"
    index: Optional[StrictStr] = "common"
    
    class Config:
        arbitrary_types_allowed = True
        extra = 'forbid'
        
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
        extra = 'forbid'
        
    
class FilesCallsEnum(str, Enum):
    files_ld = 'ls'
    files_list = 'list'
    files_rm = "rm"
    files_remove = "remove"
    files_delete = "delete"
    files_read = "read"
    files_diff = "diff"
    
class model_files(BaseModel):
    """Model for nornir_salt.plugins.tasks.file_diff plugin arguments"""
    task: Task    
    call: FilesCallsEnum
    
    class Config:
        arbitrary_types_allowed = True
        extra = 'allow'