from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date


class TestMicroCredit(TransactionCase):

    def setUp(self):
        super().setUp()
        self.zone = self.env['micro.zone'].create({'name': 'Zone Test', 'code': 'TST'})
        self.partner = self.env['res.partner'].create({
            'name': 'Emprunteur Test',
            'birthdate': date(1985, 3, 20),
            'zone_id': self.zone.id,
            'entity_type': 'individual',
            'member_type': 'saver',
        })
        self.journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        self.env['ir.config_parameter'].sudo().set_param('microflow.journal_id', self.journal.id)

    def _make_credit(self, capital=10000.0, rate=10.0, installments=5, max_partial=3):
        return self.env['micro.credit'].create({
            'partner_id': self.partner.id,
            'capital': capital,
            'interest_rate': rate,
            'installment_count': installments,
            'max_partial_payments': max_partial,
        })

    # ── compute_installments ──────────────────────────────────────────────────

    def test_compute_installments(self):
        """N échéances créées, total = capital*(1+rate/100)."""
        credit = self._make_credit(capital=10000.0, rate=10.0, installments=5)
        credit.compute_installments()
        self.assertEqual(len(credit.line_ids), 5)
        total = sum(credit.line_ids.mapped('amount_due'))
        self.assertAlmostEqual(total, 11000.0, places=2)

    def test_compute_installments_idempotent(self):
        """Appel double → toujours N lignes, pas 2N."""
        credit = self._make_credit(installments=4)
        credit.compute_installments()
        credit.compute_installments()  # doit être ignoré
        self.assertEqual(len(credit.line_ids), 4)

    # ── register_payment ─────────────────────────────────────────────────────

    def _get_first_line(self, credit):
        credit.compute_installments()
        return credit.line_ids[0]

    def test_register_payment_valid(self):
        """Paiement partiel valide → amount_paid mis à jour."""
        credit = self._make_credit(capital=10000.0, rate=0.0, installments=1)
        line = self._get_first_line(credit)
        line.register_payment(3000.0)
        self.assertAlmostEqual(line.amount_paid, 3000.0, places=2)
        self.assertEqual(line.payment_count, 1)

    def test_register_payment_over_limit(self):
        """N+1 versements au-delà de max_partial_payments → UserError."""
        credit = self._make_credit(capital=10000.0, rate=0.0, installments=1, max_partial=2)
        line = self._get_first_line(credit)
        line.register_payment(1000.0)
        line.register_payment(1000.0)
        with self.assertRaises(UserError):
            line.register_payment(1000.0)

    def test_register_payment_invalid_amount(self):
        """Montant > résiduel → UserError."""
        credit = self._make_credit(capital=5000.0, rate=0.0, installments=1)
        line = self._get_first_line(credit)
        with self.assertRaises(UserError):
            line.register_payment(9999.0)

    def test_register_payment_zero_rejected(self):
        """Montant <= 0 → UserError."""
        credit = self._make_credit(capital=5000.0, rate=0.0, installments=1)
        line = self._get_first_line(credit)
        with self.assertRaises(UserError):
            line.register_payment(0.0)

    def test_no_double_counting_via_wizard(self):
        """Wizard appelle register_payment() une seule fois → amount_paid = montant versé, pas le double."""
        credit = self._make_credit(capital=6000.0, rate=0.0, installments=1)
        line = self._get_first_line(credit)
        wizard = self.env['credit.payment.wizard'].create({
            'line_id': line.id,
            'amount_to_pay': 1500.0,
        })
        wizard.action_validate_payment()
        self.assertAlmostEqual(line.amount_paid, 1500.0, places=2,
                               msg="amount_paid doit être 1500, pas 3000 (double-comptage)")
        self.assertEqual(line.payment_count, 1)

    def test_amount_residual_computed(self):
        """amount_residual = amount_due - amount_paid après paiement."""
        credit = self._make_credit(capital=4000.0, rate=0.0, installments=1)
        line = self._get_first_line(credit)
        line.register_payment(1000.0)
        self.assertAlmostEqual(line.amount_residual, 3000.0, places=2)
