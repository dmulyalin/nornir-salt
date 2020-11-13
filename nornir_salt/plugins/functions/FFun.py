import logging
from fnmatch import fnmatchcase
from nornir.core.filter import F


log = logging.getLogger(__name__)


def FFun(nr, **kwargs):
    """
    Inventory filters dispatcher function
    """
    ret = nr
    has_filter = False
    # check if kwargs argument given, usually
    # supplied by SALT nornir-proxy
    if kwargs.get("kwargs"):
        kwargs = kwargs["kwargs"]
    if kwargs.get("FO"):
        ret = _filter_FO(ret, kwargs.pop("FO"))
        has_filter = True
    if kwargs.get("FB"):
        ret = _filter_FB(ret, kwargs.pop("FB"))
        has_filter = True
    if kwargs.get("FG"):
        ret = _filter_FG(ret, kwargs.pop("FG"))
        has_filter = True
    if kwargs.get("FP"):
        ret = _filter_FP(ret, kwargs.pop("FP"))
        has_filter = True
    if kwargs.get("FL"):
        ret = _filter_FL(ret, kwargs.pop("FL"))
        has_filter = True
    ret.state.has_filter = has_filter
    return ret
    
def _filter_FO(nr, filter_data):
    """
    Function to filter hosts using Filter Object
    """
    ret = nr
    if isinstance(filter_data, dict):
        ret = ret.filter(F(**filter_data))
    elif isinstance(filter_data, list):
        ret = ret.filter(F(**filter_data[0]))
        for item in filter_data[1:]:
            filtered_hosts = nr.filter(F(**item))
            ret.inventory.hosts.update(filtered_hosts.inventory.hosts)
    return ret


def _filter_FB(ret, pattern):
    """
    Function to filter hosts by name using glob patterns
    """
    return ret.filter(filter_func=lambda h: fnmatchcase(h.name, pattern))


def _filter_FG(ret, group):
    """
    Function to filter hosts using Groups
    """
    return ret.filter(filter_func=lambda h: h.has_parent_group(group))


def _filter_FP(ret, pfx):
    """
    Function to filter hosts based on IP Prefixes
    """
    import ipaddress
    import socket
    
    socket.setdefaulttimeout(1)

    def _filter_net(host):
        # convert host's ip to ip address object
        try:
            ip_addr = ipaddress.ip_address(host.hostname)
        except ValueError:
            # try to resolve hostname using DNS
            try:
                ip_str = socket.gethostbyname(host.hostname)
                ip_addr = ipaddress.ip_address(ip_str)
            except Exception as e:
                log.error(
                    "FP failed to convert host IP '{}', error '{}'".format(
                        host.name, e
                    )
                )
                return False
        # run filtering
        for net in networks:
            if ip_addr in net:
                return True
        return False

    # make a list of network objects
    prefixes = (
        [i.strip() for i in pfx.split(",")] if isinstance(pfx, str) else pfx
    )
    networks = []
    for prefix in prefixes:
        try:
            networks.append(ipaddress.ip_network(prefix))
        except Exception as e:
            log.error(
                "FP failed to convert prefix '{}', error '{}'".format(
                    prefix, e
                )
            )
    # filter hosts
    return ret.filter(filter_func=_filter_net)


def _filter_FL(ret, names_list):
    """
    Function to filter hosts names based on list of names
    """
    names_list = (
        [i.strip() for i in names_list.split(",")]
        if isinstance(names_list, str)
        else names_list
    )
    return ret.filter(filter_func=lambda h: h.name in names_list)
