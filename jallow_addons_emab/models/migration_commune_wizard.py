from odoo import models, fields, api
from odoo.exceptions import UserError

class CommuneMigrationWizard(models.TransientModel):
    _name = 'jallow.commune.migration.wizard'
    _description = 'Migration des communes vers Many2one'

    def migrate_communes(self):
        Partner = self.env['res.partner']
        Commune = self.env['jallow.commune']

        # Mapping les valeurs selection => name
        code_to_name = {
            'bambilor' : 'Bambilor',
            'bargny' : 'Bargny',
            'biscuiterie' : 'Biscuiterie',
            'camberene' : 'Camberene',
            'dakar_plateau' : 'Dakar Plateau',
            'dalifort' : 'Dalifort',
            'diamaguene_sicap_mbao' : 'Diamaguene sicap mbao',
            'diamniadio' : 'Diamniadio',
            'dieuppeul_derkle' : 'Dieuppeul Derkle',
            'djidah_thiaroye_kao' : 'Djidah Thiaroye Kao',
            'fann_point_e_amitie' : 'Fann Point E Amitie',
            'golf_sud' : 'Golf Sud',
            'goree' : 'Goree',
            'grand_dakar' : 'Grand Dakar',
            'grand_yoff' : 'Grand Yoff',
            'gueule_tapee_fass_colobane' : 'Gueule Tapee Fass Colobane',
            'guinaw' : 'Guinaw',
            'hann_bel_air' : 'Hann Bel Air',
            'hlm' : 'Hlm',
            'jaxaay_parcelles' : 'Jaxaay Parcelles',
            'keur_massar' : 'Keur Massar',
            'malika' : 'Malika',
            'mbao' : 'Mbao',
            'medina' : 'Medina',
            'medina_gounass' : 'Medina Gounass',
            'mermoz_sacre_coeur' : 'Mermoz Sacre Coeur',
            'ndiareme_limamoulaye' : 'Ndiareme Limamoulaye',
            'ngor' : 'Ngor',
            'ouakam' : 'Ouakam',
            'parcelles_assainies' : 'Parcelles Assainies',
            'patte_d_oie' : 'Patte d\'Oie',
            'pikine' : 'Pikine',
            'rufisque' : 'Rufisque',
            'sam_notaire' : 'Sam Notaire',
            'sangalkam' : 'Sangalkam',
            'sebikotane' : 'Sebikotane',
            'sendou' : 'Sendou',
            'sicap_liberte' : 'Sicap liberte',
            'thiaroye_gare' : 'Thiaroye Gare',
            'thiaroye_sur_mer' : 'Thiaroye sur Mer',
            'tivaouane_diacksao' : 'Tivaouane diacksao',
            'tivaouane_peulh_niagha' : 'Tivaouane Peulh Niagha',
            'wakhinane_nimzatt' : 'Wakhinane Nimzatt',
            'yene' : 'Yene',
            'yeumbeul' : 'Yeumbeul',
            'yoff' : 'Yoff',
        }

        updated = 0
        skipped = 0

        partners = Partner.search([])

        for partner in partners:
            code = partner.commune_id
            commune_name = code_to_name.get(code)
            if not commune_name:
                skipped += 1
                continue

            commune = Commune.search([('name', '=', commune_name)], limit=1)
            
            if commune:
                partner.commune_id = commune.id
                updated += 1
            else:
                skipped += 1

        raise UserError(f"Migration terminée : {updated} partenaire(s) mis à jour, {skipped} ignoré(s).")
