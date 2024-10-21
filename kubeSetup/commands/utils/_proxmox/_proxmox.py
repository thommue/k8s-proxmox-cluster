import logging
from typing import Any
from proxmoxer import ProxmoxAPI  # type: ignore
from time import sleep, perf_counter
from .._setup import SimpleVmConf, ComplexVmConf, ProxmoxConnection


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Proxmox VM Setup")


class ProxmoxCommands:
    def __init__(self, proxmox_conf: ProxmoxConnection):
        self.proxmox = ProxmoxAPI(
            proxmox_conf.url,
            user=proxmox_conf.proxmox_user,
            token_name=proxmox_conf.token_name,
            token_value=proxmox_conf.token,
            verify_ssl=proxmox_conf.ssl_verify,
            timeout=20,
        )
        self.template_id = proxmox_conf.template_id

    def clone_vm(self, vm_infos: list[SimpleVmConf | ComplexVmConf]) -> None:
        for vm in vm_infos:
            clone_task = (
                self.proxmox.nodes(vm.target_name)
                .qemu(self.template_id)
                .clone.post(
                    newid=vm.vm_id,
                    name=vm.vm_name,
                    target=vm.target_name,
                    full=vm.clone_type,
                )
            )

            self.wait_for_task(
                proxmox=self.proxmox, node=vm.target_name, task_id=clone_task
            )

            logger.info(f"The config will be set for {vm.vm_id} - {vm.vm_name}")
            sleep(10)

            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).config.set(
                ipconfig0=f"ip={vm.ip_address},gw={vm.ip_gw}"
            )

            if vm.cores is not None:
                self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).config.set(
                    cores=vm.cores, memory=vm.memory
                )

            if vm.disk_size is not None:
                self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).resize.post(
                    size=vm.disk_size
                )

            logger.info(f"{vm.vm_id} - {vm.vm_name} will be started now")
            sleep(10)

            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.start.post()

            sleep(15)
            logger.info(f"{vm.vm_id} - {vm.vm_name} is up and in starting progress\n")

    def make_required_restarts(self, vm_infos: list[SimpleVmConf | ComplexVmConf]):
        """
        Tries to SSH into the VM and checks if connection can be established.
        If the connection is established, it will be restarted the vm.
        """
        sleep(125)

        for vm in vm_infos:
            logger.info(f"{vm.vm_id} - {vm.vm_name} will be shutdown now...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.post("shutdown")

        sleep(25)

        for vm in vm_infos:
            logger.info(f"{vm.vm_id} - {vm.vm_name} starting up again...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.post("start")

        logger.info(f"Waiting time for restarting the VMs (takes about 2 minutes...)")
        sleep(150)



        # print("test")
        # self.proxmox.nodes(vm_infos[0].target_name).qemu(vm_infos[0].vm_id).status.post("start")
        # print("test2")

        # client = paramiko.SSHClient()
        # client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #
        # for vm in vm_infos:
        #     while True:
        #         try:
        #             private_key = paramiko.RSAKey.from_private_key_file(vm.ssh_key)
        #             client.connect(hostname=vm.ip_address.split("/")[0], port=22, username=vm.user, pkey=private_key)
        #             logger.info(f"SSHing into VM {vm.vm_id} - {vm.vm_name}. VM is ready!")
        #             logger.info(f"{vm.vm_id} - {vm.vm_name} will be started now...")
        #
        #             # Open an SSH session and run the reboot command
        #             stdin, stdout, stderr = client.exec_command("sudo reboot")
        #
        #             # This waits for the command to complete
        #             stdout.channel.recv_exit_status()
        #             sleep(15)
        #             return True
        #
        #         except paramiko.ssh_exception.NoValidConnectionsError:
        #             logger.info(f"{vm.vm_id} - {vm.vm_name} not ready yet!")
        #             sleep(10)
        #
        #         finally:
        #             client.close()

    @staticmethod
    def wait_for_task(
        proxmox: ProxmoxAPI,
        node: str,
        task_id: Any,
        timeout: int = 300,
        interval: int = 10,
    ) -> None:
        sleep(2)
        start_time = perf_counter()
        logger.info(f"Task {task_id} is started")
        while perf_counter() - start_time < timeout:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status["status"] == "stopped":
                if "exitstatus" in status and status["exitstatus"] == "OK":
                    logger.info(f"Task {task_id} stopped and status was OK.")
                    return
                else:
                    raise Exception(
                        f"Task {task_id} has failed with exit status: {status['exitstatus']}!"
                    )
            logger.info(f"Task {task_id} in progress.")
            sleep(interval)
        raise TimeoutError(f"Task {task_id} did not complete in {timeout} seconds!")
