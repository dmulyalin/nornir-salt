import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


spec = importlib.util.spec_from_file_location(
    "hosts_keepalive",
    Path(__file__).resolve().parents[1]
    / "nornir_salt/plugins/functions/HostsKeepalive.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestHostsKeepalive(unittest.TestCase):
    def run_keepalive(self, alive=True, write_error=None):
        connection = Mock()
        connection.is_alive.return_value = alive
        connection.write_channel.side_effect = write_error
        plugin = type("Netmiko", (), {})()
        plugin.connection = connection
        host = SimpleNamespace(connections={"netmiko": plugin}, close_connection=Mock())
        nr = SimpleNamespace(inventory=SimpleNamespace(hosts={"leaf1": host}))
        stats = module.HostsKeepalive(nr)
        return connection, host, stats

    def test_dead_connection_skips_recovery_and_is_removed(self):
        connection, host, stats = self.run_keepalive(alive=False)
        connection.write_channel.assert_not_called()
        connection.clear_buffer.assert_not_called()
        host.close_connection.assert_called_once_with("netmiko")
        self.assertEqual(host.connections, {})
        self.assertEqual(stats["dead_connections_cleaned"], 1)

    def test_live_connection_runs_recovery_and_is_retained(self):
        connection, host, stats = self.run_keepalive()
        connection.write_channel.assert_called_once_with(" ")
        connection.clear_buffer.assert_called_once_with()
        host.close_connection.assert_not_called()
        self.assertIn("netmiko", host.connections)
        self.assertEqual(stats["dead_connections_cleaned"], 0)

    def test_disconnect_logs_short_message_without_traceback(self):
        with self.assertLogs(module.log, level=logging.DEBUG) as captured:
            connection, host, stats = self.run_keepalive(
                write_error=OSError("Socket is closed")
            )
        info = [r for r in captured.records if r.levelno == logging.INFO]
        failure = next(r for r in info if "Socket is closed" in r.getMessage())
        self.assertIn("leaf1", failure.getMessage())
        self.assertIn("netmiko", failure.getMessage())
        self.assertEqual(
            failure.getMessage(),
            "HostsKeepalive - 'leaf1' 'netmiko' keepalive failed: Socket is closed",
        )
        self.assertNotIn("Traceback", failure.getMessage())
        self.assertIsNone(failure.exc_info)
        self.assertFalse(any(r.levelno == logging.DEBUG for r in captured.records))
        connection.clear_buffer.assert_not_called()
        host.close_connection.assert_called_once_with("netmiko")
        self.assertEqual(stats["dead_connections_cleaned"], 1)
