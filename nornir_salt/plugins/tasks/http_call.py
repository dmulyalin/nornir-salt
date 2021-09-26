"""
http_call
#########

This task plugin is to interact with devices over HTTP and is capable
of calling any method of Python built-in ``requests`` library.

http_call sample usage
======================

Sample code to run ``http_call`` task::

    from nornir_salt import http_call
    from nornir import InitNornir

    nr = InitNornir(config_file="nornir_config.yaml")

    res = nr.run(
        task=http_call,
        method="get",
        url="https://google.com",
    )

http_call returns
=================

Returns requests result string in XML or JSON format.

http_call reference
===================

.. autofunction:: nornir_salt.plugins.tasks.http_call.http_call
"""
import logging
import json
import requests
from nornir.core.task import Result, Task
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "http"


def http_call(task: Task, method: str, url: str = None, **kwargs) -> Result:
    """
    Task function to call one of the supported ``requests`` library methods.

    :param method: (str) requests method to call
    :param url: (str) relative to base_url or absolute URL to send request to
    :param kwargs: (dict) any ``**kwargs`` to use with requests method call
    :return: (str) attempt to return JSON formatted string if ``json`` string
        pattern found in response's ``Content-type`` header, returns response
        text otherwise

    ``http_call`` follows these rules to form URL to send request to:

    1. Use ``url`` attribute if provided and it starts with ``http://`` or ``https://``
    2. If ``url`` attribute provided but is relative it is merged with
        inventory ``base_url`` using formatter ``{base_url}/{url}``
    3. If ``url`` attribute provided and is relative and no ``base_url``
        defined in inventory ``extras`` sections uses this formatter
        ``{transport}://{hostname}:{port}/{url}`` to form final URL
        if ``transport`` parameter defined in inventory ``extras`` sections
    4. If no ``url`` attribute provided use ``base_url`` to send the request if
        ``base_url`` defined in inventory ``extras`` sections
    5. If no ``url`` attribute provided and no ``base_url`` defined in inventory
        ``extras`` sections use this formatter ``{transport}://{hostname}:{port}/``
        if ``transport`` parameter defined in inventory ``extras`` sections

    Default headers added to HTTP request::

            'Content-Type': 'application/yang-data+json',
            'Accept': 'application/yang-data+json'

    If no ``auth`` attribute provided in task ``kwargs``, host's username and
    password inventory parameters used to form ``auth`` tuple.
    """
    result = None

    # get rendered data if any
    if "__task__" in task.host.data:
        kwargs.update(task.host.data["__task__"])

    # get http connection inventory parameters
    conn = task.host.get_connection("http", task.nornir.config)

    log.debug(
        "nornir_salt:http_call calling '{}' with kwargs: '{}'; connection: '{}'".format(
            method, kwargs, conn
        )
    )

    # form requests parameters
    parameters = {
        "timeout": (5, 5),
        **conn["extras"],
        **kwargs,
    }

    # clean up parameters
    transport = parameters.pop("transport", None)
    base_url = parameters.pop("base_url", None)

    # add auth
    if "auth" not in parameters and conn.get("hostname") and conn.get("password"):
        parameters["auth"] = (conn["username"], conn["password"])
    # make sure auth is a tuple
    elif "auth" in parameters:
        parameters["auth"] = tuple(parameters["auth"])

    # form url
    if url:
        # if URL provided but it is relative to base url
        if not url.startswith("http://") and not url.startswith("https://"):
            # use base URL if it was provided in inventory
            if base_url:
                parameters["url"] = "{base_url}/{url}".format(
                    base_url=base_url, url=url
                )
            # form URL using transport, hostname and port parameters
            elif transport:
                parameters["url"] = "{transport}://{hostname}:{port}/{url}".format(
                    transport=transport,
                    hostname=conn["hostname"],
                    port=int(conn.get("port", 80 if transport == "http" else 443)),
                    url=url,
                )
            else:
                raise RuntimeError(
                    "nornir-salt:http_call cannot form URL. base_url or transport required, params given: {}".format(
                        parameters
                    )
                )
        else:
            parameters["url"] = url
    # use base_url if no url provided
    elif base_url:
        parameters["url"] = base_url
    # form url using transport, hostname and port parameters
    elif transport:
        parameters["url"] = "{transport}://{hostname}:{port}/".format(
            transport=transport,
            hostname=conn["hostname"],
            port=int(conn.get("port", 80 if transport == "http" else 443)),
        )
    else:
        raise RuntimeError(
            "nornir-salt:http_call cannot form URL. url, base_url or transport required, params given: {}".format(
                parameters
            )
        )

    # add headers
    parameters.setdefault(
        "headers",
        {
            "Content-Type": "application/yang-data+json",
            "Accept": "application/yang-data+json",
        },
    )

    # call requests method
    response = getattr(requests, method)(**parameters)

    # form results
    if "json" in response.headers.get("Content-type", "text"):
        try:
            result = response.json()
        except requests.exceptions.ContentDecodingError:
            result = response.text
        except json.decoder.JSONDecodeError:
            result = response.text
    else:
        result = response.text

    return Result(host=task.host, result=result, failed=not response.ok)
