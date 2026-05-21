from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date


class TestMicroCycle(TransactionCase):

    def setUp(self):
        super().setUp()
        self.zone = self.env['micro.zone'].create({'name': 'Zone Test', 'code': 'TST'})
        self.partner = self.env['res.partner'].create({
            'name': 'Membre Test',
            'birthdate': date(1990, 1, 1),
            'zone_id': self.zone.id,
            'entity_type': 'individual',
            'member_type': 'saver',
        })
        self.journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        # Configure le journal dans les paramètres système
        self.env['ir.config_parameter'].sudo().set_param('microflow.journal_id', self.journal.id)
        self.env['ir.config_parameter'].sudo().set_param('microflow.max_active_cycles', '1')

    def _make_cycle(self, opening_fee=0.0, case_count=5):
        return self.env['micro.cycle'].create({
            'partner_id': self.partner.id,
            'case_count': case_count,
            'amount_per_case': 1000.0,
            'opening_fee': opening_fee,
        })

    def test_action_activate_creates_lines(self):
        """Activation → N lignes créées."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        self.assertEqual(len(cycle.line_ids), 5)
        self.assertEqual(cycle.state, 'active')

    def test_action_activate_fees(self):
        """opening_fee > 0 → 1 transaction fees créée à l'activation."""
        cycle = self._make_cycle(opening_fee=500.0, case_count=3)
        before = self.env['micro.transaction'].search_count([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'fees'),
        ])
        cycle.action_activate()
        after = self.env['micro.transaction'].search_count([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'fees'),
        ])
        self.assertEqual(after, before + 1, "Exactement 1 transaction de frais doit être créée")

    def test_action_activate_no_fees(self):
        """opening_fee == 0 → aucune transaction fees créée."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=3)
        before = self.env['micro.transaction'].search_count([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'fees'),
        ])
        cycle.action_activate()
        after = self.env['micro.transaction'].search_count([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'fees'),
        ])
        self.assertEqual(after, before, "Aucune transaction de frais si opening_fee=0")

    def test_max_active_cycles_enforced(self):
        """Le deuxième cycle doit échouer si max_active_cycles=1."""
        self.env['ir.config_parameter'].sudo().set_param('microflow.max_active_cycles', '1')
        c1 = self._make_cycle(opening_fee=0.0)
        c1.action_activate()
        c2 = self._make_cycle(opening_fee=0.0)
        with self.assertRaises(UserError):
            c2.action_activate()

    def test_register_collection_marks_paid(self):
        """register_collection() coche la case et crée une transaction."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=3)
        cycle.action_activate()
        line = cycle.line_ids[0]
        self.assertFalse(line.is_paid)
        line.register_collection()
        self.assertTrue(line.is_paid)

    def test_register_collection_no_double(self):
        """Appel double sur une case déjà payée → pas de deuxième transaction."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=3)
        cycle.action_activate()
        line = cycle.line_ids[0]
        line.register_collection()
        count_after_first = self.env['micro.transaction'].search_count([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'savings'),
        ])
        line.register_collection()  # second call — already paid, should be ignored
        count_after_second = self.env['micro.transaction'].search_count([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'savings'),
        ])
        self.assertEqual(count_after_first, count_after_second)
