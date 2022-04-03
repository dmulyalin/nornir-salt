"""
salt_cfg_gen
############

This is a function to test configuration generation without applying
it to devices. It goes through full configuration rendering and helps
to verify configuration content or simply generate it.

Used in conjunction with ``nr.cfg_gen`` execution module function.

salt_cfg_gen reference
======================

.. autofunction:: nornir_salt.plugins.tasks.salt_cfg_gen.salt_cfg_gen
"""
from nornir.core.task import Result
from nornir_salt.utils import cfg_form_commands
from nornir_salt.utils.pydantic_models import model_salt_cfg_gen
from nornir_salt.utils.yangdantic import ValidateFuncArgs


@ValidateFuncArgs(model_salt_cfg_gen)
def salt_cfg_gen(task, config=None, **kwargs):
    """
    Task function for ``nr.cfg_gen`` function to return template rendered
    with pillar and Nornir host's Inventory data.

    In essence, this function echoes back content of ``config`` argument.

    :param config: (str) configuration string to return
    :param kwargs: (dict) ignored
    :return result: Nornir result object with task execution results
    """
    task.name = "salt_cfg_gen"

    config = cfg_form_commands(task=task, config=config, multiline=True)

    return Result(host=task.host, result=config)
