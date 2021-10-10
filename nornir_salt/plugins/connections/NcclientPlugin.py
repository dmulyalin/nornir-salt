"""
NcclientPlugin
##############

Ncclient library connection plugin to interact with devices over NETCONF.

NcclientPlugin reference
========================

.. autofunction:: nornir_salt.plugins.connections.NcclientPlugin.NcclientPlugin
"""
from typing import Any, Dict, Optional
from pathlib import Path
from nornir.core.configuration import Config

try:
    from ncclient import manager

    HAS_NCCLIENT = True
except ImportError:
    HAS_NCCLIENT = False

CONNECTION_NAME = "ncclient"


class NcclientPlugin:
    """
    Full list of inventory extras see Ncclient Docs for ``manager.connect``
    method.

    Example on how to configure a device to use netconfig without using
    an ssh agent and without verifying the keys::

        host-1:
          hostname: 192.168.16.20
          username: admin
          password: admin
          port: 2022
          connection_options:
            ncclient:
              extras:
                allow_agent: False
                hostkey_verify: False

    Anything under inventory ``extras`` section passed on to Ncclient
    ``manager.connect`` call.
    """  # noqa

    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        extras = extras or {}

        parameters: Dict[str, Any] = {
            "host": hostname,
            "username": username,
            "password": password,
            "port": port or 830,
        }

        if "ssh_config" not in extras:
            ssh_config_file = Path(configuration.ssh.config_file)
            if ssh_config_file.exists():
                parameters["ssh_config"] = ssh_config_file

        parameters.update(extras)

        self.connection = manager.connect(**parameters)

    def close(self) -> None:
        self.connection.close_session()
