import logging
from itertools import groupby
from ._ssh_connection import SSHConnectionPool
from .._setup import SimpleVmConf, ComplexVmConf, VmType
from ._general_commands import update_upgrade_cmd, execute_command
from ._setup_utils import (
    conf_sysctl,
    turnoff_swap,
    install_containerd,
    configure_containerd,
    install_kube_pkgs,
)


class PreconfigureCluster:

    def __init__(
        self,
        vm_infos: list[SimpleVmConf | ComplexVmConf],
        logger: logging.Logger,
        kube_version: str,
    ) -> None:
        self.vm_infos = vm_infos
        self.logger = logger
        self.kube_version = kube_version

    def preconfigure_vms(
        self, ssh_pool_manager: SSHConnectionPool
    ) -> tuple[dict[str, list[SimpleVmConf | ComplexVmConf]], SSHConnectionPool]:

        for vm in self.vm_infos:

            # check if the vm type is of type load balancer, so preconfigure need to happen
            if isinstance(vm, ComplexVmConf) and vm.vm_type == VmType.LOADBALANCER:
                continue

            self.logger.warning(
                f"\n\nSetup vm {vm.vm_name} with ip: {vm.ip_address}\n\n"
            )

            # set up the connection and hold it, to avoid multiple open anc close issues
            client_connection = ssh_pool_manager.get_connection(
                ip_address=vm.ip_address,
                user=vm.user,
                ssh_key=vm.ssh_key,
            )

            # update and upgrade the vm
            update_upgrade_cmd(
                client=client_connection, upgrade=True, logger=self.logger
            )

            # install nfs, so it's available for later use
            execute_command(
                cmd="sudo apt-get install nfs-common -y",
                client=client_connection,
                logger=self.logger,
            )

            # install sshpass for simple ssh password
            execute_command(
                cmd="sudo apt-get install sshpass -y",
                client=client_connection,
                logger=self.logger,
            )

            # config sysctl
            conf_sysctl(client=client_connection, logger=self.logger)

            # turn off swap
            turnoff_swap(client=client_connection, logger=self.logger)

            # update
            update_upgrade_cmd(
                client=client_connection, upgrade=False, logger=self.logger
            )

            # install containerd
            install_containerd(client=client_connection, logger=self.logger)

            # configure containerd
            configure_containerd(client=client_connection, logger=self.logger)

            # install kubernetes packages
            install_kube_pkgs(
                client=client_connection,
                logger=self.logger,
                kube_version=self.kube_version,
            )

        # return the grouped vms
        return self._group_vms(), ssh_pool_manager

    def _group_vms(self) -> dict[str, list[SimpleVmConf | ComplexVmConf]]:
        return {
            vm_type: list(grouped_vm)
            for vm_type, grouped_vm in groupby(
                sorted(self.vm_infos, key=lambda v: v.vm_type.name),
                key=lambda v: v.vm_type.name,
            )
        }
