"""
netbox_tasks
############

This task plugin is to sync information between Netbox and Nornir host.

Software versions tested:

- Netbox v3.2.9, pynetbox 6.6.2

netbox_tasks sample usage
=========================

Sample code to run ``netbox_tasks`` task::

    from nornir_salt.plugins.tasks import netbox_tasks
    from nornir import InitNornir

    nr = InitNornir(config_file="nornir_config.yaml")

    res = nr.run(
        task=netbox_tasks,
        task_name="sync_from",
        via="dev"
    )

All netbox tasks return Nornir Result object with "result" set
to string describint task results and wiht "status" key set to
either True or False depending on task success.

netbox_tasks returns
=================

Returns requests result string in XML or JSON format.

netbox_tasks reference
===================

.. autofunction:: nornir_salt.plugins.tasks.netbox_tasks.netbox_tasks
.. autofunction:: nornir_salt.plugins.tasks.netbox_tasks.sync_device_from_netbox
.. autofunction:: nornir_salt.plugins.tasks.netbox_tasks.sync_device_to_netbox
"""
import logging
from nornir.core.task import Result, Task

# from nornir_salt.utils.pydantic_models import model_netbox_tasks
# from nornir_salt.utils.yangdantic import ValidateFuncArgs

try:
    import pynetbox

    HAS_PYNETBOX = True
except ImportError:
    HAS_PYNETBOX = False

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "netbox"


def _start_netbox_connection(netbox_instances: dict, via: str):
    """
    Helper function to start Netbox connection

    :param netbox_instances: netbox instances connection parameters
    :param via: connection parameters name to use
    """
    if "token" in netbox_instances[via]:
        nb = pynetbox.api(**netbox_instances[via])
    elif "auth" in netbox_instances[via]:
        nb_params = netbox_instances[via].copy()
        auth = nb_params.pop("auth")
        nb = pynetbox.api(**nb_params)
        nb.create_token(*auth)

    log.debug(
        f"nornir-salt:netbox_tasks started Netbox connection via '{via}' instance"
    )

    return nb


def _remove_data_keys(data, remove_keys, skip=None):
    """
    Helper function to recursively remove given keys from netbox data,
    this is because previously retrieved data from netbox contains read-only
    parameters, need to remove tem prior to sending data back to Netbox.

    :param data: (dict) Nested ditionary to remove keys from
    :param remove_keys: (list) list of keys to remove
    :param skip: (list) list of data top keys to skip procesing for
    """
    skip = skip or ["config_context", "custom_fields"]

    for data_key in list(data.keys()):
        if data_key in skip:
            continue
        if data_key in remove_keys:
            _ = data.pop(data_key)
        elif isinstance(data[data_key], dict):
            _remove_data_keys(data[data_key], remove_keys, skip=[""])


def _extract_data_values(data, keys):
    """
    Helper function to exctract "value" for given "by_value_keys".

    On retrieval Netbox returns data like this::

        'airflow': {'value': 'front-to-rear', 'label': 'Front to rear'}

    While pushing data with "airflow" key to Netbox need to transform
    it to::

        'airflow': 'front-to-rear'

    This function does exactly that.

    :param data: (dict) dictionary to work with
    :param keys: (list) list of key names to extract value for
    """
    for k in keys:
        if k in data and "value" in data[k]:
            data[k] = data[k]["value"]


def sync_device_from_netbox(
    task: Task,
    via: str = "default",
    data_key: str = "netbox",
) -> dict:
    """
    Function to sync data from Netbox to host's inventory using host's name (not hostname)
    to retrieve respective Netbox device entry data.

    :param via: name of netbox instance connection parameters
    :param data_key: Nornir invetnory data key name to save host's Netbox inventory
    :return dict: Nornir results object with operation resut and ``status`` attribute
        containing ``True`` if data synced and ``False`` if device not found
    """
    netbox_instances = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    log.debug(
        f"nornir_salt:sync_device_from_netbox using '{via}' instance, "
        f"device name '{task.host.name}'"
    )

    nb = _start_netbox_connection(netbox_instances, via)
    host_obj = task.nornir.inventory.hosts[task.host.name]

    # retrieve data from netbox and save it into inventory
    device_name = task.host.name
    response = nb.dcim.devices.get(name=device_name)
    if not response:
        result = f"Device '{device_name}' not found in Netbox"
        status = False
    elif data_key:
        host_obj.data[data_key] = dict(response)
        result = f"Netbox device data synced to host's data under key '{data_key}'"
        status = True
    else:
        host_obj.data.update(dict(response))
        result = f"Netbox device data synced to hosts's data"
        status = True

    return Result(host=task.host, result=result, status=status)


def sync_device_to_netbox(
    task: Task,
    via: str = "default",
    data_key: str = "netbox",
) -> dict:
    """
    Function to sync Nornir hosts inventory into Netbox device.

    :param via: name of netbox instance connection parameters
    :param data_key: Nornir invetnory data key name with Netbox inventory

    If no device with given name exists in Netbox, it will be created.

    All parameters under host.data.netbox synced to Netbox. In addition these
    parameters added if they are missing from host.data.netbox

    - name - set to host name

    Sample Nornir hosts ``data_key=netbox`` data populated manually or by using
    ``sync_device_from_netbox`` task::

        nornir:
          hosts:
            ceos1:
              data:
                netbox:
                  airflow:
                    label: Front to rear
                    value: front-to-rear
                  asset_tag: null
                  cluster: null
                  comments: ''
                  config_context:
                    domain_name: lab.io
                    lo0_ip: 4.3.2.1
                    syslog_servers:
                    - 10.0.0.3
                    - 10.0.0.4
                  created: '2022-08-21T02:26:49.631041Z'
                  custom_fields: {}
                  device_role:
                    display: router
                    id: 1
                    name: router
                    slug: router
                    url: http://192.168.64.200:8000/api/dcim/device-roles/1/
                  device_type:
                    display: FakeNOS Arista cEOS
                    id: 1
                    manufacturer:
                      display: FakeNOS
                      id: 1
                      name: FakeNOS
                      slug: fakenos
                      url: http://192.168.64.200:8000/api/dcim/manufacturers/1/
                    model: FakeNOS Arista cEOS
                    slug: arista-ceos
                    url: http://192.168.64.200:8000/api/dcim/device-types/1/
                  display: ceos1
                  face:
                    label: Front
                    value: front
                  id: 2
                  last_updated: '2022-08-23T06:42:33.513505Z'
                  local_context_data:
                    domain_name: lab.io
                    lo0_ip: 4.3.2.1
                    syslog_servers:
                    - 10.0.0.3
                    - 10.0.0.4
                  location: null
                  name: ceos1
                  parent_device: null
                  platform:
                    display: FakeNOS Arista cEOS
                    id: 1
                    name: FakeNOS Arista cEOS
                    slug: fakenos-arista-ceos
                    url: http://192.168.64.200:8000/api/dcim/platforms/1/
                  position: 41
                  primary_ip:
                    address: 4.3.2.1/24
                    display: 4.3.2.1/24
                    family: 4
                    id: 3
                    url: http://192.168.64.200:8000/api/ipam/ip-addresses/3/
                  primary_ip4:
                    address: 4.3.2.1/24
                    display: 4.3.2.1/24
                    family: 4
                    id: 3
                    url: http://192.168.64.200:8000/api/ipam/ip-addresses/3/
                  primary_ip6: null
                  rack:
                    display: R101
                    id: 1
                    name: R101
                    url: http://192.168.64.200:8000/api/dcim/racks/1/
                  serial: ''
                  site:
                    display: SALT-NORNIR-LAB
                    id: 1
                    name: SALT-NORNIR-LAB
                    slug: salt-nornir-lab
                    url: http://192.168.64.200:8000/api/dcim/sites/1/
                  status:
                    label: Active
                    value: active
                  tags: []
                  tenant: null
                  url: http://192.168.64.200:8000/api/dcim/devices/2/
                  vc_position: null
                  vc_priority: null
                  virtual_chassis: null

    Above data automatically transformed to data below prior to pushing to Netbox
    making sure to remove read-only keys and resolve key to values::

        nornir:
          hosts:
            ceos1:
              data:
                netbox:
                  airflow: front-to-rear
                  asset_tag: null
                  cluster: null
                  comments: ''
                  config_context:
                    domain_name: lab.io
                    lo0_ip: 4.3.2.1
                    syslog_servers:
                    - 10.0.0.3
                    - 10.0.0.4
                  custom_fields: {}
                  device_role:
                    name: router
                    slug: router
                  device_type:
                    manufacturer:
                      name: FakeNOS
                      slug: fakenos
                    model: FakeNOS Arista cEOS
                    slug: arista-ceos
                  face: front
                  local_context_data:
                    domain_name: lab.io
                    lo0_ip: 4.3.2.1
                    syslog_servers:
                    - 10.0.0.3
                    - 10.0.0.4
                  location: null
                  name: ceos1
                  parent_device: null
                  platform:
                    name: FakeNOS Arista cEOS
                    slug: fakenos-arista-ceos
                  position: 41
                  primary_ip:
                    address: 4.3.2.1/24
                  primary_ip4:
                    address: 4.3.2.1/24
                  primary_ip6: null
                  rack:
                    name: R101
                  serial: ''
                  site:
                    name: SALT-NORNIR-LAB
                    slug: salt-nornir-lab
                  status: active
                  tags: []
                  tenant: null
                  vc_position: null
                  vc_priority: null
                  virtual_chassis: null

    If the goal is to sync Nornir inventory with Netbox devices this is
    the minimum set of mandatory fields to be populated into Nornir
    hosts' data::

        nornir:
          hosts:
            ceos2:
              data:
                netbox:
                  device_role:
                    slug: router
                  device_type:
                    slug: arista-ceos
                  site:
                    slug: salt-nornir-lab
                  status: active

    Where device type, role and site must refer to valid Netbox entities.

    Sample code to run ``sync_device_to_netbox`` task::

        from nornir_salt.plugins.tasks import sync_device_to_netbox
        from nornir import InitNornir

        nr = InitNornir(config_file="nornir_config.yaml")

        res = nr.run(task=sync_device_to_netbox)
    """
    nb_read_only_keys = ["created", "display", "last_updated", "id", "url", "family"]
    nb_value_only_keys = ["face", "status", "airflow"]

    netbox_instances = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    log.debug(
        f"nornir_salt:sync_device_to_netbox using '{via}' instance, "
        f"device name '{task.host.name}'"
    )

    nb = _start_netbox_connection(netbox_instances, via)
    host_obj = task.nornir.inventory.hosts[task.host.name]

    if not host_obj.data.get(data_key, {}):
        result = f"Nornir host's data has no '{data_key}' key"
        status = False
    else:
        # form netbox device data
        device_name = task.host.name
        nb_device_data = host_obj.data.get(data_key, {})
        nb_device_data.setdefault("name", device_name)
        _remove_data_keys(
            data=nb_device_data,
            remove_keys=nb_read_only_keys,
            skip=["config_context", "custom_fields"],
        )
        _extract_data_values(data=nb_device_data, keys=nb_value_only_keys)

        nb_device = nb.dcim.devices.get(name=device_name)

        # update existing device
        if nb_device:
            nb_device.update(nb_device_data)
            nb_device.save()
            result = f"Updated Netbox device '{device_name}' using Nornir host's '{data_key}' data"
            status = True
        # create new device
        else:
            response = nb.dcim.devices.create(nb_device_data)
            result = f"Created Netbox device '{device_name}' using Nornir host's '{data_key}' data"
            status = True

    return Result(host=task.host, result=result, status=status)


def sync_vrf_to_netbox():
    pass


def sync_vlan_to_netbox():
    pass


def sync_bgp_to_netbox():
    pass


def sync_ip_to_netbox():
    pass


def sync_routes_to_netbox():
    pass


def sync_arp_to_netbox():
    pass


def sync_l2vpn_to_netbox():
    pass


def sync_config_to_netbox():
    """
    Function to parse entwork devices config and sync it to
    Netbox device local config context.
    """
    pass


def sync_interfaces_to_netbox(
    task: Task,
    via: str = "default",
    use_ttp: bool = True,
    use_openconfig: bool = False,
    custom_fields: bool = True,
) -> dict:
    """
    Function to sync device interfaces to Netbox.

    :param via: name of netbox instance connection parameters
    :param custom_fields: if True populates custom fields described
        below, also creates them if neccessary
    :param use_ttp: uses TTP to parse show commands output to produce data to
        populate Netbox
    :param use_openconfig: uses OpenConfig models to extract interfaces data from
        devices over Netconf or gNMI depending on connection plugins configured

    Information synced from Nornir host to Netbox device interface:

    - device - uses host name to update Netbox device
    - name - set to device interface name
    - type - interface type one of virtual, bridge, lag, other
    - enabled - set to True or False based on interface status
    - parent - reference to parent interface name
    - bridge - reference to parent Bridged interface name
    - lag - reference to parent LAG interface name
    - mtu - set to interface MTU size value
    - mac_address - set to interface mac-address value
    - speed - set to interface speed value
    - duplex - set to interface duplex value
    - mgmt_only - set to True for OOB interfaces
    - description - set to interface description value
    - mode - set to interface L2 mode value if applicable
    - untagged_vlan - records interface native vlan value if applicable
    - tagged_vlans - records interface trunked vlans if applicable
    - vrf - set to interface VRF name
    - comments - adds timestamp information for current update
    - config_context - populated with as is interface data

    Additional custom fields populated if custom_fields is True:

    - last_flapped - records timestamp of when interface last flapped
    - state_transitions - records overall count of interface state transitions

    Platforms supported by use_ttp:

    - Arista EOS - uses ttp://misc/netbox/arista_eos_interfaces.txt TTP template
    - Cisco IOS-XR - uses ttp://misc/netbox/cisco_xr_interfaces.txt TTP template
    - Cisco IOS - uses ttp://misc/netbox/cisco_ios_interfaces.txt TTP template
    - Cisco NXOS - uses ttp://misc/netbox/cisco_nxos_interfaces.txt TTP template
    - Juniper JunOS - uses ttp://misc/netbox/juniper_junos_interfaces.txt TTP template

    Platforms supported by use_openconfig - any OpenConfig compatible platforms.
    This function tries to extract data using gNMI if gNMI connection plugins
    configured, uses Netconf otherwise.
    """
    pass


tasks_fun = {
    "sync_from": sync_device_from_netbox,
    "sync_to": sync_device_to_netbox,
    "sync_interfaces": sync_interfaces_to_netbox,
}


# @ValidateFuncArgs(model_netbox_tasks)
def netbox_tasks(
    task: Task,
    task_name: str = "dir",
    **kwargs,
) -> Result:
    """
    Task call netbox related task functions, used mainly by salt-nornir
    proxy minion module.

    :param task_name: name of task to run
    :param kwargs: any ``**kwargs`` to use with syn method method

    **Supported tasks names:**

    - ``dir`` - lists available task names
    - ``sync_from`` - uses ``sync_device_from_netbox`` task plugin to synchronize
        data from Netbox to Nornir host's inventory
    - ``sync_to`` - uses ``sync_device_to_netbox`` task plugin to synchronize
        data from Nornir host's inventory to Netbox
    """
    task.name = task_name

    # run sanity check
    if not HAS_PYNETBOX:
        return Result(
            host=task.host,
            failed=True,
            exception="nornir_salt:netbox_tasks pynetbox not found, is it installed?",
        )

    if task_name == "dir":
        return Result(host=task.host, result=list(tasks_fun.keys()) + ["dir"])
    else:
        return tasks_fun[task_name](task=task, **kwargs)
