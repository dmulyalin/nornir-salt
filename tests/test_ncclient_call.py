"""Offline NETCONF transaction checks using real ncclient reply objects."""

import importlib
from contextlib import nullcontext
from unittest.mock import Mock

import pytest

pytest.importorskip("ncclient")
from ncclient.capabilities import Capabilities
from ncclient.operations.rpc import RPCReply
from nornir.core.inventory import Host
from nornir.core.task import Task

ncclient_call = importlib.import_module("nornir_salt.plugins.tasks.ncclient_call")


@pytest.fixture
def manager():
    reply = RPCReply(
        '<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><ok/></rpc-reply>'
    )
    assert reply.ok  # ncclient parses replies before returning them to callers.
    manager = Mock()
    manager.server_capabilities = Capabilities(
        [
            "urn:ietf:params:netconf:capability:candidate:1.0",
            "urn:ietf:params:netconf:capability:validate:1.0",
            "urn:ietf:params:netconf:capability:confirmed-commit:1.1",
        ]
    )
    manager.locked.return_value = nullcontext()
    for method in ("discard_changes", "edit_config", "validate", "commit"):
        getattr(manager, method).return_value = reply
    return manager


@pytest.fixture
def error_reply():
    reply = RPCReply(
        """<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
        <rpc-error><error-type>application</error-type>
        <error-tag>operation-failed</error-tag><error-severity>error</error-severity>
        <error-message>rejected configuration</error-message></rpc-error></rpc-reply>"""
    )
    assert not reply.ok
    return reply


def test_transaction_final_commit_confirms_changes(manager):
    _, failed = ncclient_call._call_transaction(
        manager, config="<config/>", commit_final_delay=0
    )
    assert not failed
    first, final = manager.commit.call_args_list
    assert first.kwargs["confirmed"] is True
    assert final.kwargs == {"persist_id": first.kwargs["persist"]}


def test_transaction_preserves_juniper_fallback(manager):
    reply = manager.commit.return_value
    manager.commit.side_effect = [TypeError("persist unsupported"), reply, reply]
    _, failed = ncclient_call._call_transaction(
        manager, config="<config/>", commit_final_delay=0
    )
    assert not failed
    assert manager.commit.call_count == 3
    assert manager.commit.call_args.kwargs == {}


@pytest.mark.parametrize(
    "stage",
    [
        "discard_changes",
        "edit_config",
        "validate",
        "first_commit",
        "final_commit",
        "plain_commit",
    ],
)
def test_transaction_stops_on_error_replies(manager, error_reply, stage):
    reply = manager.commit.return_value
    if stage == "discard_changes":
        manager.discard_changes.side_effect = [error_reply, reply]
    elif stage == "final_commit":
        manager.commit.side_effect = [reply, error_reply]
    elif stage in ("first_commit", "plain_commit"):
        manager.commit.return_value = error_reply
    else:
        getattr(manager, stage).return_value = error_reply

    result, failed = ncclient_call._call_transaction(
        manager,
        config="<config/>",
        commit_final_delay=0,
        confirmed=stage != "plain_commit",
    )
    assert failed
    assert any("rejected configuration" in step.get("error", "") for step in result)
    expected_commits = (
        2 if stage == "final_commit" else int(stage in ("first_commit", "plain_commit"))
    )
    assert manager.commit.call_count == expected_commits
    if stage in ("discard_changes", "edit_config"):
        manager.validate.assert_not_called()
    if stage == "discard_changes":
        manager.edit_config.assert_not_called()


def test_direct_rpc_error_is_a_failed_result(manager, error_reply, monkeypatch):
    task = Task(
        task=ncclient_call.ncclient_call,
        nornir=Mock(),
        global_dry_run=False,
        processors=[],
    )
    task.host = Host(name="offline")
    manager._vendor_operations = {}
    manager.edit_config.return_value = error_reply
    monkeypatch.setattr(Host, "get_connection", Mock(return_value=manager))
    result = ncclient_call.ncclient_call(task, call="edit_config", config="<config/>")
    assert result.failed
    assert "rpc-error" in result.result


def test_transaction_handles_raised_rpc_errors(manager, error_reply):
    manager.edit_config.side_effect = error_reply.error
    result, failed = ncclient_call._call_transaction(manager, config="<config/>")
    assert failed
    manager.commit.assert_not_called()
    assert any("rejected configuration" in step.get("error", "") for step in result)


def test_direct_rpc_success_is_preserved(manager, monkeypatch):
    task = Task(
        task=ncclient_call.ncclient_call,
        nornir=Mock(),
        global_dry_run=False,
        processors=[],
    )
    task.host = Host(name="offline")
    manager._vendor_operations = {}
    monkeypatch.setattr(Host, "get_connection", Mock(return_value=manager))
    result = ncclient_call.ncclient_call(task, call="edit_config", config="<config/>")
    assert not result.failed
    assert "<ok/>" in result.result
