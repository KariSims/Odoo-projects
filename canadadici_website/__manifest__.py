# -*- coding: utf-8 -*-
{
    'name': "Canada d'ici Website",

    'summary': "Concerne les retouches sur le module Website",

    'description': """
                    Il s'agit des modifications ci-après:
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
    'category': 'Website',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': [
        # 'account',
        # 'base',
        # 'delivery',
        # 'product',
        # 'sale',
        #'website'
        'website_sale',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/delivery_mode.xml',
        # 'data/payment_mode.xml',
        # 'views/contacts.xml',
        # 'views/devis.xml',
        # 'views/reports.xml',
        # 'views/invoice_report.xml',
        # 'views/product_template_view.xml',
        # 'views/account_move_view.xml',
        # 'views/products.xml',
        # 'views/sale_order_view.xml',
        'views/res_partner_view.xml',
        'views/city_and_municipality_views.xml',
        'views/delivery_carrier_views.xml',
        'views/templates.xml',
        'views/product_template_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'canadadici_website/static/src/js/address.js',
        ],
        # 'web.assets_backend': [
        #     'canadadici_website/static/src/components/**/*',
        # ]
    },
}
