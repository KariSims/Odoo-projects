{
    'name': 'Real Estate Management',
    'version': '18.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Manage real estate properties, contracts, and maintenance',
    'description': """
        Real Estate Management Module for Odoo
        ======================================
        - Manage Properties
        - Manage Contracts (Rent/Sell)
        - Manage Maintenance Requests
    """,
    'images': ['static/description/cover.png'],
    'author': 'Alan',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/real_estate_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/property_views.xml',
        'views/contract_views.xml',
        'views/maintenance_views.xml',
        'views/dashboard_views.xml',
        'views/menu_items.xml',
    ],
    'assets': {
        'web.assets_backend': [
             'real_estate_management_advanced/static/src/components/**/*.js',
             'real_estate_management_advanced/static/src/components/**/*.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
