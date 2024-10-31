from time import sleep
from logging import Logger
from paramiko import SSHClient


def execute_command(cmd: str, client: SSHClient, logger: Logger) -> tuple[str, str]:
    """Execute a single SSH command and log its output."""
    stdin, stdout, stderr = client.exec_command(cmd)
    stdout_str, stderr_str = stdout.read().decode(), stderr.read().decode()
    logger.info(f"{cmd}: {stdout_str} | {stderr_str}")
    return stdout_str, stderr_str


def execute_commands(cmds: list[str], client: SSHClient, logger: Logger) -> None:
    """Execute a list of commands with a delay and log output."""
    for cmd in cmds:
        sleep(1)
        execute_command(cmd, client, logger)
        sleep(1)


def update_upgrade_cmd(client: SSHClient, upgrade: bool, logger: Logger) -> None:
    execute_command("sudo apt-get update", client, logger=logger)
    if upgrade:
        execute_command("sudo apt-get upgrade -y", client, logger=logger)


def get_pwd(client: SSHClient, logger: Logger) -> str:
    stdout_str, _ = execute_command(
        cmd="pwd",
        client=client,
        logger=logger,
    )
    return stdout_str.split("\n")[0]
