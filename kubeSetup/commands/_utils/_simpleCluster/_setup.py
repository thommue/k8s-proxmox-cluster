import logging
import os
import paramiko
from paramiko.client import SSHClient
from time import sleep
from kubeSetup.commands._utils import VmConf
from jinja2 import Environment, FileSystemLoader


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KubeSetup Logger")


def execute_loop_commands(cmds: list[str], client: SSHClient) -> None:
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(cmd)
        logger.info(f"{cmd}: {stdout.read().decode()} | {stderr.read().decode()}")


class SimpleKubernetesClusterSetup:
    def __init__(self, vm_infos: list[VmConf]) -> None:
        self.vm_infos = vm_infos

    @staticmethod
    def _update_upgrade_cmd(client: SSHClient, upgrade: bool) -> None:
        client.exec_command("sudo apt-get update")
        if upgrade:
            client.exec_command("sudo apt-get upgrade -y")
        return

    @staticmethod
    def _conf_sysctl(client: SSHClient) -> None:
        # Read the existing /etc/sysctl.conf file using sudo
        _, stdout, _ = client.exec_command("sudo cat /etc/sysctl.conf")
        file_contents = stdout.readlines()

        settings = ["net.ipv4.ip_forward=1", "net.ipv6.conf.all.forwarding=1"]

        # Modify the file contents to uncomment the specified settings needed
        new_lines = []
        for line in file_contents:
            stripped_line = line.strip()
            if any(setting in stripped_line for setting in settings):
                new_line = stripped_line.lstrip("#").strip() + "\n"
                new_lines.append(new_line)
            else:
                new_lines.append(line)

        # Write the modified contents back to /etc/sysctl.conf using sudo and tee
        new_file_contents = "".join(new_lines)
        stdin, stdout, stderr = client.exec_command(
            "sudo tee /etc/sysctl.conf > /dev/null"
        )
        stdin.write(new_file_contents)
        stdin.flush()
        # logger.info(f"Updating sysctl.conf file: {stdout.read().decode()} | {stderr.read().decode()}")

        stdin, stdout, stderr = client.exec_command("sudo sysctl -p")
        logger.info(f"sysctl -p: {stdout.read().decode()} | {stderr.read().decode()}")

    @staticmethod
    def _turnoff_swap(client: SSHClient) -> None:
        swap_commands = ["sudo swapoff -a", "sudo sed -i '/swap/d' /etc/fstab"]
        execute_loop_commands(cmds=swap_commands, client=client)

    def _install_containerd(self, client: SSHClient) -> None:
        stdin, stdout, stderr = client.exec_command(
            "sudo apt-get install apt-transport-https ca-certificates curl jq -y"
        )
        logger.info(f"install needed pkgs...: {stdout.read().decode()} | {stderr.read().decode()}")
        sleep(5)
        preconf_cmds = [
            "sudo install -m 0755 -d /etc/apt/keyrings",
            "sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
            'echo deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
            "cat /etc/apt/sources.list.d/docker.list"
        ]
        execute_loop_commands(cmds=preconf_cmds, client=client)
        sleep(5)
        self._update_upgrade_cmd(client=client, upgrade=False)
        sleep(2)
        stdin, stdout, stderr = client.exec_command(
            "sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y"
        )
        logger.info(f"install docker, containerd...: {stdout.read().decode()} | {stderr.read().decode()}")
        sleep(15)

    @staticmethod
    def _configure_containerd(client: SSHClient) -> None:
        client.exec_command(
            "sudo containerd config default | sudo tee /etc/containerd/config.toml"
        )

        _, stdout, _ = client.exec_command(
            "cat /etc/containerd/config.toml"
        )
        file_contents = stdout.readlines()

        setting = "SystemdCgroup = false"

        # Modify the file contents to uncomment the specified settings
        new_lines = []
        for line in file_contents:
            if setting in line:
                splited_line = line.split("=")
                new_line = splited_line[0] + "= true\n"
                new_lines.append(new_line)
            else:
                new_lines.append(line)

        # Write the modified contents back to /etc/sysctl.conf using sudo and tee
        new_file_contents = "".join(new_lines)
        stdin, _, _ = client.exec_command(
            "sudo tee /etc/containerd/config.toml > /dev/null"
        )
        stdin.write(new_file_contents)
        stdin.flush()

        stdin, stdout, stderr = client.exec_command(
            "sudo systemctl restart containerd"
        )
        logger.info(f"Restart containerd: {stdout.read().decode()} | {stderr.read().decode()}")


    def _install_kube_pkgs(self, client: SSHClient) -> None:
        preconf_cmds = [
            "sudo curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
            "echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list",
            "cat /etc/apt/sources.list.d/kubernetes.list"
        ]
        execute_loop_commands(cmds=preconf_cmds, client=client)

        sleep(10)
        self._update_upgrade_cmd(client=client, upgrade=False)
        sleep(2)
        install_pull_cmd = [
            "sudo apt-get install kubelet kubeadm kubectl -y",
            "sudo kubeadm config images pull"
        ]
        execute_loop_commands(cmds=install_pull_cmd, client=client)
        sleep(15)

    def _kubeadm_calico_setup(self, client: SSHClient, ip_address: str) -> None:
        _, stdout, _ = client.exec_command("pwd")
        pwd = stdout.read().decode().split("\n")[0]

        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_templates")

        sftp = client.open_sftp()

        # Write the rendered content directly to the VM
        with sftp.open(f"{pwd}/kubeadm-config.yaml", "w") as remote_file:
            remote_file.write(
                self.setup_kubeadm_conf(
                    ip_address=ip_address,
                    pod_subnet="10.244.0.0",
                    service_subnet="10.96.0.0",
                    temp_path=temp_path
                )
            )

        with sftp.open(f"/home/tom/calico.yaml", "w") as remote_file:
            remote_file.write(
                self.setup_calico(
                    pod_subnet="10.244.0.0",
                    temp_path=temp_path
                )
            )

        sftp.close()

    def preconfigure_vms(self):

        client = self.setup_client()

        for vm in self.vm_infos:
            private_key = paramiko.RSAKey.from_private_key_file(vm.ssh_key)
            client.connect(vm.ip_address.split("/")[0], 22, vm.user, pkey=private_key)

            # update and upgrade the vm
            self._update_upgrade_cmd(client=client, upgrade=True)

            # config sysctl
            self._conf_sysctl(client=client)

            # turn off swap
            self._turnoff_swap(client=client)

            # update
            self._update_upgrade_cmd(client=client, upgrade=False)

            # install containerd
            self._install_containerd(client=client)

            # configure containerd
            self._configure_containerd(client=client)

            # install kubernetese packages
            self._install_kube_pkgs(client=client)

        # setup kubeadm conf and calico.yaml on vm
        private_key = paramiko.RSAKey.from_private_key_file(self.vm_infos[0].ssh_key)
        client.connect(self.vm_infos[0].ip_address.split("/")[0], 22, self.vm_infos[0].user, pkey=private_key)
        self._kubeadm_calico_setup(client=client, ip_address=self.vm_infos[0].ip_address.split("/")[0])

        # now init kubeadm and setup kube home
        kubeadm_cmd = self._kubeadm_init(client=client)
        print(kubeadm_cmd)


    @staticmethod
    def _kubeadm_init(client: SSHClient) -> str:
        stdin, stdout, stderr = client.exec_command(
            "sudo kubeadm init --config=kubeadm-config.yaml"
        )
        kubeadm_lines = stdout.readlines()
        logger.info(f"kubeadm init: {stdout.read().decode()} | {stderr.read().decode()}")

        kubeadm_cmd = f"{kubeadm_lines[-2].split("\\")[0]}{kubeadm_lines[-1].replace("\t", "").replace("\n", "")}"

        # kube home setup
        kube_home_cmds = [
            "mkdir -p $HOME/.kube",
            "sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config",
            "sudo chown $(id -u):$(id -g) $HOME/.kube/config",
        ]
        execute_loop_commands(cmds=kube_home_cmds, client=client)

        return kubeadm_cmd


    @staticmethod
    def setup_client() -> SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

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


# test = SimpleKubernetesClusterSetup(
#     vm_infos=[
#         VmConf(
#             vm_name="kube1",
#             target_name="alpha",
#             vm_id=500,
#             clone_type=1,
#             ip_address="192.168.150.51",
#             ip_gw="192.168.150.1",
#             cores=None,
#             memory=None,
#             disk_size=None,
#         )
#     ],
#     user="tom",
#     ssh_key=r"C:\Users\mueth\.ssh\homelab",
# )
# test.preconfigure_vms()
# print("Done")
