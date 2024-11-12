import os
import logging
from time import sleep
from typing import Optional
from ._schemas import ClusterType
from jinja2 import Environment, FileSystemLoader
from .._setup import SimpleVmConf, ComplexVmConf, VmType
from .._setupUtils import get_pwd, kubeadm_init, setup_calico, SSHConnectionPool


class ClusterSetup:

    @classmethod
    def setup_cluster(
            cls,
            group_vms: dict[str, list[SimpleVmConf | ComplexVmConf]],
            cluster_type: ClusterType,
            logger: logging.Logger,
            ssh_pool_manager: SSHConnectionPool,
            control_plane_endpoint: Optional[str] = None
    ):
        # get the connection to the master node
        master_vm = group_vms[VmType.MASTER.name][0]
        client_master = ssh_pool_manager.get_connection(
            ip_address=master_vm.ip_address,
            user=master_vm.user,
            ssh_key=master_vm.ssh_key
        )

        # get the root directory from the vm, just to move the files there
        pwd = get_pwd(client=client_master, logger=logger)

        # establish sftp
        sftp = client_master.open_sftp()

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
                        control_plane_endpoint=control_plane_endpoint,
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
        kubeadm_cmd = kubeadm_init(client=client_master, logger=logger)

        # init calico (cni)
        setup_calico(client=client_master, logger=logger)

        # join the worker nodes
        cls._join_worker_nodes(
            vm_infos_grouped=group_vms,
            ssh_pool_manager=ssh_pool_manager,
            kubeadm_cmd=kubeadm_cmd,
            logger=logger
        )

    @staticmethod
    def setup_kubeadm_conf(
            ip_address: str,
            pod_subnet: str,
            service_subnet: str,
            temp_path: str,
            control_plane_endpoint: Optional[str] = None
    ) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "kubeadm-config.j2"
        )
        if control_plane_endpoint:
            return template.render(
                ip_address=ip_address,
                pod_subnet=pod_subnet,
                service_subnet=service_subnet,
                control_plane_endpoint=control_plane_endpoint
            )
        else:
            return template.render(
                ip_address=ip_address,
                pod_subnet=pod_subnet,
                service_subnet=service_subnet
            )

    @staticmethod
    def setup_calico(pod_subnet: str, temp_path: str) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "calico.j2"
        )
        return template.render(pod_subnet=pod_subnet)

    @staticmethod
    def _join_worker_nodes(
            vm_infos_grouped: dict[str, list[SimpleVmConf]],
            kubeadm_cmd: list[str],
            ssh_pool_manager: SSHConnectionPool,
            logger: logging.Logger
    ) -> None:

        for worker in vm_infos_grouped[VmType.WORKER.name]:
            client_worker = ssh_pool_manager.get_connection(
                ip_address=worker.ip_address,
                user=worker.user,
                ssh_key=worker.ssh_key
            )

            stdin, stdout, stderr = client_worker.exec_command(kubeadm_cmd[-1])
            logger.info(f"Connect Worker {worker.ip_address}: {stdout.read().decode()} | {stderr.read().decode()}")
            sleep(20)
