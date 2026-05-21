from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- IDENTIFICATION ---
    member_id = fields.Char(
        string="ID Membre Unique", 
        readonly=True, 
        copy=False, 
        help="Format: MF-ZONE-ANNEE-MOIS-ORDRE"
    )
    birthdate = fields.Date(
        string="Date de naissance", 
        required=True,
        help="Obligatoire pour la génération de l'ID Unique"
    )

    # --- SEGMENTATION ---
    entity_type = fields.Selection([
        ('individual', 'Individuel'),
        ('group', 'Groupement')
    ], string="Type Client", default='individual', required=True)

    member_type = fields.Selection([
        ('prospect', 'Prospect'),
        ('saver', 'Épargnant'),
        ('pos', 'Point de Vente')
    ], string="Statut Membre", default='prospect', required=True)

    # --- LOCALISATION ---
    zone_id = fields.Many2one(
        'micro.zone', 
        string="Zone Géographique", 
        required=True
    )
    gps_coordinates = fields.Char(
        string="Coordonnées GPS", 
        readonly=True,
        help="Capturées automatiquement à l'instant T"
    )

    @api.model
    def create(self, vals):
        # Récupération des données pour générer l'ID personnalisé
        zone = self.env['micro.zone'].browse(vals.get('zone_id'))
        birthdate_str = vals.get('birthdate')
        
        if zone and birthdate_str:
            # Extraction année et mois
            birth_dt = datetime.strptime(birthdate_str, '%Y-%m-%d')
            year = birth_dt.strftime('%Y')
            month = birth_dt.strftime('%m')
            
            # Récupération du numéro d'ordre via la séquence
            seq_order = self.env['ir.sequence'].next_by_code('micro.flow.member.order') or '000'
            
            # Application de la règle métier : MF-ZONE-ANNEE-MOIS-ORDRE
            vals['member_id'] = f"MF-{zone.code}-{year}-{month}-{seq_order}"
        
        return super(ResPartner, self).create(vals)

    def action_capture_gps(self):
        """
        Cette méthode sera liée au bouton sur l'interface mobile.
        Elle déclenchera l'appel à l'API de géolocalisation.
        """
        # La logique de capture réelle se fait via Javascript (Odoo Web/Mobile)
        # On prépare le terrain ici pour stocker la valeur.
        return True