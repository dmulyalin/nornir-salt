import sys
import os
import pprint
import logging
import yaml
import pytest
import time
import json

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.inventory import InventoryPluginRegister
    from nornir.core.task import Result

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt import ResultSerializer
from nornir_salt import DictInventory
from nornir_salt import nr_test
from nornir_salt.plugins.processors.ToFileProcessor import ToFileProcessor
from nornir_salt.plugins.processors.DataProcessor import DataProcessor
from nornir_salt.plugins.tasks import file_read, file_remove, file_list, file_diff, files

logging.basicConfig(level=logging.ERROR)


# ----------------------------------------------------------------------
# Initialize Nornir
# ----------------------------------------------------------------------


skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)
skip_if_no_lab = None

lab_inventory = """
hosts:
  IOL1:
    hostname: 192.168.217.10
    platform: ios
    groups: [lab]
  IOL2:
    hostname: 192.168.217.7
    platform: ios
    groups: [lab]

groups:
  lab:
    username: cisco
    password: cisco

defaults: {}
"""
lab_inventory_dict = yaml.safe_load(lab_inventory)


def init(opts):
    """
    Initiate nornir by calling InitNornir()
    """
    global skip_if_no_lab

    nr = InitNornir(
        logging={"enabled": False},
        runner={"plugin": "serial"},
        inventory={
            "plugin": "DictInventory",
            "options": {
                "hosts": opts["hosts"],
                "groups": opts.get("groups", {}),
                "defaults": opts.get("defaults", {}),
            },
        },
    )

    return nr


InventoryPluginRegister.register("DictInventory", DictInventory)

nr = init(lab_inventory_dict)


def clean_up_folder():
    # remove previous files and folder
    if os.path.exists("./tofile_outputs/"):
        for filen in os.listdir("./tofile_outputs/"):
            os.remove("./tofile_outputs/" + filen)
        os.rmdir("./tofile_outputs/")

def nr_test_grouped_subtasks(task, task_1, task_2):
    """
    Test grouped task
    """
    task.run(**task_1)
    task.run(**task_2)
    return Result(host=task.host, skip_results=True)

def generate_files(tf):
    """
    Helper function to generate files by running task
    """
    iol1_res_ntp = [
{"ntp": "1.1.1.1"},
    ]
    iol2_res_ntp = [
{"ntp": "2.2.2.2"},
    ]
    iol1_res_log = [
{"log": "3.3.3.3"},
    ]
    iol2_res_log = [
{"log": "4.4.4.4"},
    ]

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf=tf, base_url="./tofile_outputs/")]
    )

    # first task run
    nr_with_tf.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_ntp,
                "IOL2": iol2_res_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_log,
                "IOL2": iol2_res_log,
            },
            "name": "show run | inc logging",
        },
    )

# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_file_read_task():
    clean_up_folder()

    iol1_res = """
Timestamp 12:12:12

ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol2_res = """
ntp server 7.7.7.7
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res,
            "IOL2": iol2_res,
        },
        name="show run | inc ntp",
    )

    # retrieve file content
    res = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
    )

    res = ResultSerializer(res, add_details=True)
    # pprint.pprint(res)
    # {'IOL1': {'show run | inc ntp': {'changed': False,
    #                                  'diff': '',
    #                                  'exception': None,
    #                                  'failed': False,
    #                                  'result': '\n'
    #                                            'Timestamp 12:12:12\n'
    #                                            '\n'
    #                                            'ntp server 7.7.7.8\n'
    #                                            'ntp server 7.7.7.7\n'
    #                                            '        \n'}},
    #  'IOL2': {'show run | inc ntp': {'changed': False,
    #                                  'diff': '',
    #                                  'exception': None,
    #                                  'failed': False,
    #                                  'result': '\nntp server 7.7.7.7\n        \n'}}}
    assert res["IOL1"]["show run | inc ntp"]["result"] == iol1_res
    assert res["IOL2"]["show run | inc ntp"]["result"] == iol2_res

# test_file_read_task()


@skip_if_no_nornir
def test_file_read_task_last2():
    clean_up_folder()

    iol1_res = """
Timestamp 12:12:12

ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol2_res = """
ntp server 7.7.7.7
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )

    # first task run
    nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res,
            "IOL2": iol2_res,
        },
        name="show run | inc ntp",
    )
    # second, most current/latest run
    nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res + "IOL1 12345",
            "IOL2": iol2_res + "IOL2 12345",
        },
        name="show run | inc ntp",
    )

    # retrieve file content
    res1 = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
        last=1,
    )
    res2 = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
        last=2,
    )

    res1 = ResultSerializer(res1, add_details=True)
    res2 = ResultSerializer(res2, add_details=True)

    # pprint.pprint(res1)
    # pprint.pprint(res2)

    assert res2["IOL1"]["show run | inc ntp"]["result"] == iol1_res
    assert res2["IOL2"]["show run | inc ntp"]["result"] == iol2_res
    assert res1["IOL1"]["show run | inc ntp"]["result"] == iol1_res + "IOL1 12345"
    assert res1["IOL2"]["show run | inc ntp"]["result"] == iol2_res + "IOL2 12345"

# test_file_read_task_last2()

@skip_if_no_nornir
def test_file_read_result_with_subtasks():
    clean_up_folder()

    iol1_res_ntp = """
Timestamp 12:12:12

ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol2_res_ntp = """
ntp server 7.7.7.7
        """
    iol1_res_log = """
logging host 1.2.3.4
logging host 4.4.4.4
        """
    iol2_res_log = """
logging host 5.5.5.5
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )

    # first task run
    nr_with_tf.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_ntp,
                "IOL2": iol2_res_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_log,
                "IOL2": iol2_res_log,
            },
            "name": "show run | inc logging",
        },
    )

    # retrieve file content
    res = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
    )

    res = ResultSerializer(res, add_details=True)

    # pprint.pprint(res)
    # {'IOL1': {'show run | inc logging': {'changed': False,
    #                                      'diff': '',
    #                                      'exception': None,
    #                                      'failed': False,
    #                                      'result': '\n'
    #                                                'logging host 1.2.3.4\n'
    #                                                'logging host 4.4.4.4\n'
    #                                                '        '},
    #           'show run | inc ntp': {'changed': False,
    #                                  'diff': '',
    #                                  'exception': None,
    #                                  'failed': False,
    #                                  'result': '\n'
    #                                            'Timestamp 12:12:12\n'
    #                                            '\n'
    #                                            'ntp server 7.7.7.8\n'
    #                                            'ntp server 7.7.7.7\n'
    #                                            '        '}},
    #  'IOL2': {'show run | inc logging': {'changed': False,
    #                                      'diff': '',
    #                                      'exception': None,
    #                                      'failed': False,
    #                                      'result': '\n'
    #                                                'logging host 5.5.5.5\n'
    #                                                '        '},
    #           'show run | inc ntp': {'changed': False,
    #                                  'diff': '',
    #                                  'exception': None,
    #                                  'failed': False,
    #                                  'result': '\nntp server 7.7.7.7\n        '}}}

    assert res["IOL1"]["show run | inc ntp"]["result"] == iol1_res_ntp
    assert res["IOL1"]["show run | inc logging"]["result"] == iol1_res_log
    assert res["IOL2"]["show run | inc ntp"]["result"] == iol2_res_ntp
    assert res["IOL2"]["show run | inc logging"]["result"] == iol2_res_log

# test_file_read_result_with_subtasks()


@skip_if_no_nornir
def test_file_read_result_with_subtasks_task_name():
    """ Should return task results for one task only """
    clean_up_folder()

    iol1_res_ntp = """
Timestamp 12:12:12

ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol2_res_ntp = """
ntp server 7.7.7.7
        """
    iol1_res_log = """
logging host 1.2.3.4
logging host 4.4.4.4
        """
    iol2_res_log = """
logging host 5.5.5.5
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )

    # first task run
    nr_with_tf.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_ntp,
                "IOL2": iol2_res_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_log,
                "IOL2": iol2_res_log,
            },
            "name": "show run | inc logging",
        },
    )

    # retrieve file content
    res = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
        task_name="show run | inc logging"
    )

    res = ResultSerializer(res, add_details=True)

    pprint.pprint(res)
    # {'IOL1': {'show run | inc logging': {'changed': False,
    #                                      'diff': '',
    #                                      'exception': None,
    #                                      'failed': False,
    #                                      'result': '\n'
    #                                                'logging host 1.2.3.4\n'
    #                                                'logging host 4.4.4.4\n'
    #                                                '        '}},
    #  'IOL2': {'show run | inc logging': {'changed': False,
    #                                      'diff': '',
    #                                      'exception': None,
    #                                      'failed': False,
    #                                      'result': '\n'
    #                                                'logging host 5.5.5.5\n'
    #                                                '        '}}}

    assert "show run | inc ntp" not in res["IOL1"]
    assert res["IOL1"]["show run | inc logging"]["result"] == iol1_res_log
    assert "show run | inc ntp" not in res["IOL2"]
    assert res["IOL2"]["show run | inc logging"]["result"] == iol2_res_log

# test_file_read_result_with_subtasks_task_name()


@skip_if_no_nornir
def test_file_read_task_struct_data():
    """ test that structured data save as a json and read back in struct """
    clean_up_folder()

    iol1_res = [
{"ip": "1.2.3.4", "interface": "Gi123"},
{"ip": "2.2.2.2", "interface": "Gi2"},
{"ip": "3.3.3.3", "interface": "Gi3"},
    ]
    iol2_res = [
{"ip": "4.4.4.4", "interface": "Gi2"},
    ]

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res,
            "IOL2": iol2_res,
        },
        name="show run | inc ntp",
    )

    # retrieve file content
    res = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
    )

    res = ResultSerializer(res, add_details=True)
    # pprint.pprint(res)
    _ = res["IOL1"]['show run | inc ntp'].pop("timestamp")
    _ = res["IOL2"]['show run | inc ntp'].pop("timestamp")
    assert res == {'IOL1': {'show run | inc ntp': {'changed': False,
                                                   'diff': '',
                                                   'exception': None,
                                                   'failed': False,
                                                   'filegroup': 'config_for_read',
                                                   'result': [{'interface': 'Gi123',
                                                               'ip': '1.2.3.4'},
                                                              {'interface': 'Gi2',
                                                               'ip': '2.2.2.2'},
                                                              {'interface': 'Gi3',
                                                               'ip': '3.3.3.3'}]}},
                   'IOL2': {'show run | inc ntp': {'changed': False,
                                                   'diff': '',
                                                   'exception': None,
                                                   'failed': False,
                                                   'filegroup': 'config_for_read',
                                                   'result': [{'interface': 'Gi2',
                                                               'ip': '4.4.4.4'}]}}}

# test_file_read_task_struct_data()


@skip_if_no_nornir
def test_file_read_task_struct_data_last2():
    clean_up_folder()

    iol1_res = [
{"ip": "1.2.3.4", "interface": "Gi123"},
{"ip": "2.2.2.2", "interface": "Gi2"},
{"ip": "3.3.3.3", "interface": "Gi3"},
    ]
    iol2_res = [
{"ip": "4.4.4.4", "interface": "Gi2"},
    ]
    iol1_res_1 = [
{"ip": "1.2.3.4", "interface": "Gi123"},
{"ip": "3.3.3.3", "interface": "Gi3"},
    ]
    iol2_res_1 = [
{"ip": "4.4.4.4", "interface": "Gi2"},
{"ip": "2.2.2.2", "interface": "Gi2"},
    ]

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )

    # first task run
    nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res,
            "IOL2": iol2_res,
        },
        name="show run | inc ntp",
    )
    # second, most current/latest run - swap IOL1/2 results
    nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_1,
            "IOL2": iol2_res_1,
        },
        name="show run | inc ntp",
    )

    # retrieve file content
    res1 = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
        last=1,
    )
    res2 = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
        last=2,
    )

    res_last_1 = ResultSerializer(res1, add_details=True)
    res_last_2 = ResultSerializer(res2, add_details=True)

    pprint.pprint(res_last_1)
    pprint.pprint(res_last_2)
    _ = res_last_1["IOL1"]['show run | inc ntp'].pop("timestamp")
    _ = res_last_1["IOL2"]['show run | inc ntp'].pop("timestamp")
    _ = res_last_2["IOL1"]['show run | inc ntp'].pop("timestamp")
    _ = res_last_2["IOL2"]['show run | inc ntp'].pop("timestamp")
    assert res_last_1 == {'IOL1': {'show run | inc ntp': {'changed': False,
                                                    'diff': '',
                                                    'exception': None,
                                                    'failed': False,
                                                    'filegroup': 'config_for_read',
                                                    'result': [{'interface': 'Gi123',
                                                                'ip': '1.2.3.4'},
                                                               {'interface': 'Gi3',
                                                                'ip': '3.3.3.3'}]}},
                    'IOL2': {'show run | inc ntp': {'changed': False,
                                                    'diff': '',
                                                    'exception': None,
                                                    'failed': False,
                                                    'filegroup': 'config_for_read',
                                                    'result': [{'interface': 'Gi2',
                                                                'ip': '4.4.4.4'},
                                                               {'interface': 'Gi2',
                                                                'ip': '2.2.2.2'}]}}}
    assert res_last_2 == {'IOL1': {'show run | inc ntp': {'changed': False,
                                                    'diff': '',
                                                    'exception': None,
                                                    'failed': False,
                                                    'filegroup': 'config_for_read',
                                                    'result': [{'interface': 'Gi123',
                                                                'ip': '1.2.3.4'},
                                                               {'interface': 'Gi2',
                                                                'ip': '2.2.2.2'},
                                                               {'interface': 'Gi3',
                                                                'ip': '3.3.3.3'}]}},
                    'IOL2': {'show run | inc ntp': {'changed': False,
                                                    'diff': '',
                                                    'exception': None,
                                                    'failed': False,
                                                    'filegroup': 'config_for_read',
                                                    'result': [{'interface': 'Gi2',
                                                                'ip': '4.4.4.4'}]}}}

# test_file_read_task_struct_data_last2()


@skip_if_no_nornir
def test_file_read_task_struct_data_result_with_subtasks():
    clean_up_folder()

    iol1_res_ntp = [
{"ntp": "1.1.1.1"},
    ]
    iol2_res_ntp = [
{"ntp": "2.2.2.2"},
    ]
    iol1_res_log = [
{"log": "3.3.3.3"},
    ]
    iol2_res_log = [
{"log": "4.4.4.4"},
    ]

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )

    # first task run
    nr_with_tf.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_ntp,
                "IOL2": iol2_res_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_log,
                "IOL2": iol2_res_log,
            },
            "name": "show run | inc logging",
        },
    )

    # retrieve file content
    res = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
    )

    res = ResultSerializer(res, add_details=True)

    # pprint.pprint(res)
    _ = res["IOL1"]['show run | inc ntp'].pop("timestamp")
    _ = res["IOL2"]['show run | inc ntp'].pop("timestamp")
    _ = res["IOL1"]['show run | inc logging'].pop("timestamp")
    _ = res["IOL2"]['show run | inc logging'].pop("timestamp")
    assert res == {'IOL1': {'show run | inc logging': {'changed': False,
                                                       'diff': '',
                                                       'exception': None,
                                                       'failed': False,
                                                       'filegroup': 'config_for_read',
                                                       'result': [{'log': '3.3.3.3'}]},
                            'show run | inc ntp': {'changed': False,
                                                   'diff': '',
                                                   'exception': None,
                                                   'failed': False,
                                                   'filegroup': 'config_for_read',
                                                   'result': [{'ntp': '1.1.1.1'}]}},
                   'IOL2': {'show run | inc logging': {'changed': False,
                                                       'diff': '',
                                                       'exception': None,
                                                       'failed': False,
                                                       'filegroup': 'config_for_read',
                                                       'result': [{'log': '4.4.4.4'}]},
                            'show run | inc ntp': {'changed': False,
                                                   'diff': '',
                                                   'exception': None,
                                                   'failed': False,
                                                   'filegroup': 'config_for_read',
                                                   'result': [{'ntp': '2.2.2.2'}]}}}

# test_file_read_task_struct_data_result_with_subtasks()


@skip_if_no_nornir
def test_file_read_result_struct_data_with_subtasks_task_name():
    """ Should return task results for one task only """
    clean_up_folder()

    iol1_res_ntp = [
{"ntp": "1.1.1.1"},
    ]
    iol2_res_ntp = [
{"ntp": "2.2.2.2"},
    ]
    iol1_res_log = [
{"log": "3.3.3.3"},
    ]
    iol2_res_log = [
{"log": "4.4.4.4"},
    ]

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )

    # first task run
    nr_with_tf.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_ntp,
                "IOL2": iol2_res_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_log,
                "IOL2": iol2_res_log,
            },
            "name": "show run | inc logging",
        },
    )

    # retrieve file content
    res = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
        task_name="show run | inc logging"
    )

    res = ResultSerializer(res, add_details=True)

    # pprint.pprint(res)
    _ = res["IOL1"]['show run | inc logging'].pop("timestamp")
    _ = res["IOL2"]['show run | inc logging'].pop("timestamp")
    assert res == {'IOL1': {'show run | inc logging': {'changed': False,
                                                       'diff': '',
                                                       'exception': None,
                                                       'failed': False,
                                                       'filegroup': 'config_for_read',
                                                       'result': [{'log': '3.3.3.3'}]}},
                   'IOL2': {'show run | inc logging': {'changed': False,
                                                       'diff': '',
                                                       'exception': None,
                                                       'failed': False,
                                                       'filegroup': 'config_for_read',
                                                       'result': [{'log': '4.4.4.4'}]}}}

# test_file_read_result_struct_data_with_subtasks_task_name()


@skip_if_no_nornir
def test_file_read_struct_data_with_DataProcessor_lod_filter():
    """ test tofile write and after that read passing via lod filter """
    clean_up_folder()

    iol1_res = [
{"ip": "1.2.3.4", "interface": "Gi123"},
{"ip": "1.2.2.2", "interface": "Gi2"},
{"ip": "1.3.3.3", "interface": "Gi3"},
    ]
    iol2_res = [
{"ip": "1.2.4.4", "interface": "Gi2"},
    ]

    # run task to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res,
            "IOL2": iol2_res,
        },
        name="show run | inc ntp",
    )

    # retrieve file content passing it through data processor
    nr_with_dp = nr.with_processors([DataProcessor(
        [{"fun": "lod_filter", "ip": "1.2.*", "interface": "Gi[23]"}]
    )])

    res = nr_with_dp.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
    )

    res = ResultSerializer(res, add_details=True)

    # pprint.pprint(res)
    _ = res["IOL1"]['show run | inc ntp'].pop("timestamp")
    _ = res["IOL2"]['show run | inc ntp'].pop("timestamp")
    assert res == {'IOL1': {'show run | inc ntp': {'changed': False,
                                                   'diff': '',
                                                   'exception': None,
                                                   'failed': False,
                                                   'filegroup': 'config_for_read',
                                                   'result': [{'interface': 'Gi2',
                                                               'ip': '1.2.2.2'}]}},
                   'IOL2': {'show run | inc ntp': {'changed': False,
                                                   'diff': '',
                                                   'exception': None,
                                                   'failed': False,
                                                   'filegroup': 'config_for_read',
                                                   'result': [{'interface': 'Gi2',
                                                               'ip': '1.2.4.4'}]}}}
# test_file_read_struct_data_with_DataProcessor_lod_filter()

@skip_if_no_nornir
def test_file_list_get_all_files():
    """ produces list of files """
    clean_up_folder()

    generate_files(tf="interfaces")
    generate_files(tf="interfaces")
    generate_files(tf="ip")
    generate_files(tf="interfaces")

    # retrieve file content
    res = nr.run(
        task=file_list,
        base_url="./tofile_outputs/",
    )

    res = ResultSerializer(res, add_details=True)

    # pprint.pprint(res)

    assert isinstance(res["IOL1"]["file_list"]["result"], list)
    assert len(res["IOL1"]["file_list"]["result"]) == 4
    assert res["IOL1"]["file_list"]["exception"] == None
    assert isinstance(res["IOL2"]["file_list"]["result"], list)
    assert len(res["IOL2"]["file_list"]["result"]) == 4
    assert res["IOL2"]["file_list"]["exception"] == None

# test_file_list_get_all_files()


@skip_if_no_nornir
def test_file_list_get_one_filegroup():
    """ produces list of files """
    clean_up_folder()

    generate_files(tf="interfaces")
    generate_files(tf="interfaces")
    generate_files(tf="ip")
    generate_files(tf="interfaces")

    # retrieve files list
    res = nr.run(
        task=file_list,
        base_url="./tofile_outputs/",
        filegroup="ip"
    )

    res = ResultSerializer(res, add_details=True)

    # pprint.pprint(res)

    assert isinstance(res["IOL1"]["file_list"]["result"], list)
    assert len(res["IOL1"]["file_list"]["result"]) == 1
    assert res["IOL1"]["file_list"]["result"][0]["filegroup"] == "ip"
    assert res["IOL1"]["file_list"]["exception"] == None
    assert isinstance(res["IOL2"]["file_list"]["result"], list)
    assert len(res["IOL2"]["file_list"]["result"]) == 1
    assert res["IOL2"]["file_list"]["result"][0]["filegroup"] == "ip"
    assert res["IOL2"]["file_list"]["exception"] == None

# test_file_list_get_one_filegroup()

@skip_if_no_nornir
def test_file_remove_all():
    clean_up_folder()

    generate_files(tf="interfaces")
    generate_files(tf="interfaces")
    generate_files(tf="ip")
    generate_files(tf="interfaces")

    # check if folder is not empty
    if os.path.exists("./tofile_outputs/"):
        assert len(list(os.listdir("./tofile_outputs/"))) == 9, "not all files saved"

    # run task to delete all data files
    # retrieve files list
    res = nr.run(
        task=file_remove,
        base_url="./tofile_outputs/",
        filegroup=True,
    )
    res = ResultSerializer(res, add_details=True)

    # check if folder is cleaned
    if os.path.exists("./tofile_outputs/"):
        assert len(list(os.listdir("./tofile_outputs/"))) == 1, "not all files removed"

    # pprint.pprint(res)
    assert len(res["IOL1"]["file_remove"]["result"]) == 4
    assert len(res["IOL2"]["file_remove"]["result"]) == 4

    # retrieve files list
    files_list = nr.run(
        task=file_list,
        base_url="./tofile_outputs/",
        filegroup="ip"
    )
    files_list = ResultSerializer(files_list, add_details=True)
    # pprint.pprint(files_list)
    assert len(files_list["IOL1"]["file_list"]["result"]) == 0
    assert len(files_list["IOL2"]["file_list"]["result"]) == 0

    # try to generate more files to check if it will not fail
    generate_files(tf="interfaces")

# test_file_remove_all()

@skip_if_no_nornir
def test_file_remove_filegroup():
    clean_up_folder()

    generate_files(tf="interfaces")
    generate_files(tf="interfaces")
    generate_files(tf="ip")
    generate_files(tf="interfaces")

    # check if folder is not empty
    if os.path.exists("./tofile_outputs/"):
        assert len(list(os.listdir("./tofile_outputs/"))) == 9, "not all files saved"

    # run task to delete all data files
    # retrieve files list
    res = nr.run(
        task=file_remove,
        base_url="./tofile_outputs/",
        filegroup="interfaces"
    )
    res = ResultSerializer(res, add_details=True)

    # check if folder is cleaned
    if os.path.exists("./tofile_outputs/"):
        assert len(list(os.listdir("./tofile_outputs/"))) == 3, "Too many files removed"

    # pprint.pprint(res)
    assert len(res["IOL1"]["file_remove"]["result"]) == 3
    assert len(res["IOL2"]["file_remove"]["result"]) == 3

    # check index file was updated accordingly
    index_file = "./tofile_outputs/tf_index_common.json"
    with open(index_file, "r") as f:
        index_data = json.loads(f.read())

    assert index_data["interfaces"] == {}, "interfaces files data not removed from index"
    assert len(index_data["ip"]) == 2, "ip files data removed from index"

# test_file_remove_filegroup()




@skip_if_no_nornir
def test_file_diff_whole_result_last_1_2():
    clean_up_folder()

    # generate text files
    iol1_res_old = """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol1_res_new = """
ntp server 7.7.6.8
ntp server 7.7.7.7
ntp server 1.1.1.1
        """
    iol2_res_old = """
ntp server 7.7.7.7
        """
    iol2_res_new = """
ntp server 7.7.7.9
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="ntp_config", base_url="./tofile_outputs/")]
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_old,
            "IOL2": iol2_res_old,
        },
        name="show run | inc ntp",
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_new,
            "IOL2": iol2_res_new,
        },
        name="show run | inc ntp",
    )

    # run task to diff
    output = nr.run(
        task=file_diff,
        base_url="./tofile_outputs/",
        filegroup="ntp_config",
    )
    res = ResultSerializer(output, add_details=True)

    # pprint.pprint(res, width=150)
    # print(res["IOL1"]["ntp_config"]["result"])
    # print(res["IOL2"]["ntp_config"]["result"])

    assert """-ntp server 7.7.7.8
+ntp server 7.7.6.8
 ntp server 7.7.7.7
+ntp server 1.1.1.1""" in res["IOL1"]["ntp_config"]["result"]
    assert res["IOL1"]["ntp_config"]["result"].count("ntp_config") == 2

    assert """-ntp server 7.7.7.7
+ntp server 7.7.7.9""" in res["IOL2"]["ntp_config"]["result"]
    assert res["IOL2"]["ntp_config"]["result"].count("ntp_config") == 2

# test_file_diff_whole_result()


@skip_if_no_nornir
def test_file_diff_whole_result_last_2_1():
    clean_up_folder()

    # generate text files
    iol1_res_old = """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol1_res_new = """
ntp server 7.7.6.8
ntp server 7.7.7.7
ntp server 1.1.1.1
        """
    iol2_res_old = """
ntp server 7.7.7.7
        """
    iol2_res_new = """
ntp server 7.7.7.9
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="ntp_config", base_url="./tofile_outputs/")]
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_old,
            "IOL2": iol2_res_old,
        },
        name="show run | inc ntp",
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_new,
            "IOL2": iol2_res_new,
        },
        name="show run | inc ntp",
    )

    # run task to diff
    output = nr.run(
        task=file_diff,
        base_url="./tofile_outputs/",
        filegroup="ntp_config",
        last=[2,1]
    )
    res = ResultSerializer(output, add_details=True)

    # pprint.pprint(res, width=150)
    # print(res["IOL1"]["ntp_config"]["result"])
    # print(res["IOL2"]["ntp_config"]["result"])

    assert """-ntp server 7.7.6.8
+ntp server 7.7.7.8
 ntp server 7.7.7.7
-ntp server 1.1.1.1""" in res["IOL1"]["ntp_config"]["result"]
    assert res["IOL1"]["ntp_config"]["result"].count("ntp_config") == 2

    assert """-ntp server 7.7.7.9
+ntp server 7.7.7.7""" in res["IOL2"]["ntp_config"]["result"]
    assert res["IOL2"]["ntp_config"]["result"].count("ntp_config") == 2

# test_file_diff_whole_result_last_2_1()


@skip_if_no_nornir
def test_file_diff_whole_result_last_out_of_range():
    clean_up_folder()

    # generate text files
    iol1_res_old = """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol1_res_new = """
ntp server 7.7.6.8
ntp server 7.7.7.7
ntp server 1.1.1.1
        """
    iol2_res_old = """
ntp server 7.7.7.7
        """
    iol2_res_new = """
ntp server 7.7.7.9
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="ntp_config", base_url="./tofile_outputs/")]
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_old,
            "IOL2": iol2_res_old,
        },
        name="show run | inc ntp",
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_new,
            "IOL2": iol2_res_new,
        },
        name="show run | inc ntp",
    )

    # run task to diff
    output = nr.run(
        task=file_diff,
        base_url="./tofile_outputs/",
        filegroup="ntp_config",
        last=151
    )
    res = ResultSerializer(output, add_details=True)

    # pprint.pprint(res, width=150)
    print(res["IOL1"]["ntp_config"]["result"])
    print(res["IOL2"]["ntp_config"]["result"])

    assert """-ntp server 7.7.7.8
+ntp server 7.7.6.8
 ntp server 7.7.7.7
+ntp server 1.1.1.1""" in res["IOL1"]["ntp_config"]["result"]
    assert res["IOL1"]["ntp_config"]["result"].count("ntp_config") == 2

    assert """-ntp server 7.7.7.7
+ntp server 7.7.7.9""" in res["IOL2"]["ntp_config"]["result"]
    assert res["IOL2"]["ntp_config"]["result"].count("ntp_config") == 2

# test_file_diff_whole_result_last_out_of_range()


@skip_if_no_nornir
def test_file_diff_whole_result_last_both_out_of_range():
    clean_up_folder()

    # generate text files
    iol1_res_old = """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol1_res_new = """
ntp server 7.7.6.8
ntp server 7.7.7.7
ntp server 1.1.1.1
        """
    iol2_res_old = """
ntp server 7.7.7.7
        """
    iol2_res_new = """
ntp server 7.7.7.9
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="ntp_config", base_url="./tofile_outputs/")]
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_old,
            "IOL2": iol2_res_old,
        },
        name="show run | inc ntp",
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_new,
            "IOL2": iol2_res_new,
        },
        name="show run | inc ntp",
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_new,
            "IOL2": iol2_res_new,
        },
        name="show run | inc ntp",
    )

    # run task to diff
    output = nr.run(
        task=file_diff,
        base_url="./tofile_outputs/",
        filegroup="ntp_config",
        last=[100,151]
    )
    res = ResultSerializer(output, add_details=True)

    # pprint.pprint(res, width=150)

    assert res["IOL1"]["ntp_config"]["failed"] == True
    assert "new and old files are same" in res["IOL1"]["ntp_config"]["exception"]
    assert res["IOL2"]["ntp_config"]["failed"] == True
    assert "new and old files are same" in res["IOL2"]["ntp_config"]["exception"]

# test_file_diff_whole_result_last_both_out_of_range()


@skip_if_no_nornir
def test_file_diff_whole_result_last_2_1_string():
    clean_up_folder()

    # generate text files
    iol1_res_old = """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol1_res_new = """
ntp server 7.7.6.8
ntp server 7.7.7.7
ntp server 1.1.1.1
        """
    iol2_res_old = """
ntp server 7.7.7.7
        """
    iol2_res_new = """
ntp server 7.7.7.9
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="ntp_config", base_url="./tofile_outputs/")]
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_old,
            "IOL2": iol2_res_old,
        },
        name="show run | inc ntp",
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_new,
            "IOL2": iol2_res_new,
        },
        name="show run | inc ntp",
    )

    # run task to diff
    output = nr.run(
        task=file_diff,
        base_url="./tofile_outputs/",
        filegroup="ntp_config",
        last="2, 1"
    )
    res = ResultSerializer(output, add_details=True)

    # pprint.pprint(res, width=150)
    # print(res["IOL1"]["ntp_config"]["result"])
    # print(res["IOL2"]["ntp_config"]["result"])

    assert """-ntp server 7.7.6.8
+ntp server 7.7.7.8
 ntp server 7.7.7.7
-ntp server 1.1.1.1""" in res["IOL1"]["ntp_config"]["result"]
    assert res["IOL1"]["ntp_config"]["result"].count("ntp_config") == 2

    assert """-ntp server 7.7.7.9
+ntp server 7.7.7.7""" in res["IOL2"]["ntp_config"]["result"]
    assert res["IOL2"]["ntp_config"]["result"].count("ntp_config") == 2

# test_file_diff_whole_result_last_2_1_string()
