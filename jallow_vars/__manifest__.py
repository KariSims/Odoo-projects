# -*- coding: utf-8 -*-
{
    'name': "Variables complements",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
                Long description of module's purpose
                    """,

    'author': "KariSims",
    'website': "https://karisims.github.io/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sale',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': [
        'account',
        'base',
        'sale',
        'stock_delivery',
        'sale_stock'
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
    ],
}

