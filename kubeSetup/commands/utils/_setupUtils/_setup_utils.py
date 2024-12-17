from time import sleep
from logging import Logger
from typing import Optional
from paramiko.client import SSHClient
from ._general_commands import execute_command, execute_commands, update_upgrade_cmd


def _modify_file(
    client: SSHClient, file_path: str, settings: list[str], uncomment: bool
) -> None:
    """Modify specified settings in a file."""
    _, stdout, _ = client.exec_command(f"sudo cat {file_path}")
    file_contents = stdout.readlines()

    new_lines = []
    for line in file_contents:
        matched_setting = next(
            (setting for setting in settings if setting in line), None
        )
        if matched_setting:
            if uncomment:
                new_lines.append(line.lstrip("#").strip() + "\n")
            else:
                if "pause:3.8" in matched_setting:
                    new_lines.append(line.replace("3.8", "3.9"))
                else:
                    new_lines.append(line.replace("false", "true"))
        else:
            new_lines.append(line)

    new_file_contents = "".join(new_lines)
    stdin, _, _ = client.exec_command(f"sudo tee {file_path} > /dev/null")
    stdin.write(new_file_contents)
    stdin.flush()


def conf_sysctl(client: SSHClient, logger: Logger) -> None:
    """Configure sysctl settings."""
    settings = ["net.ipv4.ip_forward=1", "net.ipv6.conf.all.forwarding=1"]
    _modify_file(
        client=client, file_path="/etc/sysctl.conf", settings=settings, uncomment=True
    )
    execute_command("sudo sysctl -p", client, logger)


def turnoff_swap(client: SSHClient, logger: Logger) -> None:
    swap_commands = ["sudo swapoff -a", "sudo sed -i '/swap/d' /etc/fstab"]
    execute_commands(swap_commands, client, logger)


def install_containerd(client: SSHClient, logger: Logger) -> None:
    execute_command(
        "sudo apt-get install apt-transport-https ca-certificates curl jq -y",
        client,
        logger,
    )
    sleep(5)
    preconf_cmds = [
        "sudo install -m 0755 -d /etc/apt/keyrings",
        "sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
        'echo deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
        "cat /etc/apt/sources.list.d/docker.list",
    ]
    execute_commands(cmds=preconf_cmds, client=client, logger=logger)
    update_upgrade_cmd(client=client, upgrade=False, logger=logger)
    sleep(2)
    execute_command(
        "sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y",
        client,
        logger,
    )
    sleep(15)


def configure_containerd(client: SSHClient, logger: Logger) -> None:
    """Configure containerd to use systemd as the cgroup driver."""
    execute_command(
        "sudo containerd config default | sudo tee /etc/containerd/config.toml",
        client,
        logger,
    )
    _modify_file(
        client=client,
        file_path="/etc/containerd/config.toml",
        settings=["registry.k8s.io/pause:3.8", "SystemdCgroup = false"],
        uncomment=False,
    )
    execute_command("sudo systemctl restart containerd", client, logger)


def install_kube_pkgs(client: SSHClient, logger: Logger, kube_version: str) -> None:
    preconf_cmds = [
        f"sudo curl -fsSL https://pkgs.k8s.io/core:/stable:/v{kube_version}/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
        f"echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v{kube_version}/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list",
        "cat /etc/apt/sources.list.d/kubernetes.list",
    ]
    execute_commands(cmds=preconf_cmds, client=client, logger=logger)
    sleep(10)
    update_upgrade_cmd(client=client, upgrade=False, logger=logger)
    sleep(2)
    install_pull_cmd = [
        "sudo apt-get install kubelet kubeadm kubectl -y",
        "sudo kubeadm config images pull",
    ]
    execute_commands(cmds=install_pull_cmd, client=client, logger=logger)
    sleep(15)


def kubeadm_init(
    client: SSHClient, logger: Logger, complex_type: bool
) -> tuple[Optional[str], str]:
    """Initialize Kubernetes master node using kubeadm."""
    _, stdout, _ = client.exec_command("sudo kubeadm init --config=kubeadm-config.yaml")
    kubeadm_lines = stdout.readlines()
    logger.info(f"kubeadm init output: {''.join(kubeadm_lines)}")

    # Extract kubeadm join command for worker and master
    worker_join_cmd = (
        f"sudo {kubeadm_lines[-2].split('\\')[0]}{kubeadm_lines[-1].strip()}"
    )

    if complex_type:
        master_join_cmd = f"sudo {kubeadm_lines[-8].split('\\')[0].strip()} {kubeadm_lines[-7].split('\\')[0].strip()} {kubeadm_lines[-6].strip()}"
    else:
        master_join_cmd = None

    # Set up kube home config
    kube_home_cmds = [
        "mkdir -p $HOME/.kube",
        "sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config",
        "sudo chown $(id -u):$(id -g) $HOME/.kube/config",
    ]
    execute_commands(kube_home_cmds, client, logger)

    return master_join_cmd, worker_join_cmd


def setup_calico(client: SSHClient, logger: Logger) -> None:
    """Install Calico networking plugin."""
    execute_command("kubectl apply -f calico.yaml", client, logger)
    sleep(30)
