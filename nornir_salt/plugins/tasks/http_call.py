"""
http_call
#########

TBD

http_call sample usage
======================

Sample code to run ``http_call`` task::

    TBD

http_call returns
=================

Returns XML text string by default, but can return XML data transformed
in JSON, YAML or Python format.

http_call reference
===================

.. autofunction:: nornir_salt.plugins.tasks.http_call.http_call
"""
import logging
import json
import pprint
import traceback
import requests
from nornir.core.task import Result, Task
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "http"

def http_call(task: Task, method: str, **kwargs) -> Result:
    """
    Task function to call one of the supported requests methods
    or one of the helper functions.
    
    :param method: (str) requests method to call
    :param kwargs: (dict) any ``**kwargs`` to use with call method
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
        
    # form url
    if "url" in parameters:
        # if URL provided but it is relative to base url
        if not parameters["url"].startswith("http://") and not parameters["url"].startswith("https://"):
            # use base URL if it was provided in inventory
            if base_url:
                parameters["url"] = "{}/{}".format(base_url, parameters["url"])
            # form URL using transport, hostname and port parameters
            elif transport:
                parameters["url"] = "{transport}://{hostname}:{port}/{url}".format(
                    transport=transport, 
                    hostname=conn["hostname"],
                    port=int(conn.get("port", 80 if transport=="http" else 443)),
                    url=parameters["url"]
                )
            else:
                raise RuntimeError("nornir-salt:http_call cannot form URL. base_url or transport required, params given: {}".format(parameters))
    # use base_url if no url provided
    elif base_url:
        parameters["url"] = base_url
    # form url using transport, hostname and port parameters
    elif transport:
        parameters["url"] = "{transport}://{hostname}:{port}/".format(
            transport=transport, 
            hostname=conn["hostname"],
            port=int(conn.get("port", 80 if transport=="http" else 443))
        )        
    else:
        raise RuntimeError("nornir-salt:http_call cannot form URL. url, base_url or transport required, params given: {}".format(parameters))

    # add headers
    parameters.setdefault("headers", {
            'Content-Type': 'application/yang-data+json',
            'Accept': 'application/yang-data+json'
        }
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

    return Result(
        host=task.host, 
        result=result,
        failed=not response.ok
    )
