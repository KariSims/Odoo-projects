# -*- coding: utf-8 -*-
{
    'name': "jallow_addons",
    'version': "1.0",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
        Manage price, stock and inventory for Jallow motors
    """,

    'author': "KariSims",
    'website': "https://karisims.github.io/",

    'application': True,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sale',
    'version': '1.0',

    # any module necessary for this one to work correctly
        # any module necessary for this one to work correctly
    'depends': [
        'account',
        'base',
        'sale'
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_form.xml',
        'views/sale_order_view.xml',
        'views/society_commercial_view.xml',
        'views/product_template.xml',
        'views/report_invoice.xml',
        'views/res_partner.xml',
        'views/account_move_view.xml',
    ],
}