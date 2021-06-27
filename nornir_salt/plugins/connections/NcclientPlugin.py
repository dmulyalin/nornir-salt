"""

"""
from typing import Any, Dict, Optional
from pathlib import Path
from ncclient import manager
from nornir.core.configuration import Config

CONNECTION_NAME = "ncclient"


class NcclientPlugin:
    """
    This plugin connects to the device via NETCONF using ncclient library.
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
