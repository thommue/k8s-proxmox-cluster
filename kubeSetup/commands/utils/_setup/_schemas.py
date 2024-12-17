from enum import Enum
from typing import Optional
from dataclasses import dataclass


class VmType(Enum):
    MASTER = "MASTER"
    WORKER = "WORKER"
    LOADBALANCER = "LOADBALANCER"


class NodeType(Enum):
    MASTER = "MASTER"
    BACKUP = "BACKUP"


@dataclass
class VmConf:
    vm_name: str
    target_name: str
    vm_id: int


@dataclass
class SimpleVmConf:
    vm_name: str
    vm_type: VmType
    target_name: str
    vm_id: int
    tags: str
    clone_type: int
    ip_address: str
    ip_gw: str
    user: str
    ssh_key: str
    pw: str
    cores: Optional[int] = None
    memory: Optional[int] = None
    disk_size: Optional[int] = None


@dataclass
class ComplexVmConf(SimpleVmConf):
    virtual_ip_address: Optional[str] = None
    node_state: Optional[NodeType] = None


@dataclass
class ProxmoxConnection:
    proxmox_user: str
    url: str
    token_name: str
    token: str
    ssl_verify: bool
    template_id: int
