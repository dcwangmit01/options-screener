import click
import logging

from app import app
from app import cli as app_cli
from app import utils

log = logging.getLogger(__name__)

app = app.App()


@click.group()
def cli():
    """Subcommand to print configuration"""

    pass


@cli.command()
@app_cli.pass_context
def print(ctx):
    """This command loads config.yaml and the current ENV-ironment,
    creates a single merged dict, and prints to stdout.
    """

    c = app.get_config_dict(ctx)
    click.echo(utils.YamlUtils.yaml_dict_to_string(c))
