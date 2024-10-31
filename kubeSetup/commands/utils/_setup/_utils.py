import click
from typing import Any
from ._schemas import ComplexVmConf, SimpleVmConf, VmType, NodeType


def _converter(conf: Any, simple: bool) -> SimpleVmConf | ComplexVmConf:
    try:
        if simple:
            configuration = SimpleVmConf(
                vm_name=conf["vm_name"],
                vm_type=VmType(conf["vm_type"].upper()),
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
        else:
            configuration = ComplexVmConf(
                vm_name=conf["vm_name"],
                vm_type=VmType(conf["vm_type"].upper()),
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
                virtual_ip_address=conf["virtual_ip_address"] if VmType(conf["vm_type"].upper()) == VmType.LOADBALANCER else None,
                node_state=conf["node_state"] if NodeType(conf["node_state"].upper()) in conf.keys() else None,
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
