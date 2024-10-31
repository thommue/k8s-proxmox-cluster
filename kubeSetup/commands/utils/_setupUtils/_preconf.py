import logging
import paramiko
from itertools import groupby
from .._setup import SimpleVmConf, ComplexVmConf
from .._setupUtils import update_upgrade_cmd, execute_command, setup_client
from .._setupUtils import conf_sysctl, turnoff_swap, install_containerd, configure_containerd, install_kube_pkgs


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Preconfig KubeSetup Logger")


class PreconfigureCluster:

    def __init__(self, vm_infos: list[SimpleVmConf | ComplexVmConf]) -> None:
        self.vm_infos = vm_infos

    def preconfigure_vms(self) -> dict[str, list[SimpleVmConf | ComplexVmConf]]:

        client = setup_client()

        for vm in self.vm_infos:
            private_key = paramiko.RSAKey.from_private_key_file(vm.ssh_key)
            client.connect(vm.ip_address, 22, vm.user, pkey=private_key)

            # update and upgrade the vm
            update_upgrade_cmd(client=client, upgrade=True, logger=logger)

            # install nfs, so it's available for later use
            execute_command(
                cmd="sudo apt-get install nfs-common",
                client=client,
                logger=logger,
            )

            # config sysctl
            conf_sysctl(client=client, logger=logger)

            # turn off swap
            turnoff_swap(client=client, logger=logger)

            # update
            update_upgrade_cmd(client=client, upgrade=False, logger=logger)

            # install containerd
            install_containerd(client=client, logger=logger)

            # configure containerd
            configure_containerd(client=client, logger=logger)

            # install kubernetes packages
            install_kube_pkgs(client=client, logger=logger)

            # return the grouped vms
            return self._group_vms()

    def _group_vms(self) -> dict[str, list[SimpleVmConf | ComplexVmConf]]:
        return {
            vm_type: list(grouped_vm)
            for vm_type, grouped_vm in groupby(
                sorted(self.vm_infos, key=lambda v: v.vm_type.name),
                key=lambda v: v.vm_type.name
            )
        }
