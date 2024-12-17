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
                tags=conf["tags"],
                clone_type=conf["clone_type"],
                ip_address=conf["ip_address"],
                ip_gw=conf["ip_gw"],
                cores=conf["cores"] if "cores" in conf.keys() else None,
                memory=conf["memory"] if "memory" in conf.keys() else None,
                disk_size=conf["disk_size"] if "disk_size" in conf.keys() else None,
                user=conf["user"],
                ssh_key=conf["ssh_key"],
                pw=conf["pw"],
            )
        else:
            configuration = ComplexVmConf(
                vm_name=conf["vm_name"],
                vm_type=VmType(conf["vm_type"].upper()),
                target_name=conf["target_name"],
                vm_id=conf["vm_id"],
                tags=conf["tags"],
                clone_type=conf["clone_type"],
                ip_address=conf["ip_address"],
                ip_gw=conf["ip_gw"],
                cores=conf["cores"] if "cores" in conf.keys() else None,
                memory=conf["memory"] if "memory" in conf.keys() else None,
                disk_size=conf["disk_size"] if "disk_size" in conf.keys() else None,
                user=conf["user"],
                ssh_key=conf["ssh_key"],
                pw=conf["pw"],
                virtual_ip_address=(
                    conf["virtual_ip_address"]
                    if VmType(conf["vm_type"].upper()) == VmType.LOADBALANCER
                    else None
                ),
                node_state=(
                    NodeType(conf["node_state"].upper())
                    if "node_state" in conf.keys()
                    and (
                        NodeType(conf["node_state"].upper()) == NodeType.MASTER
                        or NodeType(conf["node_state"].upper()) == NodeType.BACKUP
                    )
                    else None
                ),
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
        if (
            isinstance(configuration, ComplexVmConf)
            and configuration.vm_type == VmType.LOADBALANCER
            and configuration.virtual_ip_address is None
        ):
            raise click.BadParameter(
                "For a complex cluster the virtual IP address must be specified!"
            )
        if (
            isinstance(configuration, ComplexVmConf)
            and configuration.vm_type == VmType.LOADBALANCER
            and configuration.node_state is None
        ):
            raise click.BadParameter(
                "For a complex cluster the node state must be specified, either MASTER or BACKUP!"
            )
        return configuration
    except KeyError as err:
        raise click.UsageError(
            "Please provide a valid configuration file."
            "The requirements can be found in the documentation and on the example of the corresponding "
            "github page"
        )
