import click
from .commands import *


@click.group()
def cli() -> None:
    """Main CLI group."""
    pass


cli.add_command(simple_cluster_setup)


if __name__ == "__main__":
    cli()
