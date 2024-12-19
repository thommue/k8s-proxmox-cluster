import click
from .utils import (
    parse_proxmox_config_file,
    parse_simple_vm_config_file,
    SimpleVmConf,
    ProxmoxCommands,
    PreconfigureCluster,
    ProxmoxConnection,
    ClusterSetup,
    ClusterType,
    setup_logger,
    SSHConnectionPool,
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
@click.option(
    "--kube-version",
    required=False,
    type=click.STRING,
    default="1.30",
    help="Kubernetes version, which will be used for the cluster setup.",
)
def simple_cluster_setup(
    proxmox_config: ProxmoxConnection, vm_config: list[SimpleVmConf], kube_version: str
) -> None:
    """
    Command, which sets up a simple kubernetes cluster, which can be seen in the image below.
    With the config, you can set the number of workers, cpu, ram and storage specs and the ip addresses.
    """
    # setup logger
    logger = setup_logger(name="SimpleClusterSetup")

    # setup SSH connection pool manager
    ssh_pool_manager = SSHConnectionPool()

    # all proxmox calls for cloning from a template
    proxmox = ProxmoxCommands(proxmox_conf=proxmox_config, logger=logger)
    proxmox.clone_vm(vm_infos=vm_config)
    proxmox.make_required_restarts(vm_infos=vm_config)

    # preconfigure the cluster
    preconf = PreconfigureCluster(
        vm_infos=vm_config, logger=logger, kube_version=kube_version
    )
    grouped_vms, ssh_pool_manager = preconf.preconfigure_vms(
        ssh_pool_manager=ssh_pool_manager
    )

    # set up the simple cluster
    ClusterSetup.setup_cluster(
        group_vms=grouped_vms,
        cluster_type=ClusterType.SIMPLE,
        logger=logger,
        ssh_pool_manager=ssh_pool_manager,
    )

    # close all connections
    ssh_pool_manager.close_all_connections()


if __name__ == "__main__":
    simple_cluster_setup()
