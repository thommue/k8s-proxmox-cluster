import json
import click
from typing import Any
from ._schemas import ProxmoxConnection


def _converter(conf: dict[str, Any]) -> ProxmoxConnection:
    try:
        return ProxmoxConnection(
            proxmox_user=conf["proxmox_user"],
            url=conf["url"],
            token_name=conf["token_name"],
            token=conf["token"],
            ssl_verify=bool(conf["ssl_verify"]),
            template_id=conf["template_id"],
        )
    except KeyError:
        raise click.UsageError(
            "Please provide a valid configuration file."
            "The following is required: "
            "proxmox_user, url, token_name, token, ssl_verify, template_id"
        )


def parse_proxmox_config_file(
    _: Any, param: click.Parameter, value: str
) -> ProxmoxConnection:
    if value.endswith(".json"):
        with open(value, "r") as file:
            return _converter(conf=json.load(file))
    else:
        raise click.BadParameter("File must be a JSON file", param=param)
