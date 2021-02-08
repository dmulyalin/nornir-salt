import logging
import traceback

log = logging.getLogger(__name__)


def HostsKeepalive(nr):
    """
    Function to iterate over Nornir hosts' connections and
    check if connection still alive. If connection not
    responding, ``HostsKeepalive`` function closes it.
    
    :param nr: Nornir object
    :returns stats: dictionary with statistics about ``HostsKeepalive`` execution
    
    ``stats`` dictionary keys description
    
    - ``dead_connections_cleaned`` - contains overall number of connections cleaned
    
    ``HostsKeepalive`` function supports these connection types:
    
    - netmiko - writes ``chr(0)`` to the channel to check connection
    - paramiko channel - uses connection ``active`` attribute to check connection
    - napalm - uses ``is_alive()`` method to check connection
    - scrapli - uses ``isalive()`` method to check connection
    """
    stats = {
        "dead_connections_cleaned": 0
    }
    
    for host_name, host_obj in nr.inventory.hosts.items():
        # to avoid "RuntimeError: dictionary changed size during iteration" error
        # going to iterate over a copy of dictionary keys
        for conn_name in list(host_obj.connections.keys()):
            conn_obj = host_obj.connections[conn_name]
            is_alive = True
            try:
                if "netmiko" in str(type(conn_obj)).lower():
                    conn_obj.connection.write_channel(chr(0))
                elif "paramiko.channel.channel" in str(type(conn_obj)).lower():
                    is_alive = conn_obj.active
                elif "napalm" in str(type(conn_obj)).lower():
                    is_alive = conn_obj.connection.is_alive()
                elif "scrapli" in str(type(conn_obj)).lower():
                    is_alive = conn_obj.connection.isalive()
                else:
                    log.debug(
                        "nornir_salt:HostsKeepalive - uncknown connection type '{}'".format(conn_name)
                    )
            except:
                is_alive = False
                tb = traceback.format_exc()
                log.info(
                    "nornir_salt:HostsKeepalive - '{}' connection keepalive error: {}".format(
                        conn_name, tb
                    )
                )
            # close connection if not alive
            if not is_alive:
                host_obj.close_connection(conn_name)
                _ = host_obj.connections.pop(conn_name, None)
                stats["dead_connections_cleaned"] += 1
                log.info(
                    "nornir_salt:HostsKeepalive, removed dead '{}' connection, host '{}'".format(
                        conn_name, host_name
                    )
                )
                
    return stats