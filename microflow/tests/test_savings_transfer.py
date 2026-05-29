from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date


class TestSavingsTransfer(TransactionCase):
    """Tests pour la feature : transfert épargne → crédit (smart button + wizard)."""

    def setUp(self):
        super().setUp()
        self.zone = self.env['micro.zone'].create({'name': 'Zone ST', 'code': 'ST'})
        self.partner = self.env['res.partner'].create({
            'name': 'Membre Transfert Test',
            'birthdate': date(1990, 5, 10),
            'zone_id': self.zone.id,
            'entity_type': 'individual',
            'member_type': 'saver',
        })
        self.cash_journal = self.env['account.journal'].search(
            [('type', '=', 'cash')], limit=1)
        self.env['ir.config_parameter'].sudo().set_param(
            'microflow.journal_id', self.cash_journal.id)
        self.env['ir.config_parameter'].sudo().set_param(
            'microflow.max_active_cycles', '2')  # autoriser 2 cycles pour tester multi-sélection

        # Groupe Manager
        self.manager_group = self.env.ref('microflow.group_micro_flow_manager')
        self.env.user.groups_id |= self.manager_group

        # Compte épargne (passif)
        self.savings_account = self.env['account.account'].create({
            'name': 'Dépôts Membres ST',
            'code': 'MF-ST-9998',
            'account_type': 'liability_current',
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'microflow.savings_account_id', self.savings_account.id)

        # Journal général (Opérations diverses)
        self.general_journal = self.env['account.journal'].search(
            [('type', '=', 'general')], limit=1)
        if not self.general_journal:
            self.general_journal = self.env['account.journal'].create({
                'name': 'Opérations diverses Test',
                'type': 'general',
                'code': 'MISC',
            })

    def _make_active_cycle(self, case_count=5, amount_per_case=1000.0):
        """Crée un cycle épargne actif avec N cases."""
        cycle = self.env['micro.cycle'].create({
            'partner_id': self.partner.id,
            'case_count': case_count,
            'amount_per_case': amount_per_case,
            'opening_fee': 0.0,
        })
        cycle.action_activate()
        return cycle

    def _collect_cases(self, cycle, count):
        """Collecte les N premières cases d'un cycle."""
        lines = cycle.line_ids.sorted('sequence')
        for line in lines[:count]:
            line.register_collection()
        return lines[:count]

    def _make_active_credit(self, capital=10000.0, installments=3, max_partial=5):
        """Crée un crédit actif avec un échéancier généré."""
        credit = self.env['micro.credit'].create({
            'partner_id': self.partner.id,
            'capital': capital,
            'interest_rate': 0.0,
            'installment_count': installments,
            'max_partial_payments': max_partial,
        })
        credit.action_submit()
        credit.action_approve()
        return credit

    # ── Tests smart button (partner_savings_total) ────────────────────────────

    def test_smart_button_active_cycle(self):
        """Membre avec cycle actif + cases collectées → partner_savings_total > 0."""
        cycle = self._make_active_cycle(case_count=3, amount_per_case=2000.0)
        self._collect_cases(cycle, 2)
        credit = self._make_active_credit()
        self.assertEqual(credit.partner_savings_total, 4000.0)
        self.assertEqual(credit.partner_savings_cycle_count, 1)

    def test_smart_button_no_cycle(self):
        """Membre sans cycle → partner_savings_total == 0."""
        credit = self._make_active_credit()
        self.assertEqual(credit.partner_savings_total, 0.0)
        self.assertEqual(credit.partner_savings_cycle_count, 0)

    def test_smart_button_draft_cycle_excluded(self):
        """Cycle en brouillon (non activé) ne compte pas."""
        self.env['micro.cycle'].create({
            'partner_id': self.partner.id,
            'case_count': 3,
            'amount_per_case': 1000.0,
        })
        credit = self._make_active_credit()
        self.assertEqual(credit.partner_savings_total, 0.0)

    # ── Tests savings_balance sur micro.cycle ────────────────────────────────

    def test_savings_balance_no_withdrawals(self):
        """Sans retrait : savings_balance == amount_collected."""
        cycle = self._make_active_cycle(case_count=4, amount_per_case=1000.0)
        self._collect_cases(cycle, 3)
        self.assertEqual(cycle.savings_balance, 3000.0)
        self.assertEqual(cycle.amount_withdrawn, 0.0)

    def test_savings_balance_after_withdrawal(self):
        """Après un retrait confirmé : savings_balance = collected - withdrawn."""
        cycle = self._make_active_cycle(case_count=4, amount_per_case=1000.0)
        self._collect_cases(cycle, 4)
        # Créer manuellement une transaction de retrait confirmée
        self.env['micro.transaction'].create({
            'partner_id': self.partner.id,
            'amount': 1500.0,
            'journal_id': self.general_journal.id,
            'transaction_type': 'savings_withdrawal',
            'cycle_id': cycle.id,
            'state': 'confirmed',
        })
        cycle._compute_savings_balance()
        self.assertEqual(cycle.amount_withdrawn, 1500.0)
        self.assertEqual(cycle.savings_balance, 2500.0)

    # ── Test register_payment avec from_savings=True ──────────────────────────

    def test_register_payment_from_savings_no_transaction(self):
        """from_savings=True → pas de transaction credit_repayment créée."""
        credit = self._make_active_credit(capital=6000.0, installments=1)
        line = credit.line_ids[0]
        before = self.env['micro.transaction'].search_count([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'credit_repayment'),
        ])
        line.register_payment(2000.0, from_savings=True)
        after = self.env['micro.transaction'].search_count([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'credit_repayment'),
        ])
        self.assertEqual(after, before, "Aucune transaction credit_repayment ne doit être créée")
        self.assertEqual(line.amount_paid, 2000.0)
        self.assertEqual(line.payment_count, 1)

    # ── Tests wizard SavingsRepaymentWizard ──────────────────────────────────

    def _run_wizard(self, credit_line, cycle, amount):
        wizard = self.env['savings.repayment.wizard'].create({
            'credit_line_id': credit_line.id,
            'cycle_id': cycle.id,
            'amount_to_transfer': amount,
        })
        return wizard.action_validate()

    def test_transfer_happy_path(self):
        """Transfert valide : credit_line.amount_paid augmente, savings_balance diminue."""
        cycle = self._make_active_cycle(case_count=5, amount_per_case=1000.0)
        self._collect_cases(cycle, 4)
        credit = self._make_active_credit(capital=3000.0, installments=1)
        line = credit.line_ids[0]
        initial_residual = line.amount_residual
        self._run_wizard(line, cycle, 1000.0)
        line._compute_residual()
        cycle._compute_savings_balance()
        self.assertEqual(line.amount_paid, 1000.0)
        self.assertEqual(line.amount_residual, initial_residual - 1000.0)
        self.assertEqual(cycle.savings_balance, 3000.0)
        self.assertEqual(cycle.amount_withdrawn, 1000.0)

    def test_transfer_amount_exceeds_savings(self):
        """Montant > savings_balance → UserError."""
        cycle = self._make_active_cycle(case_count=2, amount_per_case=1000.0)
        self._collect_cases(cycle, 1)
        credit = self._make_active_credit(capital=9000.0, installments=1)
        line = credit.line_ids[0]
        with self.assertRaises(UserError):
            self._run_wizard(line, cycle, 2000.0)

    def test_transfer_amount_exceeds_residual(self):
        """Montant > montant résiduel de l'échéance → UserError."""
        cycle = self._make_active_cycle(case_count=5, amount_per_case=5000.0)
        self._collect_cases(cycle, 5)
        credit = self._make_active_credit(capital=1000.0, installments=1)
        line = credit.line_ids[0]
        with self.assertRaises(UserError):
            self._run_wizard(line, cycle, 2000.0)

    def test_transfer_max_partial_payments(self):
        """payment_count atteint max_partial_payments → UserError."""
        cycle = self._make_active_cycle(case_count=5, amount_per_case=2000.0)
        self._collect_cases(cycle, 5)
        credit = self._make_active_credit(capital=9000.0, installments=1, max_partial=1)
        line = credit.line_ids[0]
        line.register_payment(1000.0, from_savings=True)
        with self.assertRaises(UserError):
            self._run_wizard(line, cycle, 500.0)

    def test_transfer_journal_entry(self):
        """L'écriture comptable débite savings_account et crédite receivable."""
        cycle = self._make_active_cycle(case_count=5, amount_per_case=1000.0)
        self._collect_cases(cycle, 5)
        credit = self._make_active_credit(capital=3000.0, installments=1)
        line = credit.line_ids[0]
        self._run_wizard(line, cycle, 1500.0)
        withdrawal_tx = self.env['micro.transaction'].search([
            ('cycle_id', '=', cycle.id),
            ('transaction_type', '=', 'savings_withdrawal'),
        ], limit=1)
        self.assertTrue(withdrawal_tx, "La transaction savings_withdrawal doit exister")
        self.assertTrue(withdrawal_tx.move_id, "L'écriture comptable doit être liée")
        move = withdrawal_tx.move_id
        savings_lines = move.line_ids.filtered(
            lambda l: l.account_id == self.savings_account)
        self.assertTrue(savings_lines, "Ligne débit compte dépôts membres manquante")
        self.assertEqual(savings_lines[0].debit, 1500.0)
        receivable = self.partner.property_account_receivable_id
        receivable_lines = move.line_ids.filtered(
            lambda l: l.account_id == receivable)
        self.assertTrue(receivable_lines, "Ligne crédit créances client manquante")
        self.assertEqual(receivable_lines[0].credit, 1500.0)

    def test_transfer_savings_account_missing(self):
        """savings_account non configuré → UserError."""
        self.env['ir.config_parameter'].sudo().set_param(
            'microflow.savings_account_id', '0')
        cycle = self._make_active_cycle(case_count=3, amount_per_case=1000.0)
        self._collect_cases(cycle, 3)
        credit = self._make_active_credit(capital=2000.0, installments=1)
        line = credit.line_ids[0]
        with self.assertRaises(Exception):
            self._run_wizard(line, cycle, 500.0)

    def test_transfer_cycle_selection(self):
        """Avec 2 cycles actifs, le wizard prélève uniquement sur le cycle sélectionné."""
        cycle1 = self._make_active_cycle(case_count=3, amount_per_case=1000.0)
        self._collect_cases(cycle1, 3)
        cycle2 = self._make_active_cycle(case_count=3, amount_per_case=2000.0)
        self._collect_cases(cycle2, 2)
        credit = self._make_active_credit(capital=5000.0, installments=1)
        line = credit.line_ids[0]
        self._run_wizard(line, cycle1, 1000.0)
        cycle1._compute_savings_balance()
        cycle2._compute_savings_balance()
        self.assertEqual(cycle1.savings_balance, 2000.0, "cycle1 réduit de 1000")
        self.assertEqual(cycle2.savings_balance, 4000.0, "cycle2 inchangé")
