# import os
# import logging
# import paramiko
# from time import sleep
# from paramiko.client import SSHClient
# from .._setup import ComplexVmConf, VmType
# from jinja2 import Environment, FileSystemLoader
# from .._setupUtils import setup_client, get_pwd, kubeadm_init, setup_calico
#
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("KubeSetup Logger")
#
#
# class ComplexKubernetesSetup:
#     def __init__(self, vm_infos: list[ComplexVmConf]) -> None:
#         self.vm_infos = vm_infos
#
#     def setup_cluster(self, group_vms: dict[str, list[ComplexVmConf]]) -> None:
#         # configure ssh connection to main master vm
#         client = setup_client(group_vms=group_vms)
#
#         # get temp path from vm and of the templates
#         pwd = get_pwd(client=client, logger=logger)
#         temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
#
#         # establish sftp
#         sftp = client.open_sftp()