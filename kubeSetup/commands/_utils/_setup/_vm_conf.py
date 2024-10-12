import json
import click
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class VmConf:
    vm_name: str
    target_name: str
    vm_id: int
    clone_type: int
    ip_address: str
    ip_gw: str
    cores: Optional[int]
    memory: Optional[int]
    disk_size: Optional[int]
    user: str
    ssh_key: str


def _converter(conf: Any) -> VmConf:
    try:
        configuration = VmConf(
            vm_name=conf["vm_name"],
            target_name=conf["target_name"],
            vm_id=conf["vm_id"],
            clone_type=conf["clone_type"],
            ip_address=conf["ip_address"],
            ip_gw=conf["ip_gw"],
            cores=conf["cores"] if "cores" in conf.keys() else None,
            memory=conf["memory"] if "memory" in conf.keys() else None,
            disk_size=conf["disk_size"] if "disk_size" in conf.keys() else None,
            user=conf["user"],
            ssh_key=conf["ssh_key"],
        )
        if (
            configuration.cores
            and not configuration.memory
            or not configuration.cores
            and configuration.memory
        ):
            raise click.UsageError(
                "If a cpu or memory is specified, you must specify both --cores and --memory in the config file!"
            )
        return configuration
    except KeyError:
        raise click.UsageError(
            "Please provide a valid configuration file."
            "The requirements can be found in the documentation and on the example of the corresponding"
            "github page"
        )


def parse_vm_config_file(_: Any, param: click.Parameter, value: str) -> list[VmConf]:
    if value.endswith(".json"):
        with open(value, "r") as file:
            conf_dict = json.load(file)
            if len(conf_dict) > 1:
                return [_converter(conf) for conf in conf_dict]
            else:
                raise click.BadParameter(
                    "There must be at least two vm be defined in the JSON file."
                )
    else:
        raise click.BadParameter("File must be a JSON file", param=param)
