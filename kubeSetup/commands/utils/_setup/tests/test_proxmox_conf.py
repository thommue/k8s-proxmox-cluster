import click
import json
import pytest
from click.testing import CliRunner
from kubeSetup.commands.utils import parse_proxmox_config_file
from kubeSetup.commands.utils._setup import ProxmoxConnection

test_conf = {
    "url": "test.net",
    "proxmox_user": "test@test",
    "token_name": "test",
    "token": "test-test",
    "ssl_verify": "True",
    "template_id": 123,
}


@pytest.fixture
def runner():
    return CliRunner()


def test_parse_proxmox_config_file_valid_json(tmp_path, runner):
    # Create a temporary JSON file
    json_file = tmp_path / "config.json"
    with open(json_file, "w") as f:
        json.dump(test_conf, f)

    # Test the parse_proxmox_config_file function
    param = click.Option(["--proxmox-config-file"])
    result = parse_proxmox_config_file(None, param, str(json_file))
    assert isinstance(result, ProxmoxConnection)
    assert result.url == "test.net"
    assert result.template_id == 123


def test_parse_proxmox_config_file_invalid_extension(runner):
    param = click.Option(["--proxmox-config-file"])
    with pytest.raises(click.BadParameter) as err:
        parse_proxmox_config_file(None, param, "config.txt")
    assert "File must be a JSON file" in str(err.value)
