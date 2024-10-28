import os
import logging
import paramiko
from jinja2 import Environment, FileSystemLoader
from kubeSetup.commands.utils import ComplexVmConf, VmType, setup_client, update_upgrade_cmd, execute_command, execute_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HAProxy Logger")


class HAProxySetup:
    def __init__(self, vm_infos: list[ComplexVmConf]):
        self.vm_infos = vm_infos
        
    def configure_haproxy(self):
        client = setup_client()
        
        for vm in self.vm_infos:
            private_key = paramiko.RSAKey.from_private_key_file(vm.ssh_key)
            client.connect(vm.ip_address.split("/")[0], 22, vm.user, pkey=private_key)
            
            # update and upgrade the vm
            update_upgrade_cmd(client=client, upgrade=True, logger=logger)
            
            # install haproxy
            execute_command(
                cmd="sudo apt install haproxy -y", 
                logger=logger, 
                client=client
            )
            
            # generate the conf and transfer the file
            self._haproxy_setup()

    def _haproxy_setup(self, client: paramiko.SSHClient):
        stdout_str, _ = execute_command(
            cmd="pwd",
            client=client,
            logger=logger,
        )
        pwd = stdout_str.split("\n")[0]

        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_templates")

        sftp = client.open_sftp()

    def _extract_master_ip_addresses(self) -> list[str]:
        return sorted([vm.ip_address.split("/")[0] for vm in self.vm_infos if vm.vm_type == VmType.MASTER])

    @staticmethod
    def setup_haproxy_conf(
            temp_path: str,
            ip_addresses: list[str],
    ):
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "keepalived-conf.j2"
        )
        return template.render(
            master_nodes=ip_addresses
        )
    