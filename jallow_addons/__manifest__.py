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
        'point_of_sale',
        ],

    # always loaded
    'data': [
        'views/product_template.xml',
        'views/pos_order_form.xml',
        'views/point_of_sale_dashboard.xml',
        'views/res_partner.xml',
        'views/report_invoice.xml',
        'views/report_stockpicking_operations.xml',
        'views/stock_picking_views.xml',
        # 'views/order_receipt.xml',
    ],
    # 'assets': {
    #     'point_of_sale.assets': [
    #         'jallow_addons/static/src/js/**/*',
    #         'jallow_addons/static/src/xml/**/*'
    #         ],
    # },
    # 'qweb': ['jallow_addons/static/src/xml/order_receipt.xml'],
}