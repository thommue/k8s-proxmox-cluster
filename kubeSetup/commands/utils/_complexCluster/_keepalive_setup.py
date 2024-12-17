import os
import logging
import paramiko
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from .._setupUtils import (
    update_upgrade_cmd,
    execute_command,
    execute_commands,
    get_pwd,
    SSHConnectionPool,
)
from kubeSetup.commands.utils import ComplexVmConf, VmType, NodeType


class KeepaLivedSetup:
    def __init__(self, vm_infos: list[ComplexVmConf], logger: logging.Logger):
        self.vm_infos = vm_infos
        self.logger = logger

    def configure_keepalived(
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

                # install keepalived
                execute_command(
                    cmd="sudo apt install keepalived -y",
                    client=client_connection,
                    logger=self.logger,
                )

                # generate conf and transfer conf file
                self._keepalived_setup(
                    client=client_connection,
                    node_state=vm.node_state,  # type: ignore
                    virtual_ip=vm.virtual_ip_address,  # type: ignore
                )

        return ssh_pool_manager

    def _keepalived_setup(
        self, client: paramiko.SSHClient, node_state: NodeType, virtual_ip: str
    ) -> None:
        pwd = get_pwd(client=client, logger=self.logger)

        temp_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_templates"
        )

        sftp = client.open_sftp()

        # get the files on the home dir
        with sftp.open(f"{pwd}/keepalived.conf", "w") as remote_file:
            remote_file.write(
                self.setup_keepalived_conf(
                    node_state=node_state.value,
                    node_interface="eth0",
                    virtual_router_id="51",
                    node_prio="100",
                    auth_pass="passwordd",
                    virtual_ip=virtual_ip,
                    temp_path=temp_path,
                )
            )

        with sftp.open(f"{pwd}/check_apiserver.sh", "w") as remote_file:
            remote_file.write(
                self.setup_check_script(
                    virtual_ip=virtual_ip,
                    temp_path=temp_path,
                )
            )

        sftp.close()

        # move the files to the right position
        cmds = [
            "sudo mv keepalived.conf /etc/keepalived/keepalived.conf",
            "sudo mv check_apiserver.sh /etc/keepalived/check_apiserver.sh",
            "sudo systemctl start keepalived",
            "sudo systemctl enable keepalived",
        ]
        execute_commands(
            cmds=cmds,
            client=client,
            logger=self.logger,
        )

    @staticmethod
    def setup_keepalived_conf(
        node_state: str,
        node_interface: str,
        virtual_router_id: str,
        node_prio: str,
        auth_pass: str,
        virtual_ip: str,
        temp_path: str,
    ) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "keepalived-conf.j2"
        )
        return template.render(
            node_state=node_state,
            node_interface=node_interface,
            virtual_router_id=virtual_router_id,
            node_prio=node_prio,
            auth_pass=auth_pass,
            virtual_ip=virtual_ip,
        )

    @staticmethod
    def setup_check_script(virtual_ip: str, temp_path: str) -> str:
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "check_apiserver-template.j2"
        )
        return template.render(virtual_ip=virtual_ip)
