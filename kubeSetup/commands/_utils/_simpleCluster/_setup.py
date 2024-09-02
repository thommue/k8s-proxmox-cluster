import logging
import paramiko
from kubeSetup.commands._utils import VmConf
from jinja2 import Environment, FileSystemLoader


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleKubernetesClusterSetup:
    def __init__(self, vm_infos: list[VmConf], user: str, ssh_key: str) -> None:
        self.vm_infos = vm_infos
        self.user = user
        self.ssh_key = ssh_key

    def preconfigure_vms(self):
        for vm in self.vm_infos:
            client = self.setup_client()
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key)
            client.connect(vm.ip_address, 22, self.user, pkey=private_key)

            # Execute a command to update package lists
            stdin, stdout, stderr = client.exec_command("sudo apt-get update")
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command("sudo apt-get upgrade -y")
            print(stdout.read().decode())
            print(stderr.read().decode())

            # Read the existing /etc/sysctl.conf file using sudo
            stdin, stdout, stderr = client.exec_command("sudo cat /etc/sysctl.conf")
            file_contents = stdout.readlines()

            settings = ["net.ipv4.ip_forward=1", "net.ipv6.conf.all.forwarding=1"]

            # Modify the file contents to uncomment the specified settings
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

            stdin, stdout, stderr = client.exec_command("sudo sysctl -p")
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(f"sudo swapoff -a")
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                f"sudo sed -i '/swap/d' /etc/fstab"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command("sudo apt-get update")
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "sudo apt-get install apt-transport-https ca-certificates curl jq -y"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "sudo install -m 0755 -d /etc/apt/keyrings"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                'echo deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "cat /etc/apt/sources.list.d/docker.list"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command("sudo apt-get update")
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "sudo containerd config default | sudo tee /etc/containerd/config.toml"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
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
            stdin, stdout, stderr = client.exec_command(
                "sudo tee /etc/containerd/config.toml > /dev/null"
            )
            stdin.write(new_file_contents)
            stdin.flush()

            stdin, stdout, stderr = client.exec_command(
                "sudo systemctl restart containerd"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "sudo curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "cat /etc/apt/sources.list.d/kubernetes.list"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command("sudo apt-get update")
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "sudo apt-get install kubelet kubeadm kubectl -y"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command(
                "sudo kubeadm config images pull"
            )
            print(stdout.read().decode())
            print(stderr.read().decode())

            stdin, stdout, stderr = client.exec_command("pwd")
            pwd = stdout.read().decode().split("\n")[0]
            print(stdout.read().decode())
            print(stderr.read().decode())

            sftp = client.open_sftp()

            print(f"{pwd}/kubeadm-config.yaml")

            # Write the rendered content directly to the VM
            with sftp.open(f"/home/tom/kubeadm-config.yaml", "w") as remote_file:
                remote_file.write(
                    self.setup_kubeadm_conf(
                        ip_address="192.168.150.51",
                        pod_subnet="10.244.0.0",
                        service_subnet="10.96.0.0",
                    )
                )

            with sftp.open(f"/home/tom/calico.yaml", "w") as remote_file:
                remote_file.write(
                    self.setup_calico(
                        pod_subnet="10.244.0.0",
                    )
                )

            sftp.close()

    @staticmethod
    def setup_client():
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    @staticmethod
    def setup_kubeadm_conf(
        ip_address: str, pod_subnet: str, service_subnet: str
    ) -> str:
        template = Environment(loader=FileSystemLoader("_templates")).get_template(
            "kubeadm-config.j2"
        )
        return template.render(
            ip_address=ip_address, pod_subnet=pod_subnet, service_subnet=service_subnet
        )

    @staticmethod
    def setup_calico(pod_subnet: str) -> str:
        template = Environment(loader=FileSystemLoader("_templates")).get_template(
            "calico.j2"
        )
        return template.render(pod_subnet=pod_subnet)


test = SimpleKubernetesClusterSetup(
    vm_infos=[
        VmConf(
            vm_name="kube1",
            target_name="alpha",
            vm_id=500,
            clone_type=1,
            ip_address="192.168.150.51",
            ip_gw="192.168.150.1",
            cores=None,
            memory=None,
            disk_size=None,
        )
    ],
    user="tom",
    ssh_key=r"C:\Users\mueth\.ssh\homelab",
)
test.preconfigure_vms()
print("Done")
