from odoo import fields, models, api

class PartnerCommercial(models.Model):
    _name = 'jallow.commercial'
    _description = 'Commercial'

    name = fields.Char(string='Commercial')
    sexe = fields.Selection([
        ('', 'Choisissez le sexe'),
        ('m', 'Masculin'),
        ('f', 'Féminin'),
        ],
        string="Sexe",
        default='')
    tel = fields.Char(string='Téléphone')
    ese = fields.Many2one(
    'jallow.society',
    string='Société',
    help='Société où l\'agent travaille'
    )

class PartnerSupervisor(models.Model):
    _name = 'jallow.supervisor'
    _description = 'Superviseur Foot Soldiers'

    name = fields.Char(string='Superviseur')
    sexe = fields.Selection([
        ('', 'Choisissez le sexe'),
        ('m', 'Masculin'),
        ('f', 'Féminin'),
        ],
        string="Sexe",
        default='')
    tel = fields.Char(string='Téléphone')
    ese = fields.Many2one(
    'jallow.society',
    string='Société',
    help='Société où l\'agent travaille'
    )
    soldier_ids2 = fields.One2many("jallow.soldier", "supervisor", string="Merchandiser")
    team_required = fields.Boolean(compute="_compute_required")

    @api.depends('soldier_ids2')
    def _compute_required(self):
        for record in self:
            record.team_required = False
            if record.soldier_ids2:
                record.team_required = True

class PartnerSoldier(models.Model):
    _name = 'jallow.soldier'
    _description = 'Foot Soldier'

    name = fields.Char(string='Foot Soldier')
    sexe = fields.Selection([
        ('', 'Choisissez le sexe'),
        ('m', 'Masculin'),
        ('f', 'Féminin'),
        ],
        string="Sexe",
        default='')
    tel = fields.Char(string='Téléphone')
    ese = fields.Many2one(
    'jallow.society',
    string='Société',
    help='Société où l\'agent travaille'
    )
    supervisor = fields.Many2one(
    'jallow.supervisor',
    string='Superviseur ou Responsable d\'Equipe'
    )

class PartnerCommune(models.Model):
    _name = 'jallow.commune'
    _description = 'Commune'

    name = fields.Char(string='Commune')
    city_sn = fields.Char(string='Ville')
    region_sn = fields.Char(string='Region')


class Partner(models.Model):
    _inherit = 'res.partner'   


    canal_trade = fields.Selection([
        ('mt', 'Modern Trade'),
        ('tt', 'Traditionnal Trade'),
        ],
        string="Canal Trade",
        default='')
    
    commune_id_m2o = fields.Many2one(
        'jallow.commune',
        string='Commune',
        help='Commune d\'implantation du Client'
    )

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
        default='')

    # commercial_id: PartnerCommercial = fields.Many2one('jallow.commercial')
    commercial_id = fields.Many2one(
    'jallow.commercial',
    string='Commercial',
    help='Commercial qui a prospecté le client'
    )
    supervisor_id = fields.Many2one(
    'jallow.supervisor',
    string='Superviseur des Merchandisers',
    help='Superviseur des Merchandisers ou Foot Soldiers'
    )
    soldier_id = fields.Many2one(
    'jallow.soldier',
    string='Foot Soldier',
    help='Foot Soldier qui a prospecté le client'
    )