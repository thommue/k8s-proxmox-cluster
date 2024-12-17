import json
import click
from typing import Any
from ._schemas import SimpleVmConf
from ._utils import _converter


def parse_simple_vm_config_file(
    _: Any, param: click.Parameter, value: str
) -> list[SimpleVmConf]:
    if value.endswith(".json"):
        with open(value, "r") as file:
            conf_dict = json.load(file)
            if len(conf_dict) > 1:
                result: list[SimpleVmConf] = [
                    _converter(conf, simple=True) for conf in conf_dict
                ]
                return result
            else:
                raise click.BadParameter(
                    "There must be at least two vm be defined in the JSON file."
                )
    else:
        raise click.BadParameter("File must be a JSON file", param=param)
