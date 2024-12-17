import click
from .utils import (
    parse_proxmox_config_file,
    parse_config_file,
    ProxmoxConnection,
    ProxmoxCommands,
    VmConf,
    setup_logger,
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
    callback=parse_config_file,
    help="Path to the configuration file for the cleanup.",
)
def cluster_cleanup(proxmox_config: ProxmoxConnection, vm_config: list[VmConf]) -> None:
    """
    Command, which cleans up the vms from the previous cluster setup. So all vms will be removed
    from the proxmox cluster.
    """
    # setup logger
    logger = setup_logger(name="Cluster - cleanup")

    # setup connection to proxmox and cleanup
    proxmox = ProxmoxCommands(proxmox_conf=proxmox_config, logger=logger)
    proxmox.cleanup_vm(vm_infos=vm_config)


if __name__ == "__main__":
    cluster_cleanup()
