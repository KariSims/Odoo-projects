from odoo import models, fields, exceptions
import logging
_logger = logging.getLogger(__name__)


class MicroCycleLine(models.Model):
    _name = 'micro.cycle.line'
    _order = 'sequence'

    cycle_id = fields.Many2one('micro.cycle', string="Cycle Parent", ondelete='cascade')
    sequence = fields.Integer("N° Case")
    currency_id = fields.Many2one('res.currency', related='cycle_id.currency_id')
    amount_expected = fields.Monetary(string="Montant attendu", currency_field='currency_id')
    amount_collected = fields.Monetary(string="Montant collecté", currency_field='currency_id', default=0.0)
    is_paid = fields.Boolean("Coché", default=False)
    # Rang chronologique de collecte dans le cycle (0 = non payé)
    collection_order = fields.Integer("Rang de collecte", default=0)

    # Annulation en attente d'approbation Manager (demande tardive > 2 min)
    uncheck_pending = fields.Boolean("Annulation en attente", default=False)
    uncheck_requested_at = fields.Datetime("Demandé le", readonly=True)
    uncheck_requested_by = fields.Many2one(
        'res.users', string="Demandé par", readonly=True
    )

    def register_collection(self, amount=None):
        """Coche une case et crée la transaction terrain.
        Pour les cycles variables, amount est obligatoire."""
        journal_id = self.env['micro.transaction']._get_collection_journal_id()
        for line in self:
            if line.is_paid:
                continue
            is_variable = line.cycle_id.cycle_type == 'variable'
            if is_variable:
                if not amount or amount <= 0:
                    raise exceptions.UserError(
                        "Pour un cycle à montant variable, indiquez un montant valide."
                    )
                tx_amount = amount
            else:
                tx_amount = line.amount_expected
            self.env['micro.transaction'].create({
                'partner_id': line.cycle_id.partner_id.id,
                'amount': tx_amount,
                'currency_id': line.cycle_id.currency_id.id,
                'journal_id': journal_id,
                'transaction_type': 'savings',
                'state': 'draft',
                'cycle_line_id': line.id,
            })
            if is_variable:
                line.amount_collected = amount
            current_max = max(
                (l.collection_order for l in line.cycle_id.line_ids if l.collection_order > 0),
                default=0
            )
            line.collection_order = current_max + 1
            line.is_paid = True

    def _do_unregister(self):
        """Effectue le décocochage immédiat (appelé si autorisé)."""
        transaction = self.env['micro.transaction'].search(
            [('cycle_line_id', '=', self.id)], limit=1
        )
        if transaction:
            if transaction.state == 'confirmed':
                raise exceptions.UserError(
                    "Impossible d'annuler : cette collecte a déjà été validée "
                    "par le Manager."
                )
            transaction.sudo().unlink()
        self.write({
            'is_paid': False,
            'collection_order': 0,
            'amount_collected': 0.0,
            'uncheck_pending': False,
            'uncheck_requested_at': False,
            'uncheck_requested_by': False,
        })

    def unregister_collection(self):
        """Décoche une case — immédiat si Manager ou dans les 2 min, sinon soumet au Manager."""
        self.ensure_one()
        if not self.is_paid:
            raise exceptions.UserError("Cette case n'est pas encore cochée.")
        if self.uncheck_pending:
            raise exceptions.UserError(
                "Une demande d'annulation est déjà en attente de validation Manager."
            )

        is_manager = self.env.user.has_group('microflow.group_micro_flow_manager')

        transaction = self.env['micro.transaction'].search(
            [('cycle_line_id', '=', self.id)], limit=1
        )

        if transaction and transaction.state == 'confirmed':
            raise exceptions.UserError(
                "Impossible d'annuler : cette collecte a déjà été validée "
                "par le Manager."
            )

        if is_manager:
            self._do_unregister()
            return {'status': 'done'}

        # Agent : vérifier fenêtre de 2 minutes
        if transaction:
            elapsed = (fields.Datetime.now() - transaction.create_date).total_seconds()
            if elapsed <= 120:
                self._do_unregister()
                return {'status': 'done'}

        # Au-delà du délai : soumettre au Manager
        self.write({
            'uncheck_pending': True,
            'uncheck_requested_at': fields.Datetime.now(),
            'uncheck_requested_by': self.env.user.id,
        })
        return {'status': 'pending'}

    def action_approve_uncheck(self):
        """Manager approuve la demande d'annulation tardive."""
        self.ensure_one()
        if not self.env.user.has_group('microflow.group_micro_flow_manager'):
            raise exceptions.UserError("Réservé au Manager.")
        if not self.uncheck_pending:
            raise exceptions.UserError("Aucune demande d'annulation en attente pour cette case.")
        self._do_unregister()

    def action_reject_uncheck(self):
        """Manager rejette la demande d'annulation tardive."""
        self.ensure_one()
        if not self.env.user.has_group('microflow.group_micro_flow_manager'):
            raise exceptions.UserError("Réservé au Manager.")
        self.write({
            'uncheck_pending': False,
            'uncheck_requested_at': False,
            'uncheck_requested_by': False,
        })
