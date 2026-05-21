from odoo.tests.common import TransactionCase
from datetime import date


class TestResPartner(TransactionCase):

    def setUp(self):
        super().setUp()
        self.zone = self.env['micro.zone'].create({
            'name': 'Zone Test',
            'code': 'TST',
        })

    def _make_partner(self, **kwargs):
        defaults = {
            'name': 'Test Member',
            'birthdate': date(1990, 6, 15),
            'zone_id': self.zone.id,
            'entity_type': 'individual',
            'member_type': 'saver',
        }
        defaults.update(kwargs)
        return self.env['res.partner'].create(defaults)

    def test_member_id_generation(self):
        """Zone + birthdate → member_id format MF-CODE-YYYY-MM-SEQ."""
        partner = self._make_partner()
        self.assertTrue(partner.member_id, "member_id doit être généré")
        self.assertTrue(
            partner.member_id.startswith('MF-TST-1990-06-'),
            f"Format inattendu: {partner.member_id}"
        )

    def test_member_id_unique_per_member(self):
        """Deux membres distincts doivent avoir des member_id différents."""
        p1 = self._make_partner(name='Alice')
        p2 = self._make_partner(name='Bob')
        self.assertNotEqual(p1.member_id, p2.member_id)

    def test_member_id_contains_zone_code(self):
        """Le code de zone doit apparaître dans le member_id."""
        zone_b = self.env['micro.zone'].create({'name': 'Zone B', 'code': 'ZBB'})
        partner = self._make_partner(zone_id=zone_b.id)
        self.assertIn('ZBB', partner.member_id)
