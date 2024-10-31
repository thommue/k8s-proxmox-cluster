import click
from .utils import (
    parse_proxmox_config_file,
    parse_simple_vm_config_file,
    SimpleVmConf,
    ProxmoxCommands,
    SimpleKubernetesClusterSetup,
    PreconfigureCluster,
    ProxmoxConnection,
    ClusterSetup,
    ClusterType
)


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
    callback=parse_simple_vm_config_file,
    help="Path to the configuration file for the vm setup for the kubernetes cluster.",
)
def simple_cluster_setup(
    proxmox_config: ProxmoxConnection,
    vm_config: list[SimpleVmConf],
) -> None:
    """
    Command, which sets up a simple kubernetes cluster, which can be seen in the image below.
    With the config, you can set the number of workers, cpu, ram and storage specs and the ip addresses.
    """
    click.echo(f"The config proxmox file {proxmox_config}")
    click.echo(f"The config vm file {vm_config}")

    # all proxmox calls for cloning from a template
    proxmox = ProxmoxCommands(proxmox_conf=proxmox_config)
    proxmox.clone_vm(vm_infos=vm_config)
    proxmox.make_required_restarts(vm_infos=vm_config)

    # preconfigure the cluster
    preconf = PreconfigureCluster(vm_infos=vm_config)
    grouped_vms = preconf.preconfigure_vms()

    # set up the simple cluster
    ClusterSetup.setup_cluster(group_vms=grouped_vms, cluster_type=ClusterType.SIMPLE)

    # cluster_setup = SimpleKubernetesClusterSetup(vm_infos=vm_config)
    # cluster_setup.setup_cluster(group_vms=grouped_vms)


if __name__ == "__main__":
    simple_cluster_setup()
