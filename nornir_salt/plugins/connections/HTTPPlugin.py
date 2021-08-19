from typing import Any, Dict, Optional
from nornir.core.configuration import Config

CONNECTION_NAME = "http"

class HTTPPlugin:
    """
    This plugin connects to the device via HTTP using requests library.
    
    Inventory extras see `here <https://docs.python-requests.org/en/latest/api/>`_
        
    Sample inventory::
    
        ---
        nc_device:
            hostname: "https://192.168.1.1/"
            username: admin
            password: admin
            port: 8088
            connection_options:
                http:
                    extras:
                        verify : False

    Then it can be used like::
    
        TBD
        
    """  # noqa

    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        extras: Optional[Dict[str, Any]],
        configuration: Optional[Config],
    ) -> None:
        """
        HTTP does not maintain connection open, hence this method does nothing
        apart from saving inventory parameters in connection dictionary.
        """
        self.connection = {
            "extras": extras,
            "configuration": configuration,
            "hostname": hostname,
            "username": username,
            "password": password,
            "port": port,
            "platform": platform,
        }

    def close(self) -> None:
        """
        HTTP does not maintain connection open, hence this method does nothing.
        """
        self.connection = {}
