# -*- coding: utf-8 -*-
{
    'name': 'MaxImmo - Gestion Immobilière',
    'version': '18.0.1.3.0',
    'category': 'Real Estate',
    'summary': 'Gestion des propriétés, chambres, occupations et factures',
    'description': """
        MaxImmo - Module de gestion immobilière (Odoo v18)
        ===================================================
        - Gestion multi-propriétés : immeubles, villas, maisons
        - Configuration des pièces/unités par propriété (type, étage, surface, loyer)
        - Suivi temps réel par immeuble ET par pièce :
            * États : disponible, occupé, réservé, maintenance
            * Durée d'occupation en cours
            * Délai d'inoccupation depuis dernière libération
        - Gestion des locataires via res.partner (module base Odoo)
        - Historique complet des occupations par locataire
        - Taux d'occupation par propriété
        - Suivi minutieux des règlements par locataire (res.partner) :
            * Date et heure exactes de chaque paiement
            * Historique chronologique par occupation et par partenaire
            * Solde restant dû calculé automatiquement (mois × loyer − encaissé)
            * Modes de paiement : espèces, virement, chèque, Mobile Money
            * Vue «Par Locataire» pour voir tous les paiements d'un client
        - Suivi des échéances de factures par chambre :
            * Types configurables : Eau, Électricité, Internet, Loyer, Assurance...
            * Alertes factures en retard (par pièce et par immeuble)
            * Vue globale : en retard / à venir / toutes
            * Marquage payé en un clic
    """,
    'author': 'KariSims',
    # web_gantt est requis pour la vue Gantt (Odoo 18 Enterprise uniquement).
    # En édition Community, retirez 'web_gantt' de cette liste — les menus
    # Gantt seront inaccessibles mais le module s'installera sans erreur.
    'depends': ['base', 'mail', 'web', 'web_gantt'],
    'data': [
        # Sécurité
        'security/max_immo_security.xml',
        'security/ir.model.access.csv',
        # Données initiales
        'data/ir_sequence_data.xml',
        'data/room_type_data.xml',
        'data/bill_type_data.xml',
        # Vues
        'views/property_views.xml',
        'views/room_type_views.xml',
        'views/room_views.xml',
        'views/occupation_views.xml',
        'views/bill_type_views.xml',
        'views/bill_views.xml',
        'views/payment_views.xml',
        'views/planning_views.xml',
        'views/menu_items.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
