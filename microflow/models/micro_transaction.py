from odoo import models, fields, api, exceptions

class MicroTransaction(models.Model):
    _name = 'micro.transaction'
    _description = 'Transactions de Caisse Micro Flow'
    _order = 'create_date desc'

    name = fields.Char(string="Référence", readonly=True, default="Nouveau")
    partner_id = fields.Many2one('res.partner', string="Membre", required=True)
    agent_id = fields.Many2one('res.users', string="Agent responsable",
                               default=lambda self: self.env.user, readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string="Montant Collecté", currency_field='currency_id', required=True)
    commission_amount = fields.Monetary("Commission déduite", currency_field='currency_id', readonly=True)
    net_amount = fields.Monetary("Montant Net Membre", currency_field='currency_id',
                                 compute="_compute_net_amount")
    journal_id = fields.Many2one('account.journal', string="Journal", required=True)
    move_id = fields.Many2one('account.move', string="Écriture Comptable", readonly=True)
    cycle_line_id = fields.Many2one(
        'micro.cycle.line', string="Case d'épargne liée",
        ondelete='set null', index=True)

    transaction_type = fields.Selection([
        ('savings', 'Épargne'),
        ('credit_repayment', 'Remboursement Crédit'),
        ('fees', 'Frais Adhésion')
    ], string="Type d'opération", required=True)

    state = fields.Selection([
        ('draft', 'Collecté (Terrain)'),
        ('confirmed', 'Confirmé (Caisse)')
    ], default='draft', string="Statut")

    is_verified = fields.Boolean(
        string="Versement Reçu (Admin)",
        groups="microflow.group_micro_flow_manager",
        help="Coché par le manager lors de la remise physique des fonds."
    )

    @api.model
    def _get_collection_journal_id(self):
        """Retourne l'ID du journal de collecte configuré, ou auto-détecte le premier
        journal cash/banque de la société et le persiste pour les appels suivants."""
        ICP = self.env['ir.config_parameter'].sudo()
        journal_id = int(ICP.get_param('microflow.journal_id', 0))
        if not journal_id:
            journal = self.env['account.journal'].search(
                [('type', '=', 'cash'), ('company_id', '=', self.env.company.id)],
                limit=1
            )
            if not journal:
                raise exceptions.UserError(
                    "Aucun journal de caisse trouvé pour cette société. "
                    "Créez-en un dans Comptabilité > Configuration > Journaux (type : Caisse), "
                    "ou configurez-le dans MICRO FLOW > Configuration."
                )
            journal_id = journal.id
            ICP.set_param('microflow.journal_id', journal_id)
        return journal_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('micro.transaction') or 'Nouveau'
        return super().create(vals_list)

    def _ensure_journal_account(self, journal):
        """Vérifie que le journal a un compte par défaut, tente de l'affecter sinon."""
        if journal.default_account_id:
            return
        account_type = 'asset_cash' if journal.type == 'cash' else 'asset_bank'
        candidate = self.env['account.account'].search([
            ('account_type', '=', account_type),
            ('company_id', '=', journal.company_id.id),
        ], limit=1)
        if candidate:
            journal.default_account_id = candidate
        else:
            raise exceptions.UserError(
                f"Le journal '{journal.name}' n'a pas de compte par défaut. "
                f"Configurez-le dans Comptabilité > Configuration > Journaux."
            )

    @api.depends('amount', 'commission_amount')
    def _compute_net_amount(self):
        for rec in self:
            rec.net_amount = rec.amount - rec.commission_amount

    def action_confirm_payment(self):
        """Validation individuelle — conservée pour compatibilité."""
        for record in self:
            if not record.is_verified:
                continue
            self._ensure_journal_account(record.journal_id)
            move_vals = {
                'journal_id': record.journal_id.id,
                'date': fields.Date.today(),
                'ref': f"Collecte {record.name} - {record.partner_id.name}",
                'line_ids': [
                    (0, 0, {
                        'name': 'Collecte Micro Flow',
                        'partner_id': record.partner_id.id,
                        'account_id': record.partner_id.property_account_receivable_id.id,
                        'debit': record.amount if record.transaction_type == 'savings' else 0,
                        'credit': record.amount if record.transaction_type != 'savings' else 0,
                    }),
                    (0, 0, {
                        'name': 'Versement Caisse Centrale',
                        'account_id': record.journal_id.default_account_id.id,
                        'debit': record.amount if record.transaction_type != 'savings' else 0,
                        'credit': record.amount if record.transaction_type == 'savings' else 0,
                    }),
                ],
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            record.write({'state': 'confirmed', 'move_id': move.id})

    def action_bulk_confirm(self):
        """1 écriture comptable groupée par agent — remplace N écritures séparées (TODO-4)."""
        verified_draft = self.filtered(lambda t: t.is_verified and t.state == 'draft')
        agents = verified_draft.mapped('agent_id')
        for agent in agents:
            agent_txns = verified_draft.filtered(lambda t: t.agent_id == agent)
            if not agent_txns:
                continue
            journal = agent_txns[0].journal_id
            self._ensure_journal_account(journal)
            line_ids = []
            for tx in agent_txns:
                line_ids.append((0, 0, {
                    'name': f"Collecte {tx.transaction_type} — {tx.partner_id.name}",
                    'partner_id': tx.partner_id.id,
                    'account_id': tx.partner_id.property_account_receivable_id.id,
                    'debit': tx.amount if tx.transaction_type == 'savings' else 0,
                    'credit': tx.amount if tx.transaction_type != 'savings' else 0,
                }))
            savings_total = sum(tx.amount for tx in agent_txns if tx.transaction_type == 'savings')
            other_total = sum(tx.amount for tx in agent_txns if tx.transaction_type != 'savings')
            line_ids.append((0, 0, {
                'name': f"Versement Caisse — Agent {agent.name}",
                'account_id': journal.default_account_id.id,
                'debit': other_total,
                'credit': savings_total,
            }))
            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'ref': f"Collecte journalière — Agent {agent.name}",
                'line_ids': line_ids,
            })
            move.action_post()
            agent_txns.write({'state': 'confirmed', 'move_id': move.id})
