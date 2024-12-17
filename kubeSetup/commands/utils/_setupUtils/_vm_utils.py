import paramiko
from typing import Optional
from .._setup import SimpleVmConf, ComplexVmConf, VmType


def setup_client(
    group_vms: Optional[dict[str, list[SimpleVmConf | ComplexVmConf]]] = None
) -> paramiko.SSHClient:
    # set up the client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if group_vms:
        # establish a connection
        master_vm = group_vms[VmType.MASTER.name][0]
        private_key = paramiko.RSAKey.from_private_key_file(master_vm.ssh_key)
        client.connect(master_vm.ip_address, 22, master_vm.user, pkey=private_key)

    # return the client so the specific sftp connection can be made
    return client
