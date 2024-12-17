import json
import click
from typing import Any
from ._schemas import VmConf


def _convert(conf: Any) -> VmConf:
    try:
        return VmConf(
            vm_name=conf["vm_name"],
            target_name=conf["target_name"],
            vm_id=conf["vm_id"],
        )
    except KeyError:
        raise click.UsageError(
            "Please provide a valid configuration file."
            "The requirements can be found in the documentation and on the example of the corresponding"
            "github page"
        )


def parse_config_file(_: Any, param: click.Parameter, value: str) -> list[VmConf]:
    if value.endswith(".json"):
        with open(value, "r") as file:
            conf_dict = json.load(file)
            return [_convert(conf=config) for config in conf_dict]
    else:
        raise click.BadParameter("File must be a JSON file", param=param)
