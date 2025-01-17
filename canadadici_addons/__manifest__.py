# -*- coding: utf-8 -*-
{
    'name': "Canada d'ici",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
                    Long description of module's purpose
                    """,

    'author': "KariSims",
    'website': "https://karisims.github.io/",

    'application': True,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sale/CRM',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'product',
        'sale',
        'account'
        ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/contacts.xml',
        'views/devis.xml',
        'views/reports.xml',
        'views/invoice_report.xml',
        'views/product_template_view.xml',
        'views/account_move_view.xml',
        'views/products.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'canadadici_addons/static/src/components/**/*',
        ]
    },
}