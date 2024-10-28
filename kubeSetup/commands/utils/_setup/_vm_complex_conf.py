import json
import click
from typing import Any
from ._schemas import ComplexVmConf
from ._utils import _converter


def parse_complex_vm_config_file(_: Any, param: click.Parameter, value: str) -> list[ComplexVmConf]:
    if value.endswith(".json"):
        with open(value, "r") as file:
            conf_dict = json.load(file)
            # TODO CHANGE BACK TO 5!
            if len(conf_dict) > 1:
                result: list[ComplexVmConf] = [_converter(conf, simple=False) for conf in conf_dict]
                return result
            else:
                raise click.BadParameter(
                    "There must be at least six vm be defined in the JSON file."
                )
    else:
        raise click.BadParameter("File must be a JSON file", param=param)
