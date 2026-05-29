from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Corrige l'action d'accueil pour tous les utilisateurs Microflow existants."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.microflow.hooks import _apply_home_actions
    _apply_home_actions(env)
