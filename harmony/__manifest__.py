# -*- coding: utf-8 -*-
{
    'name': "harmony",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
            Long description of module's purpose
                """,

    'author': "KariSims",
    'website': "https://karisims.github.io/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
            'sale',
            'harmony_vars'
                ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/payment_mode.xml',
        'views/account_move_view.xml',
        'views/product_template.xml',
        'views/report_invoice.xml',
        'views/res_partner.xml',
        'views/sale_order_view.xml',
        'views/report_stockinventory_view.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}

