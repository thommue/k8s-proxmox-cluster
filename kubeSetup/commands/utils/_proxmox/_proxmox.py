import logging
from typing import Any
from proxmoxer import ProxmoxAPI  # type: ignore
from time import sleep, perf_counter
from .._setup import SimpleVmConf, ComplexVmConf, ProxmoxConnection, VmConf


class ProxmoxCommands:
    def __init__(self, proxmox_conf: ProxmoxConnection, logger: logging.Logger):
        self.proxmox = ProxmoxAPI(
            proxmox_conf.url,
            user=proxmox_conf.proxmox_user,
            token_name=proxmox_conf.token_name,
            token_value=proxmox_conf.token,
            verify_ssl=proxmox_conf.ssl_verify,
            timeout=20,
        )
        self.template_id = proxmox_conf.template_id
        self.logger = logger

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
                proxmox=self.proxmox,
                node=vm.target_name,
                task_id=clone_task,
                logger=self.logger,
            )

            self.logger.info(f"The config will be set for {vm.vm_id} - {vm.vm_name}")
            sleep(10)

            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).config.set(
                ipconfig0=f"ip={vm.ip_address}/24,gw={vm.ip_gw}"
            )

            if vm.cores is not None:
                self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).config.set(
                    cores=vm.cores, memory=vm.memory
                )

            if vm.disk_size is not None:
                self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).resize.post(
                    size=vm.disk_size
                )

            self.logger.info(f"{vm.vm_id} - {vm.vm_name} will be started now")
            sleep(10)

            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.start.post()

            sleep(15)
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} is up and in starting progress\n")

    def make_required_restarts(self, vm_infos: list[SimpleVmConf | ComplexVmConf]) -> None:
        """
        Tries to SSH into the VM and checks if connection can be established.
        If the connection is established, it will be restarted the vm.
        """
        start_up_time = 120
        for _ in range(8):
            self.logger.info(f"Start uptime remaining {start_up_time}")
            sleep(15)
            start_up_time -= 15

        self.logger.info(f"Start up finished\n")
        sleep(5)

        for vm in vm_infos:
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} will be shutdown now...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.post("shutdown")

        self.logger.info(f"Shutdown finished\n")
        sleep(25)

        for vm in vm_infos:
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} starting up again...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.post("start")

        restart_time = 150
        self.logger.info(f"Restarting\n")
        for _ in range(10):
            self.logger.info(f"Waiting time for restarting the VMs -- {restart_time} seconds left")
            sleep(15)
            restart_time -= 15

        self.logger.info(f"Restarting finished.\n")

    def cleanup_vm(self, vm_infos: list[VmConf]) -> None:
        for vm in vm_infos:
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} will be shutdown now...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.post("shutdown")
        self.logger.info(f"Shutdown finished\n")
        sleep(20)

        for vm in vm_infos:
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} will be removed now...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).delete()
        sleep(10)

        self.logger.info(f"Cleanup completed.\n")

    @staticmethod
    def wait_for_task(
            proxmox: ProxmoxAPI,
            node: str,
            task_id: Any,
            logger: logging.Logger,
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
