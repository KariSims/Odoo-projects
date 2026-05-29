from odoo import models, fields, api, exceptions
import logging
_logger = logging.getLogger(__name__)


class MicroCycle(models.Model):
    _name = 'micro.cycle'
    _description = 'Cycle d Epargne'

    partner_id = fields.Many2one('res.partner', string="Membre", required=True)
    agent_id = fields.Many2one('res.users', string="Agent responsable",
                               default=lambda self: self.env.user, readonly=True)
    duration_months = fields.Integer("Durée (Mois)", default=1)
    case_count = fields.Integer("Nombre de cases", required=True)

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    cycle_type = fields.Selection([
        ('fixed', 'Montant fixe'),
        ('variable', 'Montant variable'),
    ], string="Type d'épargne", default='fixed', required=True)
    amount_per_case = fields.Monetary(
        string="Montant par case",
        currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pre_active', 'En pré-collecte'),
        ('active', 'En cours'),
        ('closed', 'Terminé')
    ], default='draft')
    line_ids = fields.One2many(
        comodel_name='micro.cycle.line',
        inverse_name='cycle_id', string="Grille de Collecte")

    opening_fee = fields.Monetary(
        string="Frais d'adhésion",
        currency_field='currency_id', default=1000.0)
    commission_rate = fields.Float("Commission Collecte (%)", default=0.0)
    income_account_id = fields.Many2one('account.account', string="Compte de revenus")

    case_count_requested = fields.Integer(
        string="Correction demandée (cases)", default=0,
        help="Mis à jour par l'agent — en attente d'approbation Manager. 0 = aucune demande."
    )

    pending_uncheck_count = fields.Integer(
        compute='_compute_pending_uncheck_count',
    )
    pending_uncheck_line_ids = fields.One2many(
        comodel_name='micro.cycle.line',
        inverse_name='cycle_id',
        domain=[('uncheck_pending', '=', True)],
        string="Demandes d'annulation en attente",
    )

    amount_expected_total = fields.Monetary(
        string="Total attendu",
        currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    amount_collected = fields.Monetary(
        string="Collecté",
        currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    amount_remaining = fields.Monetary(
        string="Restant",
        currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    withdrawal_ids = fields.One2many(
        'micro.transaction', 'cycle_id',
        domain=[('transaction_type', '=', 'savings_withdrawal')],
        string="Retraits épargne",
    )
    amount_withdrawn = fields.Monetary(
        string="Retiré (transferts crédit)",
        currency_field='currency_id',
        compute='_compute_savings_balance', store=True,
    )
    savings_balance = fields.Monetary(
        string="Solde épargne disponible",
        currency_field='currency_id',
        compute='_compute_savings_balance', store=True,
        help="Montant collecté moins les retraits effectués (transferts vers crédit).",
    )

    amount_projected = fields.Monetary(
        string="Engagement prévisionnel",
        currency_field='currency_id',
        compute='_compute_amount_projected',
    )
    kanban_urgency_state = fields.Selection([
        ('correction_pending', 'Corrections de cases — À approuver'),
        ('uncheck_pending',    'Annulations de cases — À approuver'),
        ('to_process',         'Activation requise'),
        ('draft',              'Brouillon'),
        ('active',             'En cours'),
        ('closed',             'Terminé'),
    ], string="Rubrique Kanban",
       compute='_compute_kanban_urgency_state', store=True)

    @api.depends('line_ids.uncheck_pending')
    def _compute_pending_uncheck_count(self):
        for cycle in self:
            cycle.pending_uncheck_count = len(cycle.line_ids.filtered('uncheck_pending'))

    @api.depends('state', 'line_ids.uncheck_pending', 'case_count_requested')
    def _compute_kanban_urgency_state(self):
        for record in self:
            if record.state == 'pre_active':
                record.kanban_urgency_state = 'to_process'
            elif record.state == 'active':
                has_correction = record.case_count_requested != 0
                has_uncheck = any(l.uncheck_pending for l in record.line_ids)
                if has_correction:
                    # Correction prioritaire — l'annulation reste visible via badge dans la carte
                    record.kanban_urgency_state = 'correction_pending'
                elif has_uncheck:
                    record.kanban_urgency_state = 'uncheck_pending'
                else:
                    record.kanban_urgency_state = 'active'
            elif record.state == 'draft':
                record.kanban_urgency_state = 'draft'
            else:
                record.kanban_urgency_state = 'closed'

    @api.depends('withdrawal_ids.amount', 'withdrawal_ids.state', 'amount_collected')
    def _compute_savings_balance(self):
        for record in self:
            withdrawn = sum(
                t.amount for t in record.withdrawal_ids if t.state == 'confirmed'
            )
            record.amount_withdrawn = withdrawn
            record.savings_balance = record.amount_collected - withdrawn

    @api.depends('case_count', 'amount_per_case', 'cycle_type')
    def _compute_amount_projected(self):
        for record in self:
            if record.cycle_type == 'variable':
                record.amount_projected = 0
            else:
                record.amount_projected = record.case_count * record.amount_per_case

    @api.depends('line_ids.is_paid', 'line_ids.amount_expected', 'line_ids.amount_collected', 'cycle_type')
    def _compute_amounts(self):
        for record in self:
            if record.cycle_type == 'variable':
                collected = sum(l.amount_collected for l in record.line_ids if l.is_paid)
                record.amount_expected_total = 0
                record.amount_collected = collected
                record.amount_remaining = 0
            else:
                expected = sum(l.amount_expected for l in record.line_ids)
                collected = sum(l.amount_expected for l in record.line_ids if l.is_paid)
                record.amount_expected_total = expected
                record.amount_collected = collected
                record.amount_remaining = expected - collected

    @api.model
    def init(self):
        _logger.warning("MODEL micro.cycle loaded")

    def action_agent_start_collecting(self):
        """Étape 1 — Agent : crée les cases preview et passe en pré-collecte.
        Si appelé par un Manager, redirige directement vers l'activation complète."""
        if self.env.user.has_group('microflow.group_micro_flow_manager'):
            return self.action_activate()
        for record in self:
            if record.state != 'draft':
                raise exceptions.UserError(
                    "Ce cycle n'est pas en état Brouillon — impossible de démarrer la pré-collecte."
                )
            if record.cycle_type == 'fixed' and not record.amount_per_case:
                raise exceptions.UserError(
                    "Indiquez le montant par case pour un cycle à montant fixe."
                )
            draft_count = int(self.env['ir.config_parameter'].sudo()
                              .get_param('microflow.draft_case_count', 5))
            preview = min(draft_count, record.case_count)
            line_amount = record.amount_per_case if record.cycle_type == 'fixed' else 0.0
            for i in range(1, preview + 1):
                self.env['micro.cycle.line'].create({
                    'cycle_id': record.id,
                    'sequence': i,
                    'amount_expected': line_amount,
                })
            record.state = 'pre_active'

    def action_activate(self):
        """Étape 2 — Manager : crée toutes les cases restantes et active le cycle complet."""
        if not self.env.user.has_group('microflow.group_micro_flow_manager'):
            raise exceptions.UserError(
                "Seul un Manager peut activer un cycle d'épargne."
            )
        max_cycles = int(self.env['ir.config_parameter'].sudo().get_param('microflow.max_active_cycles', 1))
        for record in self:
            if record.state not in ('draft', 'pre_active'):
                raise exceptions.UserError(
                    f"Le cycle ne peut pas être activé depuis l'état « {record.state} »."
                )
            if record.cycle_type == 'fixed' and not record.amount_per_case:
                raise exceptions.UserError(
                    "Indiquez le montant par case pour un cycle à montant fixe."
                )
            active_count = self.search_count([
                ('partner_id', '=', record.partner_id.id),
                ('state', '=', 'active'),
                ('id', '!=', record.id),
            ])
            if active_count >= max_cycles:
                raise exceptions.UserError(
                    f"Ce membre a déjà {active_count} cycle(s) actif(s). Maximum autorisé : {max_cycles}."
                )

            existing = len(record.line_ids)
            if existing > record.case_count:
                excess = (
                    record.line_ids
                    .filtered(lambda l: not l.is_paid)
                    .sorted('sequence', reverse=True)
                )[:existing - record.case_count]
                excess.unlink()
                existing = len(record.line_ids)
            line_amount = record.amount_per_case if record.cycle_type == 'fixed' else 0.0
            for i in range(existing + 1, record.case_count + 1):
                self.env['micro.cycle.line'].create({
                    'cycle_id': record.id,
                    'sequence': i,
                    'amount_expected': line_amount,
                })

            if record.opening_fee > 0:
                journal_id = self.env['micro.transaction']._get_collection_journal_id()
                self.env['micro.transaction'].create({
                    'partner_id': record.partner_id.id,
                    'amount': record.opening_fee,
                    'currency_id': record.currency_id.id,
                    'journal_id': journal_id,
                    'transaction_type': 'fees',
                    'state': 'confirmed',
                    'name': f"Frais adhésion — {record.partner_id.name}"
                })

            record.state = 'active'

    def action_request_correction(self):
        self.ensure_one()
        new_count = self.case_count_requested
        if new_count <= 0:
            raise exceptions.UserError("Indiquez un nombre de cases valide (supérieur à 0).")
        current_count = len(self.line_ids)
        if new_count == current_count:
            raise exceptions.UserError(
                f"Le nombre demandé ({new_count}) est identique au nombre de cases actuelles."
            )
        paid_count = len(self.line_ids.filtered('is_paid'))
        if new_count < paid_count:
            raise exceptions.UserError(
                f"{paid_count} case(s) déjà collectée(s). "
                f"Le nombre corrigé ne peut pas être inférieur à {paid_count}."
            )

    def action_approve_correction(self):
        self.ensure_one()
        new_count = self.case_count_requested
        paid_count = len(self.line_ids.filtered('is_paid'))
        if new_count < paid_count:
            raise exceptions.UserError(
                f"Approbation impossible : {paid_count} case(s) déjà collectée(s). "
                f"Minimum autorisé : {paid_count}."
            )
        current_count = len(self.line_ids)
        if new_count > current_count:
            line_amount = self.amount_per_case if self.cycle_type == 'fixed' else 0.0
            for i in range(current_count + 1, new_count + 1):
                self.env['micro.cycle.line'].create({
                    'cycle_id': self.id,
                    'sequence': i,
                    'amount_expected': line_amount,
                })
        elif new_count < current_count:
            unpaid_desc = (
                self.line_ids
                .filtered(lambda l: not l.is_paid)
                .sorted('sequence', reverse=True)
            )
            unpaid_desc[:current_count - new_count].unlink()
        self.case_count = new_count
        self.case_count_requested = 0

    def action_reject_correction(self):
        self.ensure_one()
        self.case_count_requested = 0
