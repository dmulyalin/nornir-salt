"""
HTTPPlugin
##########

HTTP Connection plugin to interact with devices over HTTP/HTTPS.

HTTPPlugin reference
====================

.. autofunction:: nornir_salt.plugins.connections.HTTPPlugin.HTTPPlugin
"""
from typing import Any, Dict, Optional
from nornir.core.configuration import Config

CONNECTION_NAME = "http"


class HTTPPlugin:
    """
    This plugin connects to the device via HTTP using Python
    requests library.

    Connection reference name is ``http``

    Full list of inventory extras see `here <https://docs.python-requests.org/en/latest/api/>`_

    Sample Nornir inventory::

        hosts:
          ceos1:
            hostname: 10.0.1.4
            platform: arista_eos
            groups: [lab, connection_params]

          ceos2:
            hostname: 10.0.1.5
            platform: arista_eos
            groups: [lab, connection_params]

        groups:
          lab:
            username: nornir
            password: nornir
          connection_params:
            connection_options:
              http:
                port: 80
                extras:
                  transport: http
                  verify: False
                  base_url: "http://device1.lab/api/v1/"
                  headers:
                    Content-Type: "application/yang-data+json"
                    Accept: "application/yang-data+json"

    Anything under inventory extras section passed on to
    ``requests.request(method, url, **kwargs)`` call in a form of ``**kwargs``
    except for ``transport`` and ``base_url``. Inventory parameters can be
    overridden on task call.

    ``transport`` and ``base_url`` - used to form URL to send request to if no
    absolute URL provided on task call.
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
