import os
import logging
import paramiko
from jinja2 import Environment, FileSystemLoader
from kubeSetup.commands.utils import ComplexVmConf, setup_client, update_upgrade_cmd, execute_command, execute_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Keepalived Logger")


class KeepaLivedSetup:
    def __init__(self, vm_infos: list[ComplexVmConf]):
        self.vm_infos = vm_infos

    def configure_keepalived(self):
        client = setup_client()

        for vm in self.vm_infos:
            private_key = paramiko.RSAKey.from_private_key_file(vm.ssh_key)
            client.connect(vm.ip_address.split("/")[0], 22, vm.user, pkey=private_key)

            # update and upgrade the vm
            update_upgrade_cmd(client=client, upgrade=True, logger=logger)

            # install keepalived
            execute_command(
                cmd="sudo apt install keepalived -y",
                client=client,
                logger=logger,
            )

            # generate conf and transfer conf file
            self._keepalived_setup(client=client, node_state="MASTER", virtual_ip=vm.virtual_ip_address)

    def _keepalived_setup(self, client: paramiko.SSHClient, node_state: str, virtual_ip: str):
        stdout_str, _ = execute_command(
                cmd="pwd",
                client=client,
                logger=logger,
            )
        pwd = stdout_str.split("\n")[0]

        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_templates")

        sftp = client.open_sftp()

        # get the files on the home dir
        with sftp.open(f"{pwd}/keepalived.conf", "w") as remote_file:
            remote_file.write(
                self.setup_keepalived_conf(
                    node_state=node_state,
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

        # move the files to the right position
        cmds = [
            "sudo mv keepalived.conf /etc/keepalived/keepalived.conf",
            "sudo mv check_apiserver.sh /etc/keepalived/check_apiserver.sh",
            # "sudo systemctl start keepalived",
            # "sudo systemctl enable keepalived"
        ]
        execute_commands(
            cmds=cmds,
            client=client,
            logger=logger,
        )

        sftp.close()

    @staticmethod
    def setup_keepalived_conf(
            node_state: str,
            node_interface: str,
            virtual_router_id: str,
            node_prio: str,
            auth_pass: str,
            virtual_ip: str,
            temp_path: str
    ):
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
    def setup_check_script(virtual_ip: str, temp_path: str):
        template = Environment(loader=FileSystemLoader(temp_path)).get_template(
            "check_apiserver-template.j2"
        )
        return template.render(virtual_ip=virtual_ip)
