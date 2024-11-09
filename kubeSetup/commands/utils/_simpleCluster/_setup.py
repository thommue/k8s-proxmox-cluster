# import os
# import logging
# import paramiko
# from time import sleep
# from paramiko.client import SSHClient
# from .._setup import SimpleVmConf, VmType
# from jinja2 import Environment, FileSystemLoader
# from .._setupUtils import setup_client, get_pwd, kubeadm_init, setup_calico
#
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("KubeSetup Logger")
#
#
# class SimpleKubernetesClusterSetup:
#     def __init__(self, vm_infos: list[SimpleVmConf]) -> None:
#         self.vm_infos = vm_infos
#
#     def setup_cluster(self, group_vms: dict[str, list[SimpleVmConf]]) -> None:
#         # configure ssh connection to main master vm
#         client = setup_client(group_vms=group_vms)
#
#         # get temp path from vm and of the templates
#         pwd = get_pwd(client=client, logger=logger)
#         temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
#
#         # establish sftp
#         sftp = client.open_sftp()
#
#         # setup kubeadm
#         with sftp.open(f"{pwd}/kubeadm-config.yaml", "w") as remote_file:
#             remote_file.write(
#                 self.setup_kubeadm_conf(
#                     ip_address=master_vm.ip_address,
#                     pod_subnet="10.244.0.0",
#                     service_subnet="10.96.0.0",
#                     temp_path=temp_path
#                 )
#             )
#
#         # setup calico
#         with sftp.open(f"{pwd}/calico.yaml", "w") as remote_file:
#             remote_file.write(
#                 self.setup_calico(
#                     pod_subnet="10.244.0.0",
#                     temp_path=temp_path
#                 )
#             )
#
#         # close sftp connection
#         sftp.close()
#
#         # init kubeadm and setup kube home
#         kubeadm_cmd = kubeadm_init(client=client, logger=logger)
#
#         # init calico (cni)
#         setup_calico(client=client, logger=logger)
#
#         # join the worker nodes
#         self._join_worker_nodes(vm_infos_grouped=group_vms, client=client, kubeadm_cmd=kubeadm_cmd)
#
#     @staticmethod
#     def setup_kubeadm_conf(
#             ip_address: str, pod_subnet: str, service_subnet: str, temp_path: str
#     ) -> str:
#         template = Environment(loader=FileSystemLoader(temp_path)).get_template(
#             "kubeadm-config.j2"
#         )
#         return template.render(
#             ip_address=ip_address, pod_subnet=pod_subnet, service_subnet=service_subnet
#         )
#
#     @staticmethod
#     def setup_calico(pod_subnet: str, temp_path: str) -> str:
#         template = Environment(loader=FileSystemLoader(temp_path)).get_template(
#             "calico.j2"
#         )
#         return template.render(pod_subnet=pod_subnet)
#
#     @staticmethod
#     def _join_worker_nodes(vm_infos_grouped: dict[str, list[SimpleVmConf]], kubeadm_cmd: str, client: SSHClient) -> None:
#
#         for worker in vm_infos_grouped[VmType.WORKER.name]:
#
#             private_key = paramiko.RSAKey.from_private_key_file(worker.ssh_key)
#             client.connect(worker.ip_address, 22, worker.user, pkey=private_key)
#
#             stdin, stdout, stderr = client.exec_command(kubeadm_cmd)
#             logger.info(f"Connect Worker {worker.ip_address}: {stdout.read().decode()} | {stderr.read().decode()}")
#             sleep(20)
