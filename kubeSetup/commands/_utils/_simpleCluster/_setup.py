import os
import logging
import paramiko
from time import sleep
from itertools import groupby
from paramiko.client import SSHClient
from jinja2 import Environment, FileSystemLoader
from kubeSetup.commands._utils import VmConf, VmType
from ._setup_utils import update_upgrade_cmd, conf_sysctl, turnoff_swap, install_containerd, configure_containerd, install_kube_pkgs, setup_calico, kubeadm_init


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KubeSetup Logger")


class SimpleKubernetesClusterSetup:
    def __init__(self, vm_infos: list[VmConf]) -> None:
        self.vm_infos = vm_infos

    def preconfigure_vms(self) -> dict[str, list[VmConf]]:

        client = self.setup_client()

        for vm in self.vm_infos:
            private_key = paramiko.RSAKey.from_private_key_file(vm.ssh_key)
            client.connect(vm.ip_address.split("/")[0], 22, vm.user, pkey=private_key)

            # update and upgrade the vm
            update_upgrade_cmd(client=client, upgrade=True, logger=logger)

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

            # install kubernetese packages
            install_kube_pkgs(client=client, logger=logger)

        # setup kubeadm conf and calico.yaml on master vm
        vm_infos_grouped = {
            vm_type: list(grouped_vm)
            for vm_type, grouped_vm in groupby(
                sorted(self.vm_infos, key=lambda v: v.vm_type.name),
                key=lambda v: v.vm_type.name
            )
        }

        master_vm = vm_infos_grouped[VmType.MASTER.name][0]

        private_key = paramiko.RSAKey.from_private_key_file(master_vm.ssh_key)
        client.connect(master_vm.ip_address.split("/")[0], 22, master_vm.user, pkey=private_key)
        self._kubeadm_calico_setup(client=client, ip_address=master_vm.ip_address.split("/")[0])

        return vm_infos_grouped

    def setup_cluster(self, vm_infos_grouped: dict[str, list[VmConf]]) -> None:

        # init the cluster on master node
        client = self.setup_client()
        private_key = paramiko.RSAKey.from_private_key_file(vm_infos_grouped[VmType.MASTER.name][0].ssh_key)
        client.connect(vm_infos_grouped[VmType.MASTER.name][0].ip_address.split("/")[0], 22,
                       vm_infos_grouped[VmType.MASTER.name][0].user, pkey=private_key)

        # now init kubeadm and setup kube home
        kubeadm_cmd = kubeadm_init(client=client, logger=logger)
        print(kubeadm_cmd)

        # setup calico on master node
        setup_calico(client=client, logger=logger)

        # join other worker nodes
        self._join_worker_nodes(vm_infos_grouped=vm_infos_grouped, kubeadm_cmd=kubeadm_cmd)

    def _kubeadm_calico_setup(self, client: SSHClient, ip_address: str) -> None:
        _, stdout, _ = client.exec_command("pwd")
        pwd = stdout.read().decode().split("\n")[0]

        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_templates")

        sftp = client.open_sftp()

        # Write the rendered content directly to the VM
        with sftp.open(f"{pwd}/kubeadm-config.yaml", "w") as remote_file:
            remote_file.write(
                self.setup_kubeadm_conf(
                    ip_address=ip_address,
                    pod_subnet="10.244.0.0",
                    service_subnet="10.96.0.0",
                    temp_path=temp_path
                )
            )

        with sftp.open(f"/home/tom/calico.yaml", "w") as remote_file:
            remote_file.write(
                self.setup_calico(
                    pod_subnet="10.244.0.0",
                    temp_path=temp_path
                )
            )

        sftp.close()

    def _join_worker_nodes(self, vm_infos_grouped: dict[str, list[VmConf]], kubeadm_cmd: str) -> None:

        client = self.setup_client()

        for worker in vm_infos_grouped[VmType.WORKER.name]:

            private_key = paramiko.RSAKey.from_private_key_file(worker.ssh_key)
            client.connect(worker.ip_address.split("/")[0], 22, worker.user, pkey=private_key)

            stdin, stdout, stderr = client.exec_command(kubeadm_cmd)
            logger.info(f"Connect Worker {worker.ip_address.split("/")[0]}: {stdout.read().decode()} | {stderr.read().decode()}")
            sleep(20)

    @staticmethod
    def setup_client() -> SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    @staticmethod
    def setup_kubeadm_conf(
            ip_address: str, pod_subnet: str, service_subnet: str, temp_path: str
    ) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "kubeadm-config.j2"
        )
        return template.render(
            ip_address=ip_address, pod_subnet=pod_subnet, service_subnet=service_subnet
        )

    @staticmethod
    def setup_calico(pod_subnet: str, temp_path: str) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "calico.j2"
        )
        return template.render(pod_subnet=pod_subnet)
