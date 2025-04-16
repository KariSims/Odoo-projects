from odoo import fields, models, api

class PartnerCommercial(models.Model):
    _name = 'jallow.commercial'
    _description = 'Commercial'

    name = fields.Char(string='Commercial', required=True)
    sexe = fields.Selection([
        ('', 'Choisissez le sexe'),
        ('m', 'Masculin'),
        ('f', 'Féminin'),
        ],
        string="Sexe",
        required=True,
        default='')
    tel = fields.Char(string='Téléphone')
    # ese = fields.Char(string='Société')
    # ese: PartnerSociety = fields.Many2one('res.society')
    ese = fields.Many2one(
    'jallow.society',
    string='Société',
    help='Société où l\'agent travaille'
    )

class PartnerSoldier(models.Model):
    _name = 'jallow.soldier'
    _description = 'Foot Soldier'

    name = fields.Char(string='Foot Soldier', required=True)
    sexe = fields.Selection([
        ('', 'Choisissez le sexe'),
        ('m', 'Masculin'),
        ('f', 'Féminin'),
        ],
        string="Sexe",
        required=True,
        default='')
    tel = fields.Char(string='Téléphone')
    ese = fields.Many2one(
    'jallow.society',
    string='Société',
    help='Société où l\'agent travaille'
    )
    commercial = fields.Many2one(
    'jallow.commercial',
    string='Responsable commercial'
    )

class Partner(models.Model):
    _inherit = 'res.partner'   


    canal_trade = fields.Selection([
        ('mt', 'Modern Trade'),
        ('tt', 'Traditionnel Trade'),
        ],
        string="Canal Trade",
        required=True,
        default='')
    commune_id = fields.Selection([
        ('bambilor','Bambilor'),
        ('bargny','Bargny'),
        ('biscuiterie','Biscuiterie'),
        ('camberene','Camberene'),
        ('dakar_plateau','Dakar Plateau'),
        ('dalifort','Dalifort'),
        ('diamaguene_sicap_mbao','Diamaguene sicap mbao'),
        ('diamniadio','Diamniadio'),
        ('dieuppeul_derkle','Dieuppeul Derkle'),
        ('djidah_thiaroye_kao','Djidah Thiaroye Kao'),
        ('fann_point_e_amitie','Fann Point E Amitie'),
        ('golf_sud','Golf Sud'),
        ('goree','Goree'),
        ('grand_dakar','Grand Dakar'),
        ('grand_yoff','Grand Yoff'),
        ('gueule_tapee_fass_colobane','Gueule Tapee Fass Colobane'),
        ('guinaw','Guinaw'),
        ('hann_bel_air','Hann Bel Air'),
        ('hlm','Hlm'),
        ('jaxaay_parcelles','Jaxaay Parcelles'),
        ('keur_massar','Keur Massar'),
        ('malika','Malika'),
        ('mbao','Mbao'),
        ('medina','Medina'),
        ('medina_gounass','Medina Gounass'),
        ('mermoz_sacre_coeur','Mermoz Sacre Coeur'),
        ('ndiareme_limamoulaye','Ndiareme Limamoulaye'),
        ('ngor','Ngor'),
        ('ouakam','Ouakam'),
        ('parcelles_assainies','Parcelles Assainies'),
        ('patte_d_oie','Patte d\'Oie'),
        ('pikine','Pikine'),
        ('rufisque','Rufisque'),
        ('sam_notaire','Sam Notaire'),
        ('sangalkam','Sangalkam'),
        ('sebikotane','Sebikotane'),
        ('sendou','Sendou'),
        ('sicap_liberte','Sicap liberte'),
        ('thiaroye_gare','Thiaroye Gare'),
        ('thiaroye_sur_mer','Thiaroye sur Mer'),
        ('tivaouane_diacksao','Tivaouane diacksao'),
        ('tivaouane_peulh_niagha','Tivaouane Peulh Niagha'),
        ('wakhinane_nimzatt','Wakhinane Nimzatt'),
        ('yene','Yene'),
        ('yeumbeul','Yeumbeul'),
        ('yoff','Yoff'),
        ],
        string="Commune",
        # required=True,
        default='')
    # commercial_id: PartnerCommercial = fields.Many2one('jallow.commercial')
    commercial_id = fields.Many2one(
    'jallow.commercial',
    string='Commercial',
    help='Commercial qui a prospecté le client'
    )
    soldier_id = fields.Many2one(
    'jallow.soldier',
    string='Foot Soldier',
    help='Foot Soldier qui a prospecté le client'
    )

    phone = fields.Char('phone')
    street2 = fields.Char('Street2')

    @api.onchange('phone')
    def _onchange_telephone(self):
        if self.phone:
            self.street2 = self.phone