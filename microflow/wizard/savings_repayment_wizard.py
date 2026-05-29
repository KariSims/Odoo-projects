# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SavingsRepaymentWizard(models.TransientModel):
    _name = 'savings.repayment.wizard'
    _description = "Assistant de transfert épargne → crédit"

    # ── Contexte crédit (readonly) ────────────────────────────────────────────
    credit_line_id = fields.Many2one(
        'micro.credit.line', string="Échéance cible", readonly=True, required=True)
    partner_id = fields.Many2one(
        'res.partner', related='credit_line_id.credit_id.partner_id',
        string="Membre", readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='credit_line_id.currency_id', readonly=True)

    installment_sequence = fields.Integer(
        related='credit_line_id.sequence', readonly=True, string="N° Échéance")
    installment_residual = fields.Monetary(
        related='credit_line_id.amount_residual', readonly=True,
        string="Reste à payer sur l'échéance", currency_field='currency_id')

    # ── Source épargne ────────────────────────────────────────────────────────
    cycle_id = fields.Many2one(
        'micro.cycle', string="Cycle épargne source",
        required=True,
        domain="[('partner_id', '=', partner_id), ('state', '=', 'active'), ('savings_balance', '>', 0)]",
        help="Cycle épargne depuis lequel prélever le montant.")
    savings_balance = fields.Monetary(
        related='cycle_id.savings_balance', readonly=True,
        string="Solde épargne disponible", currency_field='currency_id')

    # ── Saisie agent ──────────────────────────────────────────────────────────
    amount_to_transfer = fields.Monetary(
        string="Montant à prélever de l'épargne",
        currency_field='currency_id',
        required=True,
        help="Montant à récupérer depuis le solde épargne du membre pour régler cette échéance.")

    def action_validate(self):
        self.ensure_one()
        amount = self.amount_to_transfer

        # ── Validations ───────────────────────────────────────────────────────
        if amount <= 0:
            raise exceptions.UserError("Le montant doit être supérieur à 0.")

        if amount > self.savings_balance:
            raise exceptions.UserError(
                f"Montant insuffisant dans l'épargne : solde disponible "
                f"{self.savings_balance:,.0f} {self.currency_id.name}, "
                f"montant demandé {amount:,.0f} {self.currency_id.name}."
            )

        if amount > self.installment_residual:
            raise exceptions.UserError(
                f"Montant supérieur au reste à payer sur cette échéance "
                f"({self.installment_residual:,.0f} {self.currency_id.name})."
            )

        savings_account = self.env['micro.transaction']._get_savings_account()
        transfer_journal = self.env['micro.transaction']._get_transfer_journal_id()
        partner = self.partner_id

        # ── Conversion devise ─────────────────────────────────────────────────
        company = self.env.company
        company_currency = company.currency_id
        tx_currency = self.currency_id or company_currency
        is_foreign = tx_currency != company_currency
        date = fields.Date.today()
        amount_company = (
            tx_currency._convert(amount, company_currency, company, date)
            if is_foreign else amount
        )

        # ── 1. Mettre à jour l'échéance crédit (sans créer de transaction caisse) ──
        self.credit_line_id.register_payment(amount, from_savings=True)

        # ── 2. Créer la transaction savings_withdrawal (audit trail) ──────────
        withdrawal_tx = self.env['micro.transaction'].create({
            'partner_id': partner.id,
            'amount': amount,
            'currency_id': tx_currency.id,
            'journal_id': transfer_journal.id,
            'transaction_type': 'savings_withdrawal',
            'cycle_id': self.cycle_id.id,
            'state': 'confirmed',
            'name': (
                self.env['ir.sequence'].next_by_code('micro.transaction') or 'Nouveau'
            ),
        })

        # ── 3. Écriture comptable : DR Compte Dépôts Membres / CR Créances Client ──
        #    Aucun mouvement de caisse — compensation interne épargne/crédit.
        receivable = partner.property_account_receivable_id
        if not receivable:
            raise exceptions.UserError(
                f"Aucun compte client (receivable) configuré pour {partner.name}."
            )

        dr_line = {
            'name': f"Retrait épargne — {partner.name}",
            'partner_id': partner.id,
            'account_id': savings_account.id,
            'debit': amount_company,
            'credit': 0.0,
        }
        cr_line = {
            'name': (
                f"Remboursement crédit (épargne) — {partner.name} "
                f"Éch. {self.installment_sequence}"
            ),
            'partner_id': partner.id,
            'account_id': receivable.id,
            'debit': 0.0,
            'credit': amount_company,
        }
        if is_foreign:
            dr_line.update({'amount_currency': amount, 'currency_id': tx_currency.id})
            cr_line.update({'amount_currency': -amount, 'currency_id': tx_currency.id})

        move_vals = {
            'journal_id': transfer_journal.id,
            'date': date,
            'ref': (
                f"Transfert épargne → crédit — {partner.name} "
                f"(Éch. {self.installment_sequence})"
            ),
            'line_ids': [(0, 0, dr_line), (0, 0, cr_line)],
        }
        if is_foreign:
            move_vals['currency_id'] = tx_currency.id

        move = self.env['account.move'].create(move_vals)
        move.action_post()
        withdrawal_tx.write({'move_id': move.id})

        return {'type': 'ir.actions.act_window_close'}
