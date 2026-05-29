from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_apply_home_actions(self):
        """Rattrapage : applique action_id sur tous les utilisateurs Microflow existants.
        Utile si des utilisateurs ont reçu leurs groupes avant l'installation du correctif automatique.
        """
        all_micro_users = self.env['res.users'].with_context(active_test=False).search([
            ('groups_id', 'in', [
                self.env.ref('microflow.group_micro_flow_agent').id,
            ])
        ])
        all_micro_users._sync_microflow_home_action()


    micro_flow_journal_id = fields.Many2one(
        'account.journal',
        string="Journal de collecte Micro Flow",
        config_parameter='microflow.journal_id',
        domain=[('type', '=', 'cash')],
    )
    max_active_cycles = fields.Integer(
        string="Cycles simultanés max par membre",
        config_parameter='microflow.max_active_cycles',
        default=1,
    )
    draft_case_count = fields.Integer(
        string="Cases visibles avant activation",
        config_parameter='microflow.draft_case_count',
        default=5,
    )
    micro_savings_account_id = fields.Many2one(
        'account.account',
        string="Compte Dépôts Membres",
        config_parameter='microflow.savings_account_id',
        domain=[('account_type', 'in', ['liability_current', 'liability_non_current'])],
        help="Compte de passif crédité lors de la collecte d'épargne (ex: 'Dépôts membres'). "
             "L'épargne est une dette de l'institution envers le membre.",
    )
