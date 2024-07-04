#!/usr/bin/env python

# create a zip/tar.gz something of:
#  - the source code of both private and all third party modules, but not odoo core or
#  enterprise
#  - a csv explaining what those are
#  - the odoo config
#  - documentation

import csv
import os
import logging
import tempfile
import odoo
import shutil

from collections import namedtuple
from manifestoo_core import core_addons, odoo_series

import click
import click_odoo

_logger = logging.getLogger(__name__)


README = """
- addons.csv: describes all addons in addons directory, where they came from and author
- addons/: directory containing all addon source code
- odoo.conf: production odoo configuration
"""


OdooModule = namedtuple("OdooModule", [
    'name', 'origin', 'dependencies', 'license', 'author'
])

SUPPORTED_FORMATS = {
    "tar.gz": "gztar",
    "zip": "zip",
}


# ./export-thing.py --path=/var/lib/odoo/export.zip
@click.command()
@click_odoo.env_options(default_log_level="info")
@click.option("--path", help="Path to archive file")
def main(env, path):
    if not path:
        _logger.critical("No export path provided")
        return

    if os.path.exists(path):
        _logger.critical("Export path already exists")
        return

    if not os.path.exists(os.path.dirname(path) or "."):
        _logger.critical("Export parent directory does not exist")
        return

    (split_path, split_ext) = tuple(
        os.path.basename(path).split(".", 1)
    )
    if split_ext not in SUPPORTED_FORMATS:
        _logger.critical("Format not in supported list: %s", ", ".join(SUPPORTED_FORMATS.keys()))
        return

    modules_to_export = []

    with tempfile.TemporaryDirectory() as tmpdir:
        modules_to_exclude = list(core_addons.get_core_addons(
            odoo_series.OdooSeries.from_str(odoo.release.version.split("+")[0])
        ))
        modules_to_exclude.extend(["studio_customization"])

        for module_id in env['ir.module.module'].search([
            ('state', '=', 'installed'),
            ('name', 'not in', modules_to_exclude)
        ]):
            maybe_private_module_path = os.path.exists(f"/opt/odoo/custom/src/private/{module_id.name}")

            modules_to_export.append(
                OdooModule(
                    module_id.name,
                    module_id.website if not maybe_private_module_path else "customer specific module",
                    ",".join(module_id.dependencies_id.mapped('name')),
                    module_id.license,
                    module_id.author,
                )
            )

        export_csv = os.path.join(tmpdir, "addons.csv")
        export_addons = os.path.join(tmpdir, "addons")
        os.mkdir(export_addons)
        with open(export_csv, "w") as f:
            writer = csv.DictWriter(f, fieldnames=OdooModule._fields)
            writer.writeheader()
            for i in modules_to_export:
                writer.writerow(i._asdict())

                shutil.copytree(
                    f"/opt/odoo/auto/addons/{i.name}",
                    f"{export_addons}/{i.name}"
                )

        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write(README)

        shutil.copy("/opt/odoo/auto/odoo.conf", tmpdir)
        output_file_name = shutil.make_archive(
            os.path.join(os.path.dirname(path), split_path),
            SUPPORTED_FORMATS[split_ext],
            tmpdir
        )
        _logger.info("Created %s", output_file_name)


if __name__ == "__main__":
    main()
