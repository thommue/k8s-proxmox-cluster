import os
import logging
import paramiko
from jinja2 import Environment, FileSystemLoader
from .._setupUtils import (
    update_upgrade_cmd,
    execute_command,
    execute_commands,
    get_pwd,
    SSHConnectionPool,
)
from kubeSetup.commands.utils import ComplexVmConf, VmType


class HAProxySetup:
    def __init__(self, vm_infos: list[ComplexVmConf], logger: logging.Logger):
        self.vm_infos = vm_infos
        self.logger = logger

    def configure_haproxy(
        self, ssh_pool_manager: SSHConnectionPool
    ) -> SSHConnectionPool:

        for vm in self.vm_infos:
            if vm.vm_type == VmType.LOADBALANCER:
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

                # install haproxy
                execute_command(
                    cmd="sudo apt install haproxy -y",
                    logger=self.logger,
                    client=client_connection,
                )

                # generate the conf and transfer the file
                self._haproxy_setup(client=client_connection)

        return ssh_pool_manager

    def _haproxy_setup(self, client: paramiko.SSHClient) -> None:
        pwd = get_pwd(client=client, logger=self.logger)

        temp_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_templates"
        )

        sftp = client.open_sftp()

        with sftp.open(f"{pwd}/haproxy.cfg", mode="w") as remote_file:
            remote_file.write(
                self.setup_haproxy_conf(
                    temp_path=temp_path,
                    ip_addresses=self._extract_master_ip_addresses(),
                )
            )

        sftp.close()

        # move the file to the right position
        cmds = [
            "sudo mv haproxy.cfg /etc/haproxy/haproxy.cfg",
            "sudo systemctl restart haproxy",
            "sudo systemctl enable haproxy",
        ]
        execute_commands(
            cmds=cmds,
            client=client,
            logger=self.logger,
        )

    def _extract_master_ip_addresses(self) -> list[str]:
        return sorted(
            [vm.ip_address for vm in self.vm_infos if vm.vm_type == VmType.MASTER]
        )

    @staticmethod
    def setup_haproxy_conf(
        temp_path: str,
        ip_addresses: list[str],
    ) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "haproxy-conf.j2"
        )
        return template.render(master_nodes=ip_addresses)
