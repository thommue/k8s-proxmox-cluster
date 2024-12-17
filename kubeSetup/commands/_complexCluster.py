import click
from typing import cast
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
    ClusterType,
    VmType,
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
    callback=parse_complex_vm_config_file,
    help="Path to the configuration file for the vm setup for the kubernetes cluster.",
)
@click.option(
    "--kube-version",
    required=False,
    type=click.STRING,
    default="1.30",
    help="Kubernetes version, which will be used for the cluster setup.",
)
def complex_cluster_setup(
    proxmox_config: ProxmoxConnection,
    vm_config: list[ComplexVmConf],
    kube_version: str = "1.30",
) -> None:
    """
    Command, which sets up a complex HA kubernetes cluster, which can be seen in the image below.
    With the config, you can set the number of workers, cpu, ram and storage specs and the ip addresses.
    Also, you need here dedicated vms, which handles the control plane in HA mode.
    """
    # setup logger
    logger = setup_logger(name="ComplexClusterSetup")

    # setup SSH connection pool manager
    ssh_pool_manager = SSHConnectionPool()

    proxmox = ProxmoxCommands(proxmox_conf=proxmox_config, logger=logger)
    proxmox.clone_vm(vm_infos=vm_haconfig)  # type: ignore
    proxmox.make_required_restarts(vm_infos=vm_haconfig)  # type: ignore

    # set up keepalived and haproxy for HA
    keepalived = KeepaLivedSetup(vm_infos=vm_config, logger=logger)
    ssh_pool_manager = keepalived.configure_keepalived(
        ssh_pool_manager=ssh_pool_manager
    )

    haproxy = HAProxySetup(vm_infos=vm_config, logger=logger)
    ssh_pool_manager = haproxy.configure_haproxy(ssh_pool_manager=ssh_pool_manager)

    # close connections to load balancer
    ssh_pool_manager.close_connections(
        ip_addresses=[
            vm.ip_address for vm in vm_config if vm.vm_type == VmType.LOADBALANCER
        ]
    )

    # preconfigure the cluster
    preconf = PreconfigureCluster(
        vm_infos=vm_haconfig, logger=logger, kube_version=kube_version  # type: ignore
    )
    grouped_vms, ssh_pool_manager = preconf.preconfigure_vms(
        ssh_pool_manager=ssh_pool_manager
    )

    # set up the cluster in HA Mode with stacked ectd
    ClusterSetup.setup_cluster(
        group_vms=grouped_vms,
        cluster_type=ClusterType.COMPLEX,
        control_plane_endpoint=grouped_vms[VmType.LOADBALANCER.value][  # type: ignore
            0
        ].virtual_ip_address,
        logger=logger,
        ssh_pool_manager=ssh_pool_manager,
    )

    # close all connections
    ssh_pool_manager.close_all_connections()


if __name__ == "__main__":
    complex_cluster_setup()
