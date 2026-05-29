# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        result = super().write(vals)
        if 'groups_id' in vals:
            self._sync_microflow_home_action()
        return result

    def _sync_microflow_home_action(self):
        """Fixe l'action d'accueil selon le groupe Microflow :
        - Manager → Tableau de Bord
        - Agent (non-manager) → Épargne
        - Retiré de tous les groupes → remet action_id à zéro (si elle pointait vers Microflow)
        """
        agent_group = self.env.ref('microflow.group_micro_flow_agent', raise_if_not_found=False)
        manager_group = self.env.ref('microflow.group_micro_flow_manager', raise_if_not_found=False)
        cycle_action = self.env.ref('microflow.action_micro_cycle', raise_if_not_found=False)
        dash_action = self.env.ref('microflow.action_manager_dashboard', raise_if_not_found=False)
        if not agent_group or not cycle_action:
            return
        mf_action_ids = {cycle_action.id} | ({dash_action.id} if dash_action else set())
        for user in self:
            if manager_group and dash_action and manager_group in user.groups_id:
                user.sudo().write({'action_id': dash_action.id})
            elif agent_group in user.groups_id:
                user.sudo().write({'action_id': cycle_action.id})
            elif user.action_id.id in mf_action_ids:
                user.sudo().write({'action_id': False})
