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
        self.env['ir.config_parameter'].sudo().set_param('microflow.journal_id', self.journal.id)
        self.env['ir.config_parameter'].sudo().set_param('microflow.max_active_cycles', '1')
        self.env['ir.config_parameter'].sudo().set_param('microflow.draft_case_count', '3')
        # Groupe Manager pour les tests d'activation
        self.manager_group = self.env.ref('microflow.group_micro_flow_manager')
        self.env.user.groups_id |= self.manager_group

    def _make_cycle(self, opening_fee=0.0, case_count=5):
        return self.env['micro.cycle'].create({
            'partner_id': self.partner.id,
            'case_count': case_count,
            'amount_per_case': 1000.0,
            'opening_fee': opening_fee,
        })

    def test_action_activate_creates_lines(self):
        """Manager active depuis draft → N lignes au total, state=active."""
        cycle = self._make_cycle(case_count=5)
        self.assertEqual(len(cycle.line_ids), 0)  # pas d'auto-création
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

    # ── Tests flux Agent (pré-collecte) + Manager (activation complète) ─────

    def test_agent_start_collecting_creates_preview(self):
        """action_agent_start_collecting() crée min(draft_case_count, case_count) cases → pre_active."""
        cycle = self._make_cycle(case_count=5)
        self.assertEqual(len(cycle.line_ids), 0)
        self.env.user.groups_id -= self.manager_group  # simule un agent pur
        cycle.action_agent_start_collecting()
        self.env.user.groups_id |= self.manager_group
        # draft_case_count=3, case_count=5 → 3 cases preview
        self.assertEqual(len(cycle.line_ids), 3)
        self.assertEqual(cycle.state, 'pre_active')

    def test_agent_start_collecting_cap(self):
        """Si case_count < draft_case_count, le preview est capé à case_count."""
        cycle = self._make_cycle(case_count=2)
        self.env.user.groups_id -= self.manager_group
        cycle.action_agent_start_collecting()
        self.env.user.groups_id |= self.manager_group
        self.assertEqual(len(cycle.line_ids), 2)
        self.assertEqual(cycle.state, 'pre_active')

    def test_agent_cannot_full_activate(self):
        """Un agent ne peut pas appeler action_activate() (activation Manager uniquement)."""
        cycle = self._make_cycle(case_count=5)
        self.env.user.groups_id -= self.manager_group
        with self.assertRaises(Exception):
            cycle.action_activate()
        self.env.user.groups_id |= self.manager_group

    def test_manager_activates_remaining_cases_after_agent(self):
        """Manager active le cycle complet après pré-activation Agent — cases sans doublons."""
        cycle = self._make_cycle(case_count=5)
        # Étape 1 : agent crée 3 cases preview
        self.env.user.groups_id -= self.manager_group
        cycle.action_agent_start_collecting()
        self.env.user.groups_id |= self.manager_group
        preview_ids = cycle.line_ids.ids
        # Étape 2 : Manager crée les cases restantes
        cycle.action_activate()
        for pid in preview_ids:
            self.assertIn(pid, cycle.line_ids.ids)
        self.assertEqual(len(cycle.line_ids), 5)
        sequences = cycle.line_ids.mapped('sequence')
        self.assertEqual(sorted(sequences), [1, 2, 3, 4, 5])

    def test_manager_redirected_by_agent_button(self):
        """action_agent_start_collecting() appelé par Manager → redirige vers activation complète."""
        cycle = self._make_cycle(case_count=5)
        # Manager appelle le bouton agent → doit activer directement
        cycle.action_agent_start_collecting()
        self.assertEqual(len(cycle.line_ids), 5)
        self.assertEqual(cycle.state, 'active')

    # ── Tests montants cumulés (A-1) ──────────────────────────────────────────

    def test_amounts_all_unpaid(self):
        """Avant toute collecte : collecté=0, total=N*montant, restant=total."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=4)
        cycle.action_activate()
        self.assertEqual(cycle.amount_collected, 0.0)
        self.assertEqual(cycle.amount_expected_total, 4000.0)
        self.assertEqual(cycle.amount_remaining, 4000.0)

    def test_amounts_partial_paid(self):
        """2 cases payées sur 4 → collecté=2000, restant=2000."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=4)
        cycle.action_activate()
        lines = cycle.line_ids.sorted('sequence')
        lines[0].register_collection()
        lines[1].register_collection()
        self.assertEqual(cycle.amount_collected, 2000.0)
        self.assertEqual(cycle.amount_expected_total, 4000.0)
        self.assertEqual(cycle.amount_remaining, 2000.0)

    def test_amounts_all_paid(self):
        """Toutes les cases payées → restant=0, collecté=total."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=3)
        cycle.action_activate()
        for line in cycle.line_ids:
            line.register_collection()
        self.assertEqual(cycle.amount_collected, 3000.0)
        self.assertEqual(cycle.amount_remaining, 0.0)

    # ── Tests unregister_collection ───────────────────────────────────────────

    def test_unregister_basic(self):
        """unregister_collection remet is_paid=False."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=3)
        cycle.action_activate()
        line = cycle.line_ids.sorted('sequence')[0]
        line.register_collection()
        self.assertTrue(line.is_paid)
        line.unregister_collection()
        self.assertFalse(line.is_paid)

    def test_unregister_confirmed_blocked(self):
        """unregister_collection bloque si la transaction liée est confirmée."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=3)
        cycle.action_activate()
        line = cycle.line_ids.sorted('sequence')[0]
        line.register_collection()
        # Confirmer manuellement la transaction liée
        tx = self.env['micro.transaction'].search([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'savings'),
        ], limit=1)
        tx.write({'state': 'confirmed'})
        with self.assertRaises(UserError):
            line.unregister_collection()

    def test_unregister_not_today_blocked(self):
        """unregister_collection bloque si la collecte ne date pas d'aujourd'hui."""
        cycle = self._make_cycle(opening_fee=0.0, case_count=3)
        cycle.action_activate()
        line = cycle.line_ids.sorted('sequence')[0]
        line.register_collection()
        # Forcer une date passée sur la transaction
        tx = self.env['micro.transaction'].search([
            ('partner_id', '=', self.partner.id),
            ('transaction_type', '=', 'savings'),
        ], limit=1)
        tx.write({'date': date(2000, 1, 1)})
        with self.assertRaises(UserError):
            line.unregister_collection()

    # ── Tests collection_order ────────────────────────────────────────────────

    def test_collection_order_increments(self):
        """Les rangs s'incrémentent selon l'ordre de collecte, pas la séquence."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        lines = cycle.line_ids.sorted('sequence')
        lines[2].register_collection()  # case 3 en premier
        lines[0].register_collection()  # case 1 en deuxième
        self.assertEqual(lines[2].collection_order, 1)
        self.assertEqual(lines[0].collection_order, 2)

    def test_collection_order_reset_on_unregister(self):
        """unregister_collection remet collection_order à 0."""
        cycle = self._make_cycle(case_count=3)
        cycle.action_activate()
        line = cycle.line_ids.sorted('sequence')[0]
        line.register_collection()
        self.assertEqual(line.collection_order, 1)
        line.unregister_collection()
        self.assertEqual(line.collection_order, 0)

    def test_collection_order_no_duplicate(self):
        """Trois collectes successives → rangs 1, 2, 3 tous distincts."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        lines = cycle.line_ids.sorted('sequence')
        for line in lines[:3]:
            line.register_collection()
        orders = [l.collection_order for l in lines[:3]]
        self.assertEqual(sorted(orders), [1, 2, 3])
        self.assertEqual(len(set(orders)), 3)

    # ── Tests correction dette technique 6.6 — sens comptable épargne ─────────

    def _setup_savings_account(self):
        """Crée un compte de passif courant et le configure comme compte dépôts membres."""
        account = self.env['account.account'].create({
            'name': 'Dépôts Membres Test',
            'code': 'MF-DEP-9999',
            'account_type': 'liability_current',
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'microflow.savings_account_id', account.id
        )
        return account

    def _make_savings_tx(self, amount=1000.0):
        """Crée une transaction épargne draft is_verified=True, prête pour confirmation."""
        return self.env['micro.transaction'].create({
            'partner_id': self.partner.id,
            'amount': amount,
            'journal_id': self.journal.id,
            'transaction_type': 'savings',
            'state': 'draft',
            'is_verified': True,
        })

    def test_savings_confirm_debits_cash(self):
        """Confirmation épargne → la caisse est débitée (cash entre dans l'institution)."""
        savings_account = self._setup_savings_account()
        tx = self._make_savings_tx(amount=5000.0)
        tx.action_confirm_payment()
        self.assertEqual(tx.state, 'confirmed')
        cash_lines = tx.move_id.line_ids.filtered(
            lambda l: l.account_id == self.journal.default_account_id
        )
        self.assertTrue(cash_lines, "La ligne de caisse doit exister dans l'écriture")
        self.assertEqual(cash_lines[0].debit, 5000.0, "La caisse doit être débitée (cash reçu)")
        self.assertEqual(cash_lines[0].credit, 0.0)

    def test_savings_confirm_credits_savings_account(self):
        """Confirmation épargne → le compte dépôts membres est crédité (passif augmente)."""
        savings_account = self._setup_savings_account()
        tx = self._make_savings_tx(amount=5000.0)
        tx.action_confirm_payment()
        deposit_lines = tx.move_id.line_ids.filtered(
            lambda l: l.account_id == savings_account
        )
        self.assertTrue(deposit_lines, "La ligne dépôts membres doit exister dans l'écriture")
        self.assertEqual(deposit_lines[0].credit, 5000.0, "Le compte dépôts doit être crédité")
        self.assertEqual(deposit_lines[0].debit, 0.0)

    def test_bulk_confirm_savings_direction(self):
        """action_bulk_confirm : même sens correct (DR caisse / CR dépôts membres)."""
        savings_account = self._setup_savings_account()
        tx1 = self._make_savings_tx(amount=2000.0)
        tx2 = self._make_savings_tx(amount=3000.0)
        txns = tx1 | tx2
        txns.action_bulk_confirm()
        self.assertEqual(tx1.state, 'confirmed')
        move = tx1.move_id
        cash_lines = move.line_ids.filtered(
            lambda l: l.account_id == self.journal.default_account_id
        )
        self.assertEqual(cash_lines[0].debit, 5000.0, "Caisse débitée du total (2000+3000)")
        deposit_lines = move.line_ids.filtered(
            lambda l: l.account_id == savings_account
        )
        total_credit = sum(deposit_lines.mapped('credit'))
        self.assertEqual(total_credit, 5000.0, "Dépôts membres crédités du total")

    def test_confirm_without_savings_account_raises(self):
        """Confirmation épargne sans compte configuré → UserError explicite."""
        self.env['ir.config_parameter'].sudo().set_param('microflow.savings_account_id', '0')
        tx = self._make_savings_tx()
        with self.assertRaises(Exception):
            tx.action_confirm_payment()

    # ── Tests cycles à montant variable ──────────────────────────────────────

    def _make_variable_cycle(self, case_count=5):
        return self.env['micro.cycle'].create({
            'partner_id': self.partner.id,
            'case_count': case_count,
            'cycle_type': 'variable',
            'opening_fee': 0.0,
        })

    def test_variable_cycle_activate_lines_have_zero_amount(self):
        """Activation d'un cycle variable → cases créées avec amount_expected=0."""
        cycle = self._make_variable_cycle(case_count=4)
        cycle.action_activate()
        self.assertEqual(len(cycle.line_ids), 4)
        for line in cycle.line_ids:
            self.assertEqual(line.amount_expected, 0.0)

    def test_variable_cycle_register_collection_with_amount(self):
        """register_collection(amount=X) sur cycle variable → is_paid=True, amount_collected=X."""
        cycle = self._make_variable_cycle(case_count=3)
        cycle.action_activate()
        line = cycle.line_ids.sorted('sequence')[0]
        line.register_collection(amount=3500.0)
        self.assertTrue(line.is_paid)
        self.assertEqual(line.amount_collected, 3500.0)

    def test_variable_cycle_register_collection_without_amount_raises(self):
        """register_collection() sans montant sur cycle variable → UserError."""
        cycle = self._make_variable_cycle(case_count=3)
        cycle.action_activate()
        line = cycle.line_ids.sorted('sequence')[0]
        with self.assertRaises(Exception):
            line.register_collection()

    def test_variable_cycle_amounts_computed(self):
        """amount_collected du cycle = somme des montants réellement collectés."""
        cycle = self._make_variable_cycle(case_count=3)
        cycle.action_activate()
        lines = cycle.line_ids.sorted('sequence')
        lines[0].register_collection(amount=2000.0)
        lines[1].register_collection(amount=3500.0)
        self.assertEqual(cycle.amount_collected, 5500.0)
        self.assertEqual(cycle.amount_expected_total, 0.0)
        self.assertEqual(cycle.amount_remaining, 0.0)

    def test_variable_cycle_unregister_resets_amount(self):
        """unregister_collection sur cycle variable remet amount_collected à 0."""
        cycle = self._make_variable_cycle(case_count=3)
        cycle.action_activate()
        line = cycle.line_ids.sorted('sequence')[0]
        line.register_collection(amount=2500.0)
        self.assertEqual(line.amount_collected, 2500.0)
        line.unregister_collection()
        self.assertEqual(line.amount_collected, 0.0)
        self.assertFalse(line.is_paid)

    def test_variable_cycle_amount_per_case_not_required(self):
        """Créer un cycle variable sans amount_per_case ne doit pas échouer à l'activation."""
        cycle = self._make_variable_cycle(case_count=3)
        try:
            cycle.action_activate()
            activated = True
        except Exception:
            activated = False
        self.assertTrue(activated, "L'activation d'un cycle variable sans montant par case doit réussir")

    # ── Correction de cases ──────────────────────────────────────────────────

    def test_request_correction_invalid_zero_raises(self):
        """case_count_requested == 0 → UserError."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        cycle.case_count_requested = 0
        with self.assertRaises(Exception):
            cycle.action_request_correction()

    def test_request_correction_same_count_raises(self):
        """Demander le même nombre de cases que l'actuel → UserError."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        cycle.case_count_requested = 5
        with self.assertRaises(Exception):
            cycle.action_request_correction()

    def test_request_correction_below_paid_raises(self):
        """Demander moins de cases que les cases déjà collectées → UserError."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        lines = cycle.line_ids.sorted('sequence')
        lines[0].register_collection()
        lines[1].register_collection()
        cycle.case_count_requested = 1
        with self.assertRaises(Exception):
            cycle.action_request_correction()

    def test_approve_correction_adds_lines(self):
        """Approbation avec new_count > current → les cases supplémentaires sont créées."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        self.assertEqual(len(cycle.line_ids), 5)
        cycle.case_count_requested = 8
        cycle.action_approve_correction()
        self.assertEqual(len(cycle.line_ids), 8)
        self.assertEqual(cycle.case_count, 8)
        self.assertEqual(cycle.case_count_requested, 0)

    def test_approve_correction_removes_unpaid_lines(self):
        """Approbation avec new_count < current → les cases non-payées sont supprimées."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        lines = cycle.line_ids.sorted('sequence')
        lines[0].register_collection()
        cycle.case_count_requested = 3
        cycle.action_approve_correction()
        self.assertEqual(len(cycle.line_ids), 3)
        self.assertEqual(cycle.case_count, 3)

    def test_reject_correction_resets_requested(self):
        """Rejet de correction → case_count_requested = 0, cases inchangées."""
        cycle = self._make_cycle(case_count=5)
        cycle.action_activate()
        cycle.case_count_requested = 8
        cycle.action_reject_correction()
        self.assertEqual(cycle.case_count_requested, 0)
        self.assertEqual(len(cycle.line_ids), 5)

    def test_credit_repayment_confirm_unchanged(self):
        """Remboursement crédit : sens inchangé (DR caisse / CR receivable partenaire)."""
        # credit_repayment n'utilise pas le compte dépôts — pas besoin de le configurer
        tx = self.env['micro.transaction'].create({
            'partner_id': self.partner.id,
            'amount': 4000.0,
            'journal_id': self.journal.id,
            'transaction_type': 'credit_repayment',
            'state': 'draft',
            'is_verified': True,
        })
        tx.action_confirm_payment()
        self.assertEqual(tx.state, 'confirmed')
        receivable = self.partner.property_account_receivable_id
        receivable_lines = tx.move_id.line_ids.filtered(
            lambda l: l.account_id == receivable
        )
        self.assertTrue(receivable_lines, "Le compte client doit être utilisé pour un remboursement")
        self.assertEqual(receivable_lines[0].credit, 4000.0)
        cash_lines = tx.move_id.line_ids.filtered(
            lambda l: l.account_id == self.journal.default_account_id
        )
        self.assertEqual(cash_lines[0].debit, 4000.0, "La caisse doit être débitée")
