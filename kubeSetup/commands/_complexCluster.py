import click
from .utils import (
    parse_proxmox_config_file,
    parse_complex_vm_config_file,
    ComplexVmConf,
    ProxmoxCommands,
    KeepaLivedSetup,
    HAProxySetup,
    ProxmoxConnection,
    PreconfigureCluster,
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
    "--vm-haconfig",
    required=True,
    type=click.Path(exists=True),
    callback=parse_complex_vm_config_file,
    help="Path to the configuration file for the vm setup for the kubernetes cluster.",
)
def complex_cluster_setup(
        proxmox_config: ProxmoxConnection,
        vm_haconfig: list[ComplexVmConf],
) -> None:
    """
    Command, which sets up a complex HA kubernetes cluster, which can be seen in the image below.
    With the config, you can set the number of workers, cpu, ram and storage specs and the ip addresses.
    Also you need here dedicated vms, which handles the control plane in HA mode.
    """
    click.echo(f"The config proxmox file {proxmox_config}")
    click.echo(f"The config vm file {vm_haconfig}")

    # proxmox = ProxmoxCommands(proxmox_conf=proxmox_config)
    # proxmox.clone_vm(vm_infos=vm_haconfig)
    # proxmox.make_required_restarts(vm_infos=vm_haconfig)

    # set up keepalived and haproxy for HA
    keepalived = KeepaLivedSetup(vm_infos=vm_haconfig)
    keepalived.configure_keepalived()

    haproxy = HAProxySetup(vm_infos=vm_haconfig)
    haproxy.configure_haproxy()

    # preconfigure the cluster
    preconf = PreconfigureCluster(vm_infos=vm_haconfig)
    grouped_vms = preconf.preconfigure_vms()

    # set up the cluster in HA Mode with stacked ectd




if __name__ == "__main__":
    complex_cluster_setup()

