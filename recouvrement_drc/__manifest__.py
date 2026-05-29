# -*- coding: utf-8 -*-
{
    'name': "recouvrement_drc",

    'summary': "Variables complements de base",

    'description': """
                    Long description of module's purpose
                    """,

    'author': "KariSims",
    'website': "https://karisims.github.io/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0.1',

    # any module necessary for this one to work correctly
    'depends': [
            'base',
            'account',
            'recouvrement_vars'
            ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'views/receipt_payment_view.xml',
        'views/res_config_settings_views.xml',
        'views/product_template_view.xml',
        'report/certificat_view.xml',
        'report/report_certificat.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}

