import click
import json
import pytest
from click.testing import CliRunner
from kubeSetup.commands.utils import parse_vm_config_file, VmConf

test_conf_01 = [
    {
        "vm_name": "test_01",
        "target_name": "test_01",
        "vm_id": 123,
        "clone_type": 1,
        "ip_address": "10.10.10.10/24",
        "ip_gw": "10.10.10.1",
        "cores": "4",
        "memory": "4092",
        "disk_size": "32",
        "user": "tom",
        "ssh_key": "C:\\Users\\mueth\\.ssh\\homelab",
    },
    {
        "vm_name": "test_02",
        "target_name": "test_02",
        "vm_id": 124,
        "clone_type": 1,
        "ip_address": "10.10.10.11/24",
        "ip_gw": "10.10.10.1",
        "cores": 4,
        "memory": 4092,
        "disk_size": 32,
        "user": "tom",
        "ssh_key": "C:\\Users\\mueth\\.ssh\\homelab",
    },
]

test_conf_02 = [
    {
        "vm_name": "test_01",
        "target_name": "test_01",
        "vm_id": 123,
        "clone_type": 1,
        "ip_address": "10.10.10.10/24",
        "ip_gw": "10.10.10.1",
        "cores": "4",
        "memory": "4092",
        "disk_size": "32",
        "user": "tom",
        "ssh_key": "C:\\Users\\mueth\\.ssh\\homelab",
    }
]

test_conf_03 = [
    {
        "vm_name": "test_01",
        "target_name": "test_01",
        "vm_id": 123,
        "clone_type": 1,
        "ip_address": "10.10.10.10/24",
        "ip_gw": "10.10.10.1",
        "cores": "4",
        "disk_size": "32",
        "user": "tom",
        "ssh_key": "C:\\Users\\mueth\\.ssh\\homelab",
    },
    {
        "vm_name": "test_02",
        "target_name": "test_02",
        "vm_id": 124,
        "clone_type": 1,
        "ip_address": "10.10.10.11/24",
        "ip_gw": "10.10.10.1",
        "cores": 4,
        "memory": 4092,
        "disk_size": 32,
        "user": "tom",
        "ssh_key": "C:\\Users\\mueth\\.ssh\\homelab",
    },
]

test_conf_04 = [
    {
        "vm_name": "test_01",
        "target_name": "test_01",
        "ip_gw": "10.10.10.1",
        "cores": "4",
        "memory": "4092",
        "disk_size": "32",
        "user": "tom",
        "ssh_key": "C:\\Users\\mueth\\.ssh\\homelab",
    },
    {
        "vm_name": "test_02",
        "target_name": "test_02",
        "vm_id": 124,
        "clone_type": 1,
        "memory": 4092,
        "disk_size": 32,
    },
]


def _setup(tmp_path, conf):
    json_file = tmp_path / "conf.json"
    with open(json_file, "w") as f:
        json.dump(conf, f)
    return json_file


@pytest.fixture
def runner():
    return CliRunner()


def test_parse_vm_config_file(tmp_path, runner):
    # Create a temporary JSON file
    json_file = _setup(tmp_path, test_conf_01)

    # Test the parse_vm_config_file function
    param = click.Option(["--vm-config-file"])
    result = parse_vm_config_file(None, param, str(json_file))
    assert isinstance(result[0], VmConf)
    assert result[0].vm_name == "test_01"
    assert result[0].target_name == "test_01"
    assert result[1].vm_id == 124
    assert result[1].disk_size == 32


def test_parse_vm_config_file_invalid_extension(runner):
    param = click.Option(["--proxmox-config-file"])
    with pytest.raises(click.BadParameter) as err:
        parse_vm_config_file(None, param, "config.txt")
    assert "File must be a JSON file" in str(err.value)


def test_parse_vm_config_file_one_vm(tmp_path, runner):
    # Create a temporary JSON file
    json_file = _setup(tmp_path, test_conf_02)

    # Test the parse_vm_config_file function
    param = click.Option(["--vm-config-file"])
    with pytest.raises(click.BadParameter) as err:
        result = parse_vm_config_file(None, param, str(json_file))
    assert "There must be at least two vm be defined in the JSON file." in str(
        err.value
    )


def test_parse_vm_config_file_cores_but_no_memory(tmp_path, runner):
    # Create a temporary JSON file
    json_file = _setup(tmp_path, test_conf_03)

    # Test the parse_vm_config_file function
    param = click.Option(["--vm-config-file"])
    with pytest.raises(click.UsageError) as err:
        result = parse_vm_config_file(None, param, str(json_file))
    assert (
        "If a cpu or memory is specified, you must specify both --cores and --memory in the config file!"
        in str(err.value)
    )


def test_parse_vm_config_file_key_error(tmp_path, runner):
    # Create a temporary JSON file
    json_file = _setup(tmp_path, test_conf_04)

    # Test the parse_vm_config_file function
    param = click.Option(["--vm-config-file"])
    with pytest.raises(click.UsageError) as err:
        result = parse_vm_config_file(None, param, str(json_file))
    assert "Please provide a valid configuration file." in str(err.value)
