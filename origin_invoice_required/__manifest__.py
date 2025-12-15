# -*- coding: utf-8 -*-
{
    'name': "origin_invoice_required",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
        Cancel create invoice without origin quotation
    """,

    'author': "KariSim's",
    'website': "https://karisims.github.io",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'account'],
}

