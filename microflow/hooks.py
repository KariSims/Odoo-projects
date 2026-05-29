# -*- coding: utf-8 -*-


def _apply_home_actions(env):
    """Fixe l'action d'accueil pour tous les utilisateurs Microflow existants.
    - Manager → Tableau de Bord
    - Agent (non-manager) → Épargne
    """
    agent_group = env.ref('microflow.group_micro_flow_agent', raise_if_not_found=False)
    manager_group = env.ref('microflow.group_micro_flow_manager', raise_if_not_found=False)
    cycle_action = env.ref('microflow.action_micro_cycle', raise_if_not_found=False)
    dash_action = env.ref('microflow.action_manager_dashboard', raise_if_not_found=False)
    if not agent_group or not cycle_action:
        return

    if manager_group and dash_action:
        managers = env['res.users'].search([
            ('groups_id', 'in', [manager_group.id]),
            ('active', 'in', [True, False]),
        ])
        managers.sudo().write({'action_id': dash_action.id})

    agents = env['res.users'].search([
        ('groups_id', 'in', [agent_group.id]),
        ('active', 'in', [True, False]),
    ])
    if manager_group:
        agents = agents.filtered(lambda u: manager_group not in u.groups_id)
    agents.sudo().write({'action_id': cycle_action.id})


def post_init_hook(env):
    _apply_home_actions(env)
