# -*- coding: utf-8 -*-
{
    'name': "Canada D'Ici Stock",

    'summary': "Porte sur les modifications sur le module Stock",

    'description': """
                    Il s'agit des modifications suivantes :
                    -
                    -
                    -
                    """,

    'author': "KariSims",
    'website': "https://karisims.github.io/",

    'application': True,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Stock',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': [
        # 'account',
        # 'base',
        'delivery',
        # 'product',
        # 'sale'
        ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'data/delivery_mode.xml',
        # 'data/payment_mode.xml',
        # 'views/contacts.xml',
        # 'views/devis.xml',
        # 'views/invoices.xml',
        # 'views/reports.xml',
        # 'views/invoice_report.xml',
        # 'views/product_template_view.xml',
        # 'views/account_move_view.xml',
        # 'views/products.xml',
        # 'views/sale_order_view.xml',
        'views/stocks.xml'
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'canadadici_stock/static/src/components/**/*',
    #     ]
    # },
}