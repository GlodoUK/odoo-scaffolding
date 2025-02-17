#!/usr/bin/env python

# 1 Liner: 
# curl https://raw.githubusercontent.com/GlodoUK/odoo-scaffolding/refs/heads/glodo/tools/cloc.py | python3 - -e MODULE_TO_EXCLUDE

import json
import urllib.request

import click
import click_odoo
# from manifestoo_core.core_addons import get_core_addons
# from manifestoo_core.odoo_series import OdooSeries

import ast
import pathlib
import os
import re

import odoo

EXCLUDED_MODULE_FILES = [
    "__manifest__.py",
    "__openerp__.py",
    "static/lib/**/*",
    "migrations/**/*",
    "upgrades/**/*",
]

VALID_EXTENSIONS = ['.py', '.js', '.xml', '.css', '.scss']

DEFAULT_EXCLUDED_MODULES = [
    'payment_rbs_worldpay',

    'formio',
    'hr_employee_trainings',
    'ks_dashboard_ninja',
    'ks_dashboard_theme',
    'ks_dn_advance',

    'partner_credit_limit',

    'ebay_ept',
    'ebay_odoo_bridge',
    'fl_so_po_multi_products',
    'mailchimp',
    'odoo_helpdesk_zendesk_integration',
    'odoo_multi_channel_sale',
    'wk_wizard_messages',

    '3cxcrm',

    'aspl_website_partial_payment_ee',
    'website_cookies_consent',
    'website_cookies_consent_google',
    'website_google_analytics_4',
    'website_google_tag',
    'website_sale_google_analytics_4',
    'website_sale_google_tag',
    'website_sale_tracking_base',

    'emipro_theme_base',
    'ir_attachment_url',
    'prt_mail_messages',
    'prt_mail_messages_pro',
    'theme_clarico_vega',

    'odoo_rest',
]

def get_core_addons(major_version):
    # TODO: We should depend on manifestoo_core
    # But I need something without needing to do a redeploy

    addons = []

    # community
    addons.extend(
        urllib.request.urlopen(
        f"https://raw.githubusercontent.com/acsone/manifestoo-core/refs/heads/main/src/manifestoo_core/core_addons/addons-{major_version}.0-c.txt"
        ).read().decode("utf-8").splitlines()
    )

    # enterprise
    addons.extend(
        urllib.request.urlopen(
        f"https://raw.githubusercontent.com/acsone/manifestoo-core/refs/heads/main/src/manifestoo_core/core_addons/addons-{major_version}.0-e.txt"
        ).read().decode("utf-8").splitlines()
    )

    return [
        i for i in addons if not i.startswith('#') and len(i) > 0
    ]


# Based on https://github.com/odoo/odoo/blob/18.0/odoo/tools/cloc.py
class Cloc(object):
    def __init__(self, env):
        self.env = env
        self.modules = {}
        self.code = {}

    def parse_xml(self, s):
        s = s.strip() + "\n"
        # Unbalanced xml comments inside a CDATA are not supported, and xml
        # comments inside a CDATA will (wrongly) be considered as comment
        total = s.count("\n")
        s = re.sub("(<!--.*?-->)", "", s, flags=re.DOTALL)
        s = re.sub(r"\s*\n\s*", r"\n", s).lstrip()
        return s.count("\n"), total

    def parse_py(self, s):
        s = s.strip() + "\n"
        total = s.count("\n")
        lines = set()
        for i in ast.walk(ast.parse(s)):
            # we only count 1 for a long string or a docstring
            if hasattr(i, 'lineno'):
                lines.add(i.lineno)
        return len(lines), total

    def parse_c_like(self, s, regex):
        # Based on https://stackoverflow.com/questions/241327
        s = s.strip() + "\n"
        total = s.count("\n")

        def replacer(match):
            s = match.group(0)
            return " " if s.startswith('/') else s

        comments_re = re.compile(regex, re.DOTALL | re.MULTILINE)
        s = re.sub(comments_re, replacer, s)
        s = re.sub(r"\s*\n\s*", r"\n", s).lstrip()
        return s.count("\n"), total

    def parse_js(self, s):
        return self.parse_c_like(s, r'//.*?$|(?<!\\)/\*.*?\*/|\'(\\.|[^\\\'])*\'|"(\\.|[^\\"])*"')

    def parse_scss(self, s):
        return self.parse_c_like(s, r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"')

    def parse_css(self, s):
        return self.parse_c_like(s, r'/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"')

    def parse(self, s, ext):
        if ext == '.py':
            return self.parse_py(s)
        elif ext == '.js':
            return self.parse_js(s)
        elif ext == '.xml':
            return self.parse_xml(s)
        elif ext == '.css':
            return self.parse_css(s)
        elif ext == '.scss':
            return self.parse_scss(s)

        return (0, 0)

    def record(self, module, item='', count=0):
        self.modules.setdefault(module, {})
        if item:
            self.modules[module][item] = count
        self.code[module] = self.code.get(module, 0) + count

    def count_path(self, path):
        path = path.rstrip('/')
        exclude_list = []
        for i in odoo.modules.module.MANIFEST_NAMES:
            manifest_path = os.path.join(path, i)
            try:
                with open(manifest_path, 'rb') as manifest:
                    exclude_list.extend(EXCLUDED_MODULE_FILES)
                    d = ast.literal_eval(manifest.read().decode('latin1'))
                    for j in ['cloc_exclude', 'demo', 'demo_xml']:
                        exclude_list.extend(d.get(j, []))
                    break
            except Exception:
                pass
        exclude = set()
        for i in filter(None, exclude_list):
            exclude.update(str(p) for p in pathlib.Path(path).glob(i))

        module_name = os.path.basename(path)
        self.record(module_name)
        for root, dirs, files in os.walk(path):
            for file_name in files:
                file_path = os.path.join(root, file_name)

                if file_path in exclude:
                    continue

                ext = os.path.splitext(file_path)[1].lower()
                if ext not in VALID_EXTENSIONS:
                    continue

                with open(file_path, 'rb') as f:
                    # Decode using latin1 to avoid error that may raise by decoding with utf8
                    # The chars not correctly decoded in latin1 have no impact on how many lines will be counted
                    content = f.read().decode('latin1')
                self.record(module_name, file_path, self.parse(content, ext)[0])

    def count_modules(self, exclude_modules=None):
        if isinstance(exclude_modules, tuple):
            exclude_modules = list(exclude_modules)

        if not isinstance(exclude_modules, list):
            exclude_modules = []

        # standard and enterprise modules
        exclude_modules.extend(get_core_addons(odoo.release.version_info[0]))

        # things we just don't count
        exclude_modules.extend(DEFAULT_EXCLUDED_MODULES)

        domain = [
            ('state', '=', 'installed'),
            (
                'name',
                'not in',
                exclude_modules
            )
        ]
        # if base_import_module is present
        if self.env['ir.module.module']._fields.get('imported'):
            domain.append(('imported', '=', False))

        for module in self.env['ir.module.module'].search(domain):
            module_path = os.path.realpath(
                odoo.modules.get_module_path(module.name)
            )
            self.count_path(module_path)

    def count_studio_customization(self):
        imported_module_sa = ""
        if self.env['ir.module.module']._fields.get('imported'):
            imported_module_sa = "OR (m.imported = TRUE AND m.state = 'installed')"
        query = """
                SELECT s.id, min(m.name), array_agg(d.module)
                  FROM ir_act_server AS s
             LEFT JOIN ir_model_data AS d
                    ON (d.res_id = s.id AND d.model = 'ir.actions.server')
             LEFT JOIN ir_module_module AS m
                    ON m.name = d.module
                 WHERE s.state = 'code' AND (m.name IS null {})
              GROUP BY s.id
        """.format(imported_module_sa)
        self.env.cr.execute(query)
        data = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall()}
        for a in self.env['ir.actions.server'].browse(data.keys()):
            self.record(
                data[a.id][0] or "odoo/studio",
                "ir.actions.server/%s: %s" % (a.id, a.name),
                self.parse_py(a.code)[0],
            )

        imported_module_field = ("'odoo/studio'", "")
        if self.env['ir.module.module']._fields.get('imported'):
            imported_module_field = ("min(m.name)", "AND m.imported = TRUE AND m.state = 'installed'")
        # We always want to count manual compute field unless they are generated by studio
        # the module should be odoo/studio unless it comes from an imported module install
        # because manual field get an external id from the original module of the model
        query = r"""
                SELECT f.id, f.name, {}, array_agg(d.module)
                  FROM ir_model_fields AS f
             LEFT JOIN ir_model_data AS d ON (d.res_id = f.id AND d.model = 'ir.model.fields')
             LEFT JOIN ir_module_module AS m ON m.name = d.module {}
                 WHERE f.compute IS NOT null AND f.state = 'manual'
              GROUP BY f.id, f.name
        """.format(*imported_module_field)
        self.env.cr.execute(query)
        # Do not count field generated by studio
        all_data = self.env.cr.fetchall()
        data = {r[0]: (r[2], r[3]) for r in all_data if not ("studio_customization" in r[3] and not r[1].startswith('x_studio'))}
        for f in self.env['ir.model.fields'].browse(data.keys()):
            self.record(
                data[f.id][0] or "odoo/studio",
                "ir.model.fields/%s: %s" % (f.id, f.name),
                self.parse_py(f.compute)[0],
            )

        if not self.env['ir.module.module']._fields.get('imported'):
            return

        # Count qweb view only from imported module and not studio
        query = """
            SELECT view.id, min(mod.name), array_agg(data.module)
              FROM ir_ui_view view
        INNER JOIN ir_model_data data ON view.id = data.res_id AND data.model = 'ir.ui.view'
         LEFT JOIN ir_module_module mod ON mod.name = data.module AND mod.imported = True
             WHERE view.type = 'qweb' AND data.module != 'studio_customization'
          GROUP BY view.id
            HAVING count(mod.name) > 0
        """
        self.env.cr.execute(query)
        custom_views = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall()}
        for view in self.env['ir.ui.view'].browse(custom_views.keys()):
            module_name = custom_views[view.id][0]
            self.record(
                module_name,
                "/%s/views/%s.xml" % (module_name, view.name),
                self.parse_xml(view.arch_base)[0],
            )

        # Count js, xml, css/scss file from imported module
        query = r"""
            SELECT attach.id, min(mod.name), array_agg(data.module)
              FROM ir_attachment attach
        INNER JOIN ir_model_data data ON attach.id = data.res_id AND data.model = 'ir.attachment'
         LEFT JOIN ir_module_module mod ON mod.name = data.module AND mod.imported = True
             WHERE attach.name ~ '.*\.(js|xml|css|scss)$'
          GROUP BY attach.id
            HAVING count(mod.name) > 0
        """
        self.env.cr.execute(query)
        uploaded_file = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall()}
        for attach in self.env['ir.attachment'].browse(uploaded_file.keys()):
            module_name = uploaded_file[attach.id][0]
            ext = os.path.splitext(attach.url)[1].lower()
            if ext not in VALID_EXTENSIONS:
                continue

            # Decode using latin1 to avoid error that may raise by decoding with utf8
            # The chars not correctly decoded in latin1 have no impact on how many lines will be counted
            content = attach.raw.decode('latin1')
            self.record(
                module_name,
                attach.url,
                self.parse(content, ext)[0],
            )

    def breakdown(self):
        return self.code


@click.command()
@click_odoo.env_options(default_log_level="info")
@click.option('--exclude', '-e', multiple=True)
def main(env, exclude=None):
    c = Cloc(env)
    c.count_modules(exclude_modules=exclude)
    c.count_studio_customization()
    breakdown = c.breakdown()
    breakdown['__total'] = sum(breakdown.values())
    print(json.dumps(breakdown))


if __name__ == "__main__":
    main()
