"""
PureSNMPPlugin
##############

Connection plugin to interact with devices over SNMP using
`puresnmp library <https://github.com/exhuma/puresnmp>`_.

If planning to use puresnmp plugin with SNMPv3 make sure to install
additional dependencies on proxy minion. For example, for RedHAT Linux
(CentOS, RockyLinux etc.) install gcc and Python devel packages
substituting python39 with version of Python in use::

    dnf install gcc python39-devel

Install pycrypto and puresnmp-crypto Python modules using ``crypto`` extras::

    pip install puresnmp[crypto]

This connection plugin based on puresnmp supports SNMP version 1, 2c and 3.

PureSNMPPlugin reference
========================

.. autofunction:: nornir_salt.plugins.connections.PureSNMPPlugin.PureSNMPPlugin
"""
import logging

from typing import Any, Dict, Optional
from nornir.core.configuration import Config

log = logging.getLogger(__name__)

try:
    from puresnmp import Client, PyWrapper, V1, V2C, V3
    from puresnmp.credentials import Auth, Priv

    HAS_PURESNMP = True
except ImportError:
    HAS_PURESNMP = False

CONNECTION_NAME = "puresnmp"


class PureSNMPPlugin:
    """
    This plugin connects to the device via SNMP using Python ``puresnmp`` library.

    Connection inventory reference name is ``puresnmp``

    Sample Nornir inventory::

        hosts:
          ceos1:
            hostname: 10.0.1.4
            platform: arista_eos
            groups: [lab, connection_params_v2c]

          ceos2:
            hostname: 10.0.1.5
            platform: arista_eos
            groups: [lab, connection_params_v3]

        groups:
          lab:
            username: nornir
            password: nornir
          connection_params_snmpv1:
            connection_options:
              puresnmp:
                port: 161
                extras:
                  version: v1
                  community: public
          connection_params_snmpv2c:
            connection_options:
              puresnmp:
                port: 161
                extras:
                  version: v2c
                  community: public
          # this inventory uses specific passwords for auth and priv
          connection_params_snmpv3:
            connection_options:
              puresnmp:
                port: 161
                username: snmpv3_user
                extras:
                  version: v3
                  auth:
                    password: auth_pass
                    method: md5
                  priv:
                    password: priv_pass
                    method: des
          # this inventory uses "password: public" for auth and priv
          connection_params_snmpv3_common_password:
            connection_options:
              puresnmp:
                port: 161
                username: snmpv3_user
                password: public
                extras:
                  version: v3
                  auth:
                    method: sha1
                  priv:
                    method: aes

    As an example, ``connection_params_snmpv2c`` inventory entry above
    matches this Arista cEOS SNMPv2c configuration::

        snmp-server community public rw

    As an example, ``connection_params_snmpv3`` inventory entry above
    matches this Arista cEOS SNMPv3 configuration::

        snmp-server view snmpv3 iso included
        snmp-server group snmpview v3 priv write snmpv3
        snmp-server user snmpv3_user snmpview v3 auth md5 auth_pass priv des priv_pass
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
        SNMP does not maintain connection open, hence this method does not
        open connection but rather only creates client object for requests.
        """
        extras = extras or {}

        port = extras.get("port", port)
        version = extras.get("version", "v2c")
        community = extras.get("community", "public")

        # extract SNMPv3 params
        auth = extras.get("auth", {})
        auth.setdefault("password", password)
        priv = extras.get("priv", {})
        priv.setdefault("password", password)

        if version == "v1":
            self.connection = PyWrapper(
                Client(ip=hostname, credentials=V1(community), port=port)
            )
        elif version == "v2c":
            self.connection = PyWrapper(
                Client(ip=hostname, credentials=V2C(community), port=port)
            )
        elif version == "v3":
            self.connection = PyWrapper(
                Client(
                    ip=hostname,
                    credentials=V3(
                        username=username,
                        auth=Auth(
                            auth["password"].encode(encoding="utf-8"), auth["method"]
                        ),
                        priv=Priv(
                            priv["password"].encode(encoding="utf-8"), priv["method"]
                        ),
                    ),
                    port=port,
                )
            )

    def close(self) -> None:
        """
        SNMP does not maintain connection open, hence this method does nothing.
        """
        self.connection = None
