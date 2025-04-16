# -*- coding: utf-8 -*-
{
    'name': "Canada D'Ici Invoice",

    'summary': "Ce module porte sur les modifications du module Invoice/Facturation",

    'description': """
                    Il s'agit des modifications suivantes suivantes:
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
    'category': 'Invoice/CRM',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': [
        'account',
        'canadadici_sales'
        # 'product',
        # 'base',
        # 'delivery',
        # 'sale'
        ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'data/delivery_mode.xml',
        # 'data/payment_mode.xml',
        # 'views/contacts.xml',
        # 'views/devis.xml',
        'views/account_move_view.xml',
        # 'views/invoices.xml',
        # 'views/reports.xml',
        'views/report_invoice.xml',
        'views/product_template_view.xml',
        # 'views/products.xml',
        # 'views/sale_order_view.xml',
        # 'views/stocks.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'canadadici_account/static/src/components/**/*',
        ]
    },
}