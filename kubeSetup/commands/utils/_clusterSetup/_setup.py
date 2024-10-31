import os
import logging
import paramiko
from time import sleep
from ._schemas import ClusterType
from paramiko.client import SSHClient
from jinja2 import Environment, FileSystemLoader
from .._setup import SimpleVmConf, ComplexVmConf, VmType
from .._setupUtils import setup_client, get_pwd, kubeadm_init, setup_calico


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KubeSetup Logger")


class ClusterSetup:

    @classmethod
    def setup_cluster(cls, group_vms: dict[str, list[SimpleVmConf | ComplexVmConf]], cluster_type: ClusterType):
        # configure ssh connection to main master vm
        client = setup_client(group_vms=group_vms)

        # get the root directory from the vm, just to move the files there
        pwd = get_pwd(client=client, logger=logger)

        # establish sftp
        sftp = client.open_sftp()

        # get the right templates
        if cluster_type == ClusterType.SIMPLE:
            temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "simple")

            # setup kubeadm simple
            with sftp.open(f"{pwd}/kubeadm-config.yaml", "w") as remote_file:
                remote_file.write(
                    cls.setup_kubeadm_conf(
                        ip_address=group_vms[VmType.MASTER.name][0].ip_address,
                        pod_subnet="10.244.0.0",
                        service_subnet="10.96.0.0",
                        temp_path=temp_path
                    )
                )

        else:
            temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "complex")

            # setup kubeadm complex
            with sftp.open(f"{pwd}/kubeadm-config.yaml", "w") as remote_file:
                remote_file.write(
                    cls.setup_kubeadm_conf(
                        ip_address=group_vms[VmType.MASTER.name][0].ip_address,
                        pod_subnet="10.244.0.0",
                        service_subnet="10.96.0.0",
                        control_plane_endpoint="",
                        temp_path=temp_path
                    )
                )

        # setup calico
        with sftp.open(f"{pwd}/calico.yaml", "w") as remote_file:
            remote_file.write(
                cls.setup_calico(
                    pod_subnet="10.244.0.0",
                    temp_path=temp_path
                )
            )

        # close sftp connection
        sftp.close()

        # init kubeadm and setup kube home
        kubeadm_cmd = kubeadm_init(client=client, logger=logger)

        # init calico (cni)
        setup_calico(client=client, logger=logger)

        # join the worker nodes
        cls._join_worker_nodes(vm_infos_grouped=group_vms, client=client, kubeadm_cmd=kubeadm_cmd)

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

    @staticmethod
    def _join_worker_nodes(vm_infos_grouped: dict[str, list[SimpleVmConf]], kubeadm_cmd: str, client: SSHClient) -> None:

        for worker in vm_infos_grouped[VmType.WORKER.name]:

            private_key = paramiko.RSAKey.from_private_key_file(worker.ssh_key)
            client.connect(worker.ip_address, 22, worker.user, pkey=private_key)

            stdin, stdout, stderr = client.exec_command(kubeadm_cmd)
            logger.info(f"Connect Worker {worker.ip_address}: {stdout.read().decode()} | {stderr.read().decode()}")
            sleep(20)
