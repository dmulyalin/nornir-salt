"""
connections
###########

Collection of task plugins to work with Nornir hosts' connections

Sample usage
============

Code to invoke ``connections`` task plugins::

    from nornir import InitNornir

    from nornir_salt.plugins.tasks import connections

    nr = InitNornir(config_file="config.yaml")

    # get a list of connection
    connections_active = nr.run(
        task=connections,
        call="ls"
    )

    # close all connections
    conn_close = nr.run(
        task=connections,
        call="close"
    )

    # connect netmiko connections
    connections_connect = nr.run(
        task=connections,
        call="open",
        conn_name="netmiko",
        username="user123",
        password="pass123",
        reconnect=[
            {
                "username": "user321",
                "password": "pass321",
            },
            "local_creds",
        ]
    )

API reference
=============

.. autofunction:: nornir_salt.plugins.tasks.connections.connections
.. autofunction:: nornir_salt.plugins.tasks.connections.conn_list
.. autofunction:: nornir_salt.plugins.tasks.connections.conn_close
.. autofunction:: nornir_salt.plugins.tasks.connections.conn_open
"""
import time
import traceback
import logging
import copy
import socket

from typing import Optional, Any, Dict
from nornir.core.task import Result
from nornir.core.inventory import Host
from nornir_salt.utils.pydantic_models import (
    model_conn_list,
    model_conn_close,
    model_conn_open,
    model_connections,
)
from nornir_salt.utils.yangdantic import ValidateFuncArgs

log = logging.getLogger(__name__)


class RedispatchedConnection:
    """Dummy connection class to save redispatched connection"""

    def __init__(self, connection=None, **kwargs):
        self.connection = connection

    def close(self):
        self.connection.disconnect()


@ValidateFuncArgs(model_conn_list)
def conn_list(task, conn_name: str = "all") -> list:
    """
    Function to list host's active connections.

    :param conn_name: name of connection to list, default is "all"
    :return: list of hosts' connections
    """
    # form list of host connections
    ret = [
        {
            "connection_name": conn,
            "connection_plugin": str(type(conn_obj)).split(" ")[1].strip(">"),
            "connection_action": "list",
        }
        for conn, conn_obj in task.host.connections.items()
        if conn_name == "all" or conn == conn_name
    ]

    return Result(host=task.host, result=ret)


@ValidateFuncArgs(model_conn_close)
def conn_close(task, conn_name: str = "all") -> list:
    """
    Task to close host's connections.

    :param conn_name: name of connection to close, default is "all"
    :return: list of connections closed
    """
    ret = []

    # iterate over connections and close them
    for conn in list(task.host.connections.keys()):
        if conn_name != "all" and conn != conn_name:
            continue
        ret.append({"connection_name": conn, "connection_action": "close"})
        try:
            task.host.close_connection(conn)
        except:
            ret[-1]["status"] = traceback.format_exc()
        _ = task.host.connections.pop(conn, None)
        ret[-1].setdefault("status", "closed")

    return Result(host=task.host, result=ret)


def _redispatch_connection(
    host, conn_param: dict, conn_name: str, redispatch_data: dict
):
    """Helper function to redispatch connection using Netmiko"""
    from netmiko import ConnectHandler
    from netmiko import redispatch as netmiko_redispatch

    log.debug(
        f"nornir_salt:conn_open redispatching '{host.name}' '{conn_name}' "
        f"connection through terminal server"
    )
    # open connection to console server
    connection = ConnectHandler(
        device_type="terminal_server",
        host=conn_param["hostname"],
        port=conn_param.get("port") or host.port,
        username=conn_param.get("username") or host.username,
        password=conn_param.get("password") or host.password,
        fast_cli=False,  # https://github.com/ktbyers/netmiko/issues/2001
    )

    # redispatch connection to device
    connection.username = redispatch_data.get("username") or host.username
    connection.password = redispatch_data.get("password") or host.password
    connection.telnet_login(
        delay_factor=3
    )  # https://github.com/ktbyers/netmiko/issues/2001
    netmiko_redispatch(
        connection,
        device_type=redispatch_data.get("platform") or host.platform,
        session_prep=False,
    )

    # save connection to host connections
    host.connections[conn_name] = RedispatchedConnection(connection)


@ValidateFuncArgs(model_conn_open)
def conn_open(
    task,
    conn_name: str,
    host: Optional[Host] = None,
    hostname: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    port: Optional[int] = None,
    platform: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    default_to_host_attributes: bool = True,
    close_open: bool = False,
    reconnect: list = None,
    raise_on_error: bool = False,
    via: str = None,
) -> Result:
    """
    Helper function to open connections to hosts. Supports reconnect
    logic retrying different connection parameters.

    :param conn_name: name of configured connection plugin to use
      to open connection e.g. ``netmiko``, ``napalm``, ``scrapli``
    :param hostname: hostname or ip address to connect to
    :param username: username to use to open the connection
    :param password: password to use to open the connection
    :param port: port to use to open the connection
    :param platform: platform name connection parameter
    :param extras: connection plugin extras parameters
    :param default_to_host_attributes: on True host's open connection  method
      uses inventory data to supplement missing arguments like port or
      platform
    :param close_open: if True, closes already open connection
      and connects again
    :param reconnect: list of parameters to use to try connecting
      to device if primary set of parameters fails. If ``reconnect``
      item is a dictionary, it is supplied as ``**kwargs`` to
      host open connection call. Alternatively, ``reconnect`` item
      can refer to a name of credentials set from inventory data
      ``credentials`` section within host, groups or defaults inventory.
    :param raise_on_error: raises error if not able to establish
      connection even after trying all ``reconnect`` parameters, used
      to signal exception to parent function e.g. RetryRunner
    :param host: Nornir Host object supplied by RetryRunner
    :param via: host's ``connection_options`` parameter name to use for
      opening connection for ``conn_name``, if ``via`` parameter provided,
      ``close_open`` always set to `True`` to re-establish host connection.
      ``reconnect`` not suppported with ``via``. ``default_to_host_attributes``
      set to ``True`` if ``via`` argument provided.
    :return: Nornir result object with connection establishment status

    **Device re-connects**

    Sample ``reconnect`` list content::

        [
            {
                "username": "foo123",
                "port": "24",
                "password": "123foo",
            },
            "deprecated_creds",
            "local_account"
        ]

    Where ``deprecated_creds`` and ``local_account`` could be stored
    in Nornir inventory default data credentials section::

        defaults:
          data:
            credentials:
              deprecated_creds:
                password: foo
                username: bar
                extras:
                  optional_args:
                    key_file: False
              local_account:
                password: nornir
                username: nornir

    Starting with nornir-salt version 0.19.0 support added to reconnect
    credentials to specify per-connection parameters using
    ``connection_options`` argument::

        default:
          data:
            credentials:
              local_creds:
                # these params will be used with Netmiko conn_name
                username: nornir
                password: nornir
                platform: arista_eos
                port: 22
                extras:
                  conn_timeout: 10
                  auto_connect: True
                  session_timeout: 60
                connection_options:
                  # these params will be used with NAPALM conn_name
                  napalm:
                    username: nornir
                    platform: eos
                    port: 80
                    extras:
                      optional_args:
                        transport: http
                        eos_autoComplete: None
                  # these params will be used with Scrapli conn_name
                  scrapli:
                    password: nornir
                    platform: arista_eos
                    port: 22
                    extras:
                      auth_strict_key: False
                      ssh_config_file: False
              local_creds_old:
                username: nornir2
                password: nornir2

    ``connection_options`` parameters are preferred and override
    higher level parameters.

    **Device via connections**

    Specifying ``via`` parameter allows to open connection to device
    using certain connection options. This is useful when device has
    multiple management IP addresses, for example - in-band, out of
    band or console.

    If ``via`` parameter provided, connection always closed before
    proceeding with re-opening it.

    Given this host inventory::

        hosts:
          ceos1:
            hostname: 10.0.1.3
            platform: arista_eos
            username: nornir
            password: nornir
            connection_options:
              out_of_band:
                hostname: 10.0.1.4
                port: 22

    setting ``via`` equal to ``out_of_band`` will result in connection
    being open using ``out_of_band`` parameters.

    **Device connection redispatch**

    Primary use case is to use ``via`` to open connection to console
    server and use Netmiko redispatch functionality to access device
    console.

    .. warning: Only ``netmiko`` ``conn_name`` connection plugin
        supported for connections redispatching.

    Given this host inventory::

        hosts:
          ceos1:
            hostname: 10.0.1.3
            platform: arista_eos
            username: nornir
            password: nornir
            connection_options:
              console_port_rp0:
                # console server parameters
                hostname: 10.0.1.4
                port: 1234
                username: nornir123
                password: nornir123
                platform: terminal_server
                extras:
                  redispatch:
                    # redispatch parameters for device connected to console
                    username: nornir321
                    password: nornir321
                    platform: arista_eos
              console_port_rp1:
                # console server hostname:
                hostname: 10.0.1.5
                extras:
                  redispatch: True

    If ``via`` is equal to ``console_port_rp0``, this task plugin
    will establish connection to terminal server and will authenticate
    using ``console_port_rp0`` credentials, next Netmiko connection
    will be redispatched using platform and credentials from
    ``redispacth`` parameters.

    If ``via`` is equal to ``console_port_rp1``, this task plugin will
    establish connection to terminal server hostname and authenticating
    with host's credentials, next Netmiko connection will be redispatched
    using platform and credentials from host's parameters - ``nornir``
    username and password and ``arista_eos`` as a platform.

    For redispatch to work, ``hostname`` parameter must always be provided
    in connection options.
    """
    reconnect = reconnect or []
    info = {
        "connection_name": conn_name,
        "connection_options": via or conn_name,
        "connection_action": "open",
    }
    ret = {}
    host = host or task.host
    close_open = True if via else close_open

    # check if need to close connection first
    if conn_name in host.connections:
        if close_open:
            host.close_connection(conn_name)
        else:
            return Result(host=host, result="Connection already open", **info)

    if via:
        via_conn_opts = host._get_connection_options_recursively(via)
        conn_params = [
            {
                "hostname": via_conn_opts.hostname,
                "username": via_conn_opts.username,
                "password": via_conn_opts.password,
                "port": via_conn_opts.port,
                "platform": via_conn_opts.platform,
                "extras": copy.deepcopy(via_conn_opts.extras) or {},
            }
        ]
        # check if via connection options exists
        if conn_params[0]["hostname"] is None:
            raise RuntimeError(
                f"nornir_salt:conn_open {host.name} via '{via}' parameters not found"
            )
    else:
        conn_params = [
            {
                "hostname": str(hostname) if hostname is not None else None,
                "username": str(username) if username is not None else None,
                "password": str(password) if password is not None else None,
                "port": int(port) if port is not None else None,
                "platform": str(platform) if platform is not None else None,
                "extras": extras,
                "default_to_host_attributes": default_to_host_attributes,
            }
        ] + reconnect

    for index, param in enumerate(conn_params):
        param_name = "kwargs" if index == 0 else index
        redispatch = None

        # source parameters from inventory credentials section
        if isinstance(param, str):
            param_name = param
            param = host.get("credentials", {}).get(param)

        if not isinstance(param, dict):
            raise TypeError("'{}' parameters not found or invalid".format(param_name))

        # extract connection_options and merge with params for non kwargs params
        # do not deepcopy kwaergs params as they might contain Jumphost socket
        if index > 0:
            param = copy.deepcopy(param)
            param.update(param.pop("connection_options", {}).get(conn_name, {}))

        try:
            if index == 0:
                res_msg = f"'{conn_name}' connected with primary connection parameters"
                log_msg = f"nornir_salt:conn_open {host.name} '{conn_name}' connecting with primary connection parameters"
                if via:
                    res_msg = (
                        f"'{conn_name}' connected via '{via}' connection parameters"
                    )
                    log_msg = f"nornir_salt:conn_open {host.name} '{conn_name}' connecting via '{via}' connection parameters"
                    redispatch = param.get("extras", {}).pop("redispatch", None)
                    if redispatch is True:
                        redispatch = {}
            elif isinstance(param_name, str):
                res_msg = (
                    f"{conn_name} connected with '{param_name}' connection parameters"
                )
                log_msg = f"nornir_salt:conn_open {host.name} '{conn_name}' re-connecting with '{param_name}' connection parameters"
            else:
                res_msg = f"{conn_name} connected with reconnect index '{index - 1}' connection parameters"
                log_msg = f"nornir_salt:conn_open {host.name} '{conn_name}' re-connecting with index '{index - 1}' connection parameters"
            log.info(log_msg)
            # establish host connection
            if redispatch is not None:
                if conn_name != "netmiko":
                    raise RuntimeError(
                        f"Only 'netmiko' redispatch supported, '{conn_name}' redispatch not supported"
                    )
                _redispatch_connection(host, param, conn_name, redispatch)
                res_msg = f"'{conn_name}' connected using '{via}' connection parameters redispatching connection"
            else:
                host.open_connection(
                    **param, connection=conn_name, configuration=task.nornir.config
                )
            ret = {"result": res_msg}
            break
        except:
            tb = traceback.format_exc()
            ret = {
                "result": f"{conn_name} connection failed\n\n{tb}",
                "exception": tb,
                "failed": True,
            }
            time.sleep(0.1)

    # check if need to raise an error
    if ret.get("exception") and raise_on_error:
        raise RuntimeError(ret["exception"])

    return Result(host=host, **info, **ret)


def conn_check(
    task,
    host: Optional[Host] = None,
    connection_name: Optional[str] = None,
    timeout: Optional[int] = 5,
) -> Result:
    """
    Function to check TCP connection to host for given
    connection name.

    :param connection_name: name of configured connection plugin to check
      to open connection e.g. ``netmiko``, ``napalm``, ``scrapli``
    :param host: Nornir host object
    :param timeout: connection socket timeout in seconds
    """
    host = host or task.host
    result = Result(host=host, result=None)
    # source hostname and port
    if connection_name:
        conn_opts = host._get_connection_options_recursively(connection_name)
        hostname = conn_opts.hostname or host.hostname
        port = conn_opts.port or host.port or 22
    else:
        hostname = host.hostname
        port = host.port or 22
        connection_name = "primary connection parameters"
    # test connection
    s = socket.socket()
    try:
        s.settimeout(timeout)
        s.connect((hostname, port))
        s.close()
        result.result = True
    except Exception as e:
        result.failed = True
        result.exception = (
            f"{hostname}:{port} {connection_name} TCP connection error: '{e}'"
        )
        result.result = False
    finally:
        s.close()

    return result


@ValidateFuncArgs(model_connections)
def connections(task, call, **kwargs):
    """
    Dispatcher function to call one of the functions.

    :param call: (str) nickname of function to call
    :param arg: (list) function arguments
    :param kwargs: (dict) function key-word arguments
    :return: call function execution results

    Call function nicknames:

    * ls - calls conn_list task
    * close - calls conn_close task
    * open - calls conn_open task
    * check - calls conn_check task
    """
    task.name = "connections"
    dispatcher = {
        "ls": conn_list,
        "close": conn_close,
        "open": conn_open,
        "check": conn_check,
    }

    return dispatcher[call](task, **kwargs)
