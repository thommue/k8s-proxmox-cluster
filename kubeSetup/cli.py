import click
from .commands import *


@click.group()
def cli() -> None:
    """Main CLI group."""
    pass


cli.add_command(simple_cluster_setup)
cli.add_command(complex_cluster_setup)
cli.add_command(cluster_cleanup)


if __name__ == "__main__":
    cli()
