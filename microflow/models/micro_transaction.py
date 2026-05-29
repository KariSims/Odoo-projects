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
    cycle_id = fields.Many2one(
        'micro.cycle', string="Cycle épargne lié",
        ondelete='set null', index=True,
        help="Renseigné uniquement pour les retraits épargne (transfert vers crédit).")

    transaction_type = fields.Selection([
        ('savings', 'Épargne'),
        ('credit_repayment', 'Remboursement Crédit'),
        ('fees', 'Frais Adhésion'),
        ('savings_withdrawal', 'Retrait Épargne (Transfert Crédit)'),
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

    def _get_transfer_journal_id(self):
        """Retourne le premier journal 'Opérations diverses' de la société.
        Utilisé pour les transferts internes épargne → crédit (sans mouvement de caisse)."""
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not journal:
            raise exceptions.UserError(
                "Aucun journal 'Opérations diverses' trouvé. "
                "Créez-en un dans Comptabilité > Configuration > Journaux (type : Opérations diverses)."
            )
        return journal

    def _get_savings_account(self):
        """Retourne le compte de dépôts membres configuré (passif courant).

        L'épargne collectée est une dette de l'institution envers le membre :
        elle doit être créditée sur un compte de passif, pas sur le compte clients.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        account_id = int(ICP.get_param('microflow.savings_account_id', 0))
        if not account_id:
            raise exceptions.UserError(
                "Aucun compte de dépôts membres configuré. "
                "Définissez-le dans MICRO FLOW > Configuration > Compte Dépôts Membres."
            )
        account = self.env['account.account'].browse(account_id)
        if not account.exists():
            raise exceptions.UserError(
                "Le compte de dépôts membres configuré est introuvable. "
                "Vérifiez la configuration dans MICRO FLOW > Configuration."
            )
        return account

    def _build_move_lines(self, txns, journal, label, date=None):
        """Construit les line_ids d'un account.move pour un groupe de transactions.

        Épargne  : DR Caisse / CR Compte Dépôts Membres (passif)
        Autres   : DR Caisse / CR Compte Client (receivable)

        Multi-devise : si la devise du groupe ≠ devise société,
          - debit/credit = montants convertis en devise société
          - amount_currency = montants d'origine, currency_id = devise d'origine
        Toutes les txns du groupe doivent partager la même devise (garanti par action_bulk_confirm).
        """
        if date is None:
            date = fields.Date.today()
        company = self.env.company
        company_currency = company.currency_id

        has_savings = any(t.transaction_type == 'savings' for t in txns)
        savings_account = self._get_savings_account() if has_savings else None

        group_currency = (txns[0].currency_id or company_currency) if txns else company_currency
        is_foreign = group_currency != company_currency

        line_ids = []
        total_company = 0.0
        total_foreign = 0.0

        for tx in txns:
            tx_currency = tx.currency_id or company_currency
            amount_company = (
                tx_currency._convert(tx.amount, company_currency, company, date)
                if is_foreign else tx.amount
            )

            if tx.transaction_type == 'savings':
                credit_line = {
                    'name': f"Dépôt épargne — {tx.partner_id.name}",
                    'partner_id': tx.partner_id.id,
                    'account_id': savings_account.id,
                    'debit': 0.0,
                    'credit': amount_company,
                }
            else:
                credit_line = {
                    'name': f"Collecte {tx.transaction_type} — {tx.partner_id.name}",
                    'partner_id': tx.partner_id.id,
                    'account_id': tx.partner_id.property_account_receivable_id.id,
                    'debit': 0.0,
                    'credit': amount_company,
                }

            if is_foreign:
                credit_line['amount_currency'] = -tx.amount  # crédit → signe négatif
                credit_line['currency_id'] = group_currency.id

            line_ids.append((0, 0, credit_line))
            total_company += amount_company
            total_foreign += tx.amount

        # Ligne de caisse : DR pour le total en devise société (cash reçu par l'institution)
        cash_line = {
            'name': label,
            'account_id': journal.default_account_id.id,
            'debit': total_company,
            'credit': 0.0,
        }
        if is_foreign:
            cash_line['amount_currency'] = total_foreign
            cash_line['currency_id'] = group_currency.id

        line_ids.append((0, 0, cash_line))
        return line_ids

    @api.depends('amount', 'commission_amount')
    def _compute_net_amount(self):
        for rec in self:
            rec.net_amount = rec.amount - rec.commission_amount

    def action_confirm_payment(self):
        """Validation individuelle — conservée pour compatibilité."""
        company_currency = self.env.company.currency_id
        date = fields.Date.today()
        for record in self:
            if not record.is_verified:
                continue
            self._ensure_journal_account(record.journal_id)
            line_ids = self._build_move_lines(
                [record],
                record.journal_id,
                f"Versement Caisse — {record.partner_id.name}",
                date=date,
            )
            tx_currency = record.currency_id or company_currency
            move_vals = {
                'journal_id': record.journal_id.id,
                'date': date,
                'ref': f"Collecte {record.name} - {record.partner_id.name}",
                'line_ids': line_ids,
            }
            if tx_currency != company_currency:
                move_vals['currency_id'] = tx_currency.id
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            record.write({'state': 'confirmed', 'move_id': move.id})

    def action_bulk_confirm(self):
        """1 écriture comptable groupée par agent et par devise — remplace N écritures séparées (TODO-4).

        Le groupement par devise évite de mélanger des montants de devises différentes
        dans un même account.move (total de caisse invalide sans conversion).
        """
        verified_draft = self.filtered(lambda t: t.is_verified and t.state == 'draft')
        company_currency = self.env.company.currency_id
        date = fields.Date.today()

        # Grouper par (agent, devise) — une account.move par combinaison
        groups = {}
        for tx in verified_draft:
            key = (tx.agent_id, tx.currency_id or company_currency)
            if key not in groups:
                groups[key] = self.env['micro.transaction'].browse()
            groups[key] |= tx

        for (agent, currency), group_txns in groups.items():
            if not group_txns:
                continue
            journal = group_txns[0].journal_id
            self._ensure_journal_account(journal)
            line_ids = self._build_move_lines(
                group_txns,
                journal,
                f"Versement Caisse — Agent {agent.name}",
                date=date,
            )
            move_vals = {
                'journal_id': journal.id,
                'date': date,
                'ref': f"Collecte journalière — Agent {agent.name}",
                'line_ids': line_ids,
            }
            if currency != company_currency:
                move_vals['currency_id'] = currency.id
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            group_txns.write({'state': 'confirmed', 'move_id': move.id})
