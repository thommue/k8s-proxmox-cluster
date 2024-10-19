import click
from ._utils import *


@click.command()
@click.option(
    "--proxmox-config",
    required=True,
    type=click.Path(exists=True),
    callback=parse_proxmox_config_file,
    help="Path to the configuration file for the proxmox cluster.",
)
@click.option(
    "--vm-config",
    required=True,
    type=click.Path(exists=True),
    callback=parse_vm_config_file,
    help="Path to the configuration file for the vm setup for the kubernetes cluster.",
)
def simple_cluster_setup(
    proxmox_config: ProxmoxConnection,
    vm_config: list[VmConf],
) -> None:
    """
    Command, which sets up a simple kubernetes cluster, which can be seen in the image below.
    With the config, you can set the number of workers, cpu, ram and storage specs and the ip addresses.
    """
    click.echo(f"The config proxmox file {proxmox_config}")
    click.echo(f"The config vm file {vm_config}")

    proxmox = ProxmoxCommands(proxmox_conf=proxmox_config)
    proxmox.clone_vm(vm_infos=vm_config)
    proxmox.make_required_restarts(vm_infos=vm_config)

    cluster_setup = SimpleKubernetesClusterSetup(vm_infos=vm_config)
    vm_infos_grouped = cluster_setup.preconfigure_vms()
    cluster_setup.setup_cluster(vm_infos_grouped=vm_infos_grouped)



if __name__ == "__main__":
    simple_cluster_setup()
