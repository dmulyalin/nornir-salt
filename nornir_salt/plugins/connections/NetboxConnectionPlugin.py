"""
NetboxConnectionPlugin
######################

Netbox Connection plugin to communicate with Netbox.

NetboxConnectionPlugin reference
================================

.. autofunction:: nornir_salt.plugins.connections.NetboxConnectionPlugin.NetboxConnectionPlugin
"""
import logging
from typing import Any, Dict, Optional
from nornir.core.configuration import Config

log = logging.getLogger(__name__)


CONNECTION_NAME = "netbox"


class NetboxConnectionPlugin:
    """
    This plugin connects to Netbox Inventory system using
    `pynetbox <https://github.com/netbox-community/pynetbox>`_
    library.

    Nornir inventory connection reference name is ``netbox``

    Sample Nornir inventory::

        hosts:
          ceos1:
            hostname: 10.0.1.4
            platform: arista_eos
            groups: [lab, netbox_connection]

          ceos2:
            hostname: 10.0.1.5
            platform: arista_eos
            groups: [lab, netbox_connection]

        groups:
          lab:
            username: nornir
            password: nornir
          netbox_connection:
            connection_options:
              netbox:
                username: admin
                password: admin
                port: 8000
                extras:
                  instances:
                    dev:
                      auth: ["dev", "dev123"]
                      url: http://192.168.64.201:8000/
                    staging:
                      url: http://192.168.64.202:8000/
                    production:
                      url: http://192.168.64.203:8000/
                      token: 0123456789abcdef0123456789abcdef01234569
                      default: True

        user_defined:
          netbox:
            prod:
              url: http://192.168.64.203:8000/
              token: 0123456789abcdef0123456789abcdef01234569

    NetboxConnectionPlugin supports definition of multiple instances of Netbox
    parameters which are stored under ``netbox`` key in host connections extras
    dictionary and can be retrieved using below code in task plugins::

        def my_task(task):

            netboxes = task.host.get_connection("netbox", task.nornir.config)

    where ``netboxes`` is a dictionary keyed by netbox instances names.

    Individual instance parameters used to instantiate ``pynetbox.api`` object.

    For a full list of inventory instance parameters refer to
    `pynetbox.api documentation <https://pynetbox.readthedocs.io/en/latest/>`_

    Authentication - by default ``token`` takes precedence over ``auth``. If no ``token``
    or ``auth`` defined in instance parameters, ``auth`` credentials automatically formed 
    using host's username and password attributes.

    Alternatively, Netbox connection parameters can be stored in ``user_defined ``
    configuration instead of individual hosts, groups or defaults. Parameters
    in ``user_defined`` configuration merged with extras configuration. Extras
    configuration takes precedence over ``user_defined`` configuration.

    NetboxConnectionPlugin inventory extras parameters:

    :param instances: (dict) dictionary keyed by instance name with parameters

    Individual instance parameters:

    :param auth: (list) list of Netbox ``[password, username]``
    :param default: (bool) if True, this instance is a default Netbox instance
    :param url: (str) Netbox API URL
    :param token: (str) Netbox API token

    Netbox Task plugins use ``via`` attribute to refer to Netbox instance name
    to use for task execution, ``via`` attribute by default points to instance marked
    as ``default: True`` or at first instance if none of the instances indicated as
    default.
    """  # noqa

    def open(
        self,
        hostname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        port: Optional[int] = None,
        platform: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        """
        NetboxConnectionPlugin does not maintain connection open, hence this
        method does nothing apart from saving inventory parameters in connection
        dictionary.
        """
        self.connection = {}
        extras = extras or {}

        common_params = {
            "auth": (username, password),
            "threading": False,
        }

        netbox_config = configuration.user_defined.get("netbox", {})

        # form Netbox instance parameters using user_defined configuration
        for name, params in netbox_config.get("instances", {}).items():
            self.connection[name] = {**common_params, **params}
            if "token" in self.connection[name]:
                self.connection[name].pop("auth")
            if params.pop("default", None) is True:
                self.connection["default"] = self.connection[name]

        # form Netbox instances connection parameters using host extras
        for name, params in extras["instances"].items():
            self.connection[name] = {**common_params, **params}
            if "token" in self.connection[name]:
                self.connection[name].pop("auth")
            if params.pop("default", None) is True:
                self.connection["default"] = self.connection[name]

        # add default instance params reference
        self.connection.setdefault("default", list(self.connection.values())[0])

        log.debug(
            "NetboxConnectionPlugin instances retrieved: {}".format(
                ", ".join(self.connection.keys())
            )
        )

    def close(self) -> None:
        """
        Wipe out Netbox instances connection parameters.
        """
        self.connection = {}
