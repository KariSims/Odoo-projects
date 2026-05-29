from odoo.tests.common import TransactionCase


class TestResUsersHomeAction(TransactionCase):

    def setUp(self):
        super().setUp()
        self.agent_group = self.env.ref('microflow.group_micro_flow_agent')
        self.manager_group = self.env.ref('microflow.group_micro_flow_manager')
        self.cycle_action = self.env.ref('microflow.action_micro_cycle')
        self.dash_action = self.env.ref('microflow.action_manager_dashboard')

    def _make_user(self, name):
        return self.env['res.users'].create({
            'name': name,
            'login': f'{name.lower().replace(" ", "_")}@test.mf',
        })

    def test_agent_gets_cycle_action(self):
        """Ajouter un utilisateur au groupe agent → action_id = action_micro_cycle."""
        user = self._make_user('Agent Test')
        user.groups_id |= self.agent_group
        self.assertEqual(user.action_id.id, self.cycle_action.id)

    def test_manager_gets_dashboard_action(self):
        """Ajouter au groupe manager → action_id = action_manager_dashboard."""
        user = self._make_user('Manager Test')
        user.groups_id |= self.manager_group
        self.assertEqual(user.action_id.id, self.dash_action.id)

    def test_manager_overrides_agent(self):
        """Un agent promu manager reçoit l'action dashboard, pas cycle."""
        user = self._make_user('Promu Test')
        user.groups_id |= self.agent_group
        self.assertEqual(user.action_id.id, self.cycle_action.id)
        user.groups_id |= self.manager_group
        self.assertEqual(user.action_id.id, self.dash_action.id)

    def test_removed_from_groups_clears_action(self):
        """Retrait de tous les groupes Microflow → action_id remis à False."""
        user = self._make_user('Ex-Agent Test')
        user.groups_id |= self.agent_group
        self.assertEqual(user.action_id.id, self.cycle_action.id)
        user.groups_id -= self.agent_group
        self.assertFalse(user.action_id)

    def test_apply_home_actions_batch(self):
        """action_apply_home_actions() applique l'action à tous les utilisateurs Microflow."""
        agent = self._make_user('Batch Agent')
        manager = self._make_user('Batch Manager')
        agent.groups_id |= self.agent_group
        manager.groups_id |= self.manager_group
        # Réinitialiser manuellement pour simuler un état incorrect
        agent.sudo().write({'action_id': False})
        manager.sudo().write({'action_id': False})
        # Appel de la méthode de rattrapage depuis res.config.settings
        self.env['res.config.settings'].action_apply_home_actions()
        self.assertEqual(agent.action_id.id, self.cycle_action.id)
        self.assertEqual(manager.action_id.id, self.dash_action.id)
