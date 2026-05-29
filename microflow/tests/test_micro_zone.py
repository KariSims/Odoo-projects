from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMicroZone(TransactionCase):

    def _zone(self, name, code, parent=None):
        vals = {'name': name, 'code': code}
        if parent:
            vals['parent_id'] = parent.id
        return self.env['micro.zone'].create(vals)

    # ── complete_name computation ────────────────────────────────────────────

    def test_complete_name_root(self):
        """Zone sans parent → complete_name == name."""
        z = self._zone('Dakar', 'DKR')
        self.assertEqual(z.complete_name, 'Dakar')

    def test_complete_name_level2(self):
        """Zone enfant → complete_name = parent / name."""
        parent = self._zone('Dakar', 'DKR')
        child = self._zone('Médina', 'MDN', parent=parent)
        self.assertEqual(child.complete_name, 'Dakar / Médina')

    def test_complete_name_level3(self):
        """Zone petite-enfant → complete_name à 3 niveaux."""
        root = self._zone('Dakar', 'DKR')
        mid = self._zone('Médina', 'MDN', parent=root)
        leaf = self._zone('Bloc A', 'BLA', parent=mid)
        self.assertEqual(leaf.complete_name, 'Dakar / Médina / Bloc A')

    def test_complete_name_cascade_on_parent_rename(self):
        """Renommer la zone parente → complete_name de l'enfant se met à jour."""
        parent = self._zone('Ancienne', 'ANC')
        child = self._zone('Enfant', 'ENF', parent=parent)
        parent.name = 'Nouvelle'
        self.assertEqual(child.complete_name, 'Nouvelle / Enfant')

    def test_complete_name_cascade_three_levels(self):
        """Renommer la racine → cascade jusqu'au niveau 3."""
        root = self._zone('Racine', 'RAC')
        mid = self._zone('Milieu', 'MID', parent=root)
        leaf = self._zone('Feuille', 'FEU', parent=mid)
        root.name = 'Root'
        self.assertEqual(leaf.complete_name, 'Root / Milieu / Feuille')

    # ── child_ids ────────────────────────────────────────────────────────────

    def test_child_ids_populated(self):
        """Les enfants apparaissent dans child_ids du parent."""
        parent = self._zone('Parent', 'PAR')
        c1 = self._zone('Enfant 1', 'E01', parent=parent)
        c2 = self._zone('Enfant 2', 'E02', parent=parent)
        self.assertIn(c1, parent.child_ids)
        self.assertIn(c2, parent.child_ids)

    def test_root_has_no_parent(self):
        """Zone racine : parent_id est vide."""
        root = self._zone('Racine', 'RAC')
        self.assertFalse(root.parent_id)

    # ── anti-recursion constraints ────────────────────────────────────────────

    def test_self_reference_blocked(self):
        """Une zone ne peut pas être son propre parent."""
        z = self._zone('Test', 'TST')
        with self.assertRaises((ValidationError, Exception)):
            z.parent_id = z.id
            z._check_parent_recursion()

    def test_cycle_blocked(self):
        """Cycle A → B → A déclenche ValidationError."""
        a = self._zone('A', 'AAA')
        b = self._zone('B', 'BBB', parent=a)
        with self.assertRaises(ValidationError):
            b.write({'parent_id': False})
            a.write({'parent_id': b.id})

    # ── member_id uses leaf zone code ────────────────────────────────────────

    def test_member_id_uses_leaf_code(self):
        """member_id contient le code de la zone feuille, pas de la racine."""
        from datetime import date
        root = self._zone('Dakar', 'DKR')
        leaf = self._zone('Médina', 'MDN', parent=root)
        partner = self.env['res.partner'].create({
            'name': 'Test Leaf',
            'birthdate': date(1995, 3, 10),
            'zone_id': leaf.id,
            'entity_type': 'individual',
            'member_type': 'saver',
        })
        self.assertIn('MDN', partner.member_id)
        self.assertNotIn('DKR', partner.member_id)
