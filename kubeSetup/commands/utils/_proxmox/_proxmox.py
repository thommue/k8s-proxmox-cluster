import logging
from tqdm import tqdm
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

            self._prg_bar(
                sleep_time=10,
                desc=f"The config will be set for {vm.vm_id} - {vm.vm_name}\n",
                logger=self.logger,
            )

            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).config.set(
                ipconfig0=f"ip={vm.ip_address}/24,gw={vm.ip_gw}"
            )

            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).config.post(tags=vm.tags)

            if vm.cores is not None:
                self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).config.set(
                    cores=vm.cores, memory=vm.memory
                )

            if vm.disk_size is not None:
                self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).resize.post(
                    size=vm.disk_size
                )
            sleep(5)
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.start.post()
            self._prg_bar(
                sleep_time=15,
                desc=f"Starting up {vm.vm_id} - {vm.vm_name}\n",
                logger=self.logger,
            )

    def make_required_restarts(
        self, vm_infos: list[SimpleVmConf | ComplexVmConf]
    ) -> None:
        """
        Tries to SSH into the VM and checks if connection can be established.
        If the connection is established, it will be restarted the vm.
        """
        self._prg_bar(sleep_time=125, desc="Initial start up\n", logger=self.logger)

        for vm in vm_infos:
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} will be shutdown now...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.post("shutdown")

        self._prg_bar(
            sleep_time=25,
            desc="Waiting for the shutdown to finish\n",
            logger=self.logger,
        )

        for vm in vm_infos:
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} starting up again...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.post("start")

        self.logger.info(f"Restarting all vms\n")

        self._prg_bar(
            sleep_time=150,
            desc="Waiting for the restart task to finish\n",
            logger=self.logger,
        )

    def cleanup_vm(self, vm_infos: list[VmConf]) -> None:
        for vm in vm_infos:
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} will be shutdown now...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).status.post("shutdown")
        self._prg_bar(
            sleep_time=25,
            desc="Waiting for the shutdown to finish\n",
            logger=self.logger,
        )

        for vm in vm_infos:
            self.logger.info(f"{vm.vm_id} - {vm.vm_name} will be removed now...")
            self.proxmox.nodes(vm.target_name).qemu(vm.vm_id).delete()
        self._prg_bar(
            sleep_time=10,
            desc="Waiting for the delete task to finish\n",
            logger=self.logger,
        )

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

    @staticmethod
    def _prg_bar(sleep_time: int, desc: str, logger: logging.Logger) -> None:
        logger.info(desc)
        sleep(1)
        for _ in tqdm(range(sleep_time - 1), colour="green"):
            sleep(1)
        logger.info("\n")
