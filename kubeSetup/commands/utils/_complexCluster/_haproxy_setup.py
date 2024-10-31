import os
import logging
import paramiko
from jinja2 import Environment, FileSystemLoader
from kubeSetup.commands.utils import ComplexVmConf, VmType, setup_client, update_upgrade_cmd, execute_command, execute_commands, get_pwd


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HAProxy Logger")


class HAProxySetup:
    def __init__(self, vm_infos: list[ComplexVmConf]):
        self.vm_infos = vm_infos
        
    def configure_haproxy(self):
        client = setup_client()
        
        for vm in self.vm_infos:
            if vm.vm_type == VmType.LOADBALANCER:
                private_key = paramiko.RSAKey.from_private_key_file(vm.ssh_key)
                client.connect(vm.ip_address, 22, vm.user, pkey=private_key)

                # update and upgrade the vm
                update_upgrade_cmd(client=client, upgrade=True, logger=logger)

                # install haproxy
                execute_command(
                    cmd="sudo apt install haproxy -y",
                    logger=logger,
                    client=client
                )

                # generate the conf and transfer the file
                self._haproxy_setup(client=client)

    def _haproxy_setup(self, client: paramiko.SSHClient):
        pwd = get_pwd(client=client, logger=logger)

        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

        sftp = client.open_sftp()

        with sftp.open(f"{pwd}/haproxy.cfg", mode="w") as remote_file:
            remote_file.write(
                self.setup_haproxy_conf(
                    temp_path=temp_path,
                    ip_addresses=self._extract_master_ip_addresses()
                )
            )

        sftp.close()

        # move the file to the right position
        cmds = [
            "sudo mv haproxy.cfg /etc/haproxy/haproxy.cfg",
            "sudo systemctl restart haproxy",
            "sudo systemctl enable haproxy"
        ]
        execute_commands(
            cmds=cmds,
            client=client,
            logger=logger,
        )

    def _extract_master_ip_addresses(self) -> list[str]:
        return sorted([vm.ip_address for vm in self.vm_infos if vm.vm_type == VmType.MASTER])

    @staticmethod
    def setup_haproxy_conf(
            temp_path: str,
            ip_addresses: list[str],
    ):
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "haproxy-conf.j2"
        )
        return template.render(
            master_nodes=ip_addresses
        )
    