# -*- coding: utf-8 -*-
{
    'name': "sms_dexchange",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'base_automation',
        'sale',
        'point_of_sale',
        'sms'
        ],

    # always loaded
    'data': [
        # 'data/cron.xml',
        'security/sms_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/templates.xml',
    ],
    # "assets": {
    #     "point_of_sale._assets_pos": [
    #         'sms_dexchange/static/src/js/pos_sms.js',
    #     ],
    # },
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}

