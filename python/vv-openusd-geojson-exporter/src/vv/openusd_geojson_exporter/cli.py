import argparse
from pathlib import Path

from . import __version__
from .core import export_to_openusd


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--version',
        action='version',
        version=f'%s(prog) {__version__}',
    )

    parser.add_argument(
        '-i',
        '--input',
        required=True,
        help='Path to the GeoJSON file to read'
    )

    parser.add_argument(
        '-o',
        '--output',
        required=True,
        help='Path to where the .usda file will be exported'
    )

    parser.add_argument(
        '-m',
        '--meters-per-unit',
        required=True,
        type=float,
        help='Used to tell USD how many meters each unit should be representing.'
    )

    parser.add_argument(
        '-s',
        '--scale-factor',
        required=True,
        type=float,
        help='Scales the final geometry by this amount on all axis.'
    )

    parser.add_argument(
        '--attr-names',
        required=False,
        type=str,
        help='Only export attributes present in the given comma-separated list (e.g.: "id,created_at")'
    )

    cli = parser.parse_args()

    attributes_names = []
    if attr_names := cli.attr_names:
        attributes_names = attr_names.split(',')

    export_to_openusd(
        Path(cli.input),
        Path(cli.output),
        meters_per_unit=cli.meters_per_unit,
        scale_factor=cli.scale_factor,
        attributes_allowlist=attributes_names,
    )
