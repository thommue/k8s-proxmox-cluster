import os
import logging
from time import sleep
from typing import Optional
from ._schemas import ClusterType
from jinja2 import Environment, FileSystemLoader
from .._setup import SimpleVmConf, ComplexVmConf, VmType
from .._setupUtils import (
    get_pwd,
    kubeadm_init,
    setup_calico,
    SSHConnectionPool,
    execute_command,
)


class ClusterSetup:

    @classmethod
    def setup_cluster(
        cls,
        group_vms: dict[str, list[SimpleVmConf | ComplexVmConf]],
        cluster_type: ClusterType,
        logger: logging.Logger,
        ssh_pool_manager: SSHConnectionPool,
        control_plane_endpoint: Optional[str] = None,
    ) -> None:
        # get the connection to the master node
        master_vm = group_vms[VmType.MASTER.name][0]
        client_master = ssh_pool_manager.get_connection(
            ip_address=master_vm.ip_address,
            user=master_vm.user,
            ssh_key=master_vm.ssh_key,
        )

        # get the root directory from the vm, just to move the files there
        pwd = get_pwd(client=client_master, logger=logger)

        # establish sftp
        sftp = client_master.open_sftp()

        # get the right templates path
        temp_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "templates",
            cluster_type.name.lower(),
        )

        # set up the right kubeadm file
        with sftp.open(f"{pwd}/kubeadm-config.yaml", "w") as remote_file:
            remote_file.write(
                cls._setup_kubeadm_conf(
                    ip_address=group_vms[VmType.MASTER.name][0].ip_address,
                    master_names=[
                        master.vm_name for master in group_vms[VmType.MASTER.name]
                    ],
                    master_ips=[
                        master.ip_address for master in group_vms[VmType.MASTER.name]
                    ],
                    pod_subnet="10.244.0.0",
                    service_subnet="10.96.0.0",
                    temp_path=temp_path,
                    control_plane_endpoint=control_plane_endpoint,
                )
            )

        # setup calico
        with sftp.open(f"{pwd}/calico.yaml", "w") as remote_file:
            remote_file.write(
                cls._setup_calico(pod_subnet="10.244.0.0", temp_path=temp_path)
            )

        # close sftp connection
        sftp.close()

        # init kubeadm and setup kube home
        kubeadm_master, kubeadm_worker = kubeadm_init(
            client=client_master,
            logger=logger,
            complex_type=True if cluster_type == ClusterType.COMPLEX else False,
        )

        # init calico (cni)
        setup_calico(client=client_master, logger=logger)

        # join the master
        if cluster_type == ClusterType.COMPLEX and kubeadm_master:
            # move the certs
            cls._distribute_kube_certs(
                vms=[
                    vm  # type: ignore
                    for vm in group_vms[VmType.MASTER.name]
                    if vm.ip_address != master_vm.ip_address
                ],
                ssh_pool_manager=ssh_pool_manager,
                logger=logger,
                master_ip=master_vm.ip_address,
            )

            cls._exc_kubeadm_cmd(
                vms=[
                    vm
                    for vm in group_vms[VmType.MASTER.name]
                    if vm.ip_address != master_vm.ip_address
                ],
                ssh_pool_manager=ssh_pool_manager,
                kubeadm_cmd=kubeadm_master,
                logger=logger,
            )

        # join the worker nodes
        cls._exc_kubeadm_cmd(
            vms=[vm for vm in group_vms[VmType.WORKER.name]],
            ssh_pool_manager=ssh_pool_manager,
            kubeadm_cmd=kubeadm_worker,
            logger=logger,
        )

    @staticmethod
    def _setup_kubeadm_conf(
        ip_address: str,
        master_names: list[str],
        master_ips: list[str],
        pod_subnet: str,
        service_subnet: str,
        temp_path: str,
        control_plane_endpoint: Optional[str] = None,
    ) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "kubeadm-config.j2"
        )
        if control_plane_endpoint:
            return template.render(
                ip_address=ip_address,
                pod_subnet=pod_subnet,
                service_subnet=service_subnet,
                control_plane_endpoint=control_plane_endpoint,
                master_names=master_names,
                master_ips=master_ips,
            )
        else:
            return template.render(
                ip_address=ip_address,
                pod_subnet=pod_subnet,
                service_subnet=service_subnet,
            )

    @staticmethod
    def _setup_calico(pod_subnet: str, temp_path: str) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "calico.j2"
        )
        return template.render(pod_subnet=pod_subnet)

    @staticmethod
    def _distribute_kube_certs(
        vms: list[ComplexVmConf],
        ssh_pool_manager: SSHConnectionPool,
        logger: logging.Logger,
        master_ip: str,
    ) -> None:
        # get the certs to the initial master node and creat a temp folder with the certs in it
        init_master_client = ssh_pool_manager.get_connection(
            ip_address=master_ip,
        )

        # get the certs with sftp
        certs_dir = "/etc/kubernetes/pki"
        kube_dir = "/etc/kubernetes"

        # create folder and move the files
        for master_vm in vms:
            client_con = ssh_pool_manager.get_connection(
                ip_address=master_vm.ip_address,
                user=master_vm.user,
                ssh_key=master_vm.ssh_key,
            )
            # get the root location
            client_pwd = get_pwd(client=client_con, logger=logger)
            # copy the certs
            execute_command(
                cmd=f'sudo sshpass -p "{master_vm.pw}" scp -o StrictHostKeyChecking=no -r {certs_dir} {master_vm.user}@{master_vm.ip_address}:{client_pwd}',
                client=init_master_client,
                logger=logger,
            )
            # move the certs to the right position
            execute_command(
                cmd=f"sudo mv {client_pwd}/pki {kube_dir}",
                client=client_con,
                logger=logger,
            )

    @staticmethod
    def _exc_kubeadm_cmd(
        vms: list[SimpleVmConf | ComplexVmConf],
        kubeadm_cmd: str,
        ssh_pool_manager: SSHConnectionPool,
        logger: logging.Logger,
    ) -> None:

        for vm in vms:
            client_worker = ssh_pool_manager.get_connection(
                ip_address=vm.ip_address, user=vm.user, ssh_key=vm.ssh_key
            )

            stdin, stdout, stderr = client_worker.exec_command(kubeadm_cmd)
            logger.info(
                f"Connect to {vm.vm_name} {vm.ip_address}: {stdout.read().decode()} | {stderr.read().decode()}"
            )
            sleep(15)
