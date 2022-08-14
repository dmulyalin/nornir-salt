"""
NcclientPlugin
##############

Ncclient library connection plugin to interact with devices over NETCONF.

NcclientPlugin reference
========================

.. autofunction:: nornir_salt.plugins.connections.NcclientPlugin.NcclientPlugin
"""
import logging

from typing import Any, Dict, Optional
from pathlib import Path
from nornir.core.configuration import Config

log = logging.getLogger(__name__)

try:
    from ncclient import manager
    from ncclient.operations import RaiseMode

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
                raise_mode: None

    Everything under inventory ``extras`` section passed on to Ncclient
    ``manager.connect`` call except for non Ncclient specific arguments.

    **``extras`` section non Ncclient specific arguments**

    ``raise_mode`` - valid values are None, "all" (default) or "errors",
    defines how errors indicated by RPC handled by Ncclient:

    - ``None`` - don't raise any type of `rpc-error` as exception
    - ``errors`` - raise only when the `error-type` indicates it is an error
    - ``all`` - don't look at the `error-type`, always raise
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

        raise_mode = extras.pop("raise_mode", "all")

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

        # apply raise mode settings to connection
        self.connection.raise_mode = getattr(RaiseMode, str(raise_mode).upper())

        log.debug(
            f"Nornir-Salt:NcclientPlugin initiated connection with "
            f"RaiseMode '{self.connection.raise_mode}'"
        )

    def close(self) -> None:
        self.connection.close_session()
