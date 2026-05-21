# TODOS — Microflow

> Généré par /plan-eng-review — 2026-05-17
> Màj implémentation — 2026-05-17

---

## TODO-1 : Dashboard Manager Kanban ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

**Livré :**
- `view_micro_transaction_kanban` : kanban sur `micro.transaction` groupé par `agent_id`
- Cards avec : membre, type (badge), montant, toggle `is_verified`
- `action_micro_dashboard` : pointe vers `micro.transaction`, filtré state=draft, groupé par agent
- Bouton "Tout Valider" dans la list view header → `action_bulk_confirm()` sur la sélection
- Menu Tableau de Bord restreint au groupe Manager

**Reste à faire (scope v1) :**
- Cartes aggrégées par agent (total remis, N validés, barre progression) → nécessite composant OWL custom
- Empty state positif "Tout validé! Total: X CDF"

---

## TODO-2 : Composant OWL MicroGrid ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

**Livré :**
- `static/src/components/MicroGrid/MicroGrid.js` : field widget OWL pour `one2many`
- `static/src/components/MicroGrid/MicroGrid.xml` : template avec banner case courante + grille colorée
- `static/src/components/MicroGrid/MicroGrid.scss` : styles cases (vide/courante/payée), animation pulse, responsive 5→7→10→12 colonnes
- `views/micro_cycle_views.xml` : `line_ids` utilise `widget="MicroGrid"`
- Touch targets 65px minimum (DESIGN_SPEC §3 ✓)
- Banner case courante sticky avec animation, appel `register_collection()` on tap
- Empty state "Aucune case — activez le cycle"
- Indicateur "Toutes les cases collectées !" quand cycle complet

---

## TODO-3 : Suite de tests métier ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

16 tests dans `tests/` : `test_res_partner.py`, `test_micro_cycle.py`, `test_micro_credit.py`

Lancer : `python odoo-bin -d <db> --test-enable --stop-after-init -i microflow`

---

## TODO-4 : Écriture comptable groupée + récapitulatif journalier agent ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

- `action_bulk_confirm()` : 1 `account.move` groupée par agent
- Vue récapitulatif journalier agent + menus "Mon Récapitulatif" / "Toutes les Transactions"

---

## TODO-5 : PWA service worker ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

- `service_worker.js` + `sw_register.js` : offline queue IndexedDB + Background Sync

---

## Wizard versement plein écran ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

- `credit_payment_wizard_views.xml` : classe `mf-payment-wizard` ajoutée
- `static/src/css/microflow_mobile.scss` : dialog plein écran sur mobile (100vw/100vh), montant 48px, bouton Valider 56px pleine largeur, Annuler en text link

---

## Règles d'enregistrement par agent ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

- `security/record_rules.xml` : agent voit seulement ses cycles + transactions (domain `agent_id = user.id`)
- Manager override : domain `1=1` (voit tout)
- Pattern OR correct grâce aux `implied_ids` (manager ∈ agent group)

---

## NOT in scope (design déféré)

- Thème tiers (MuK IT) — Odoo standard suffisant pour v0
- App native (Flutter/React Native) — PWA couvre le besoin
- Reçu SMS pour agents — scope v1
- Hiérarchie de zones imbriquées — scope v1
- Tests E2E complets — scope v1
- Résolution de conflits offline sophisticated — scope v1
- Cartes agent agrégées dans le Kanban (total remis + barre progression par agent) — scope v1
- Empty state "Tout validé!" Dashboard Manager — scope v1
