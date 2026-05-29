# -*- coding: utf-8 -*-
{
    'name': "Microflow",

    'summary': "Gestion des cycles d épargne et crédits avec collecte de terrain",

    'description': """
            Module MICRO FLOW pour Odoo :
            - Gestion des membres avec ID unique (Zone/Année/Mois)
            - Capture GPS via Chrome Android
            - Cycles d épargne (Grilles de cases — OWL MicroGrid)
            - Crédits avec calcul d échéancier et paiements partiels
            - Automatisation des frais d adhésion et commissions
            - Workflow de caisse virtuelle (Agent/Manager)
            - Dashboard Manager avec validation groupée
            - PWA offline avec sync automatique
            """,

    'author': "KariSims",
    'website': "https://karisims.github.io/",

    'category': 'Finance/Microfinance',
    'version': '0.5',
    'post_init_hook': 'post_init_hook',

    'depends': [
        'base',
        'contacts',
        'account',
        'base_setup',
    ],

    'data': [
        # Security — order matters: groups first, then rules, then ACL
        'security/security_groups.xml',
        'security/record_rules.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',

        # Wizards
        'wizard/credit_payment_wizard_views.xml',
        'wizard/savings_repayment_wizard.xml',

        # Views
        'views/res_partner_views.xml',
        'views/micro_zone_views.xml',
        'views/micro_transaction_views.xml',
        'views/micro_cycle_views.xml',
        'views/micro_credit_views.xml',
        'views/res_config_settings_views.xml',

        # Menus last (references actions defined in views above)
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # GPS capture
            'microflow/static/src/js/gps_capture.js',
            # PWA service worker registration (sw_register only — service_worker.js servi via contrôleur)
            'microflow/static/src/js/sw_register.js',
            # OWL MicroGrid component (TODO-2)
            'microflow/static/src/components/MicroGrid/MicroGrid.js',
            'microflow/static/src/components/MicroGrid/MicroGrid.xml',
            'microflow/static/src/components/MicroGrid/MicroGrid.scss',
            # OWL ManagerDashboard — transactions terrain + crédits actifs/pending
            'microflow/static/src/components/ManagerDashboard/ManagerDashboard.js',
            'microflow/static/src/components/ManagerDashboard/ManagerDashboard.xml',
            'microflow/static/src/components/ManagerDashboard/ManagerDashboard.scss',
            # Mobile styles — wizard plein écran + terrain typography
            'microflow/static/src/css/microflow_mobile.scss',
        ],
    },
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
