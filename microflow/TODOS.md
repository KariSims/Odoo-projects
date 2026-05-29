# TODOS — Microflow

> Dernière mise à jour : 2026-05-27 (v1.4 — session complète : hiérarchie zones, tests 76, multi-devise, home actions)

---

## TODO-1 : Dashboard Manager Kanban ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

**Livré :**
- `view_micro_transaction_kanban` : kanban sur `micro.transaction` groupé par `agent_id`
- Cards avec : membre, type (badge), montant, toggle `is_verified`
- `action_micro_dashboard` : pointe vers `micro.transaction`, filtré state=draft, groupé par agent
- Bouton "Tout Valider" dans la list view header → `action_bulk_confirm()` sur la sélection
- Menu Tableau de Bord restreint au groupe Manager

---

## TODO-2 : Composant OWL MicroGrid ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

**Livré :**
- `static/src/components/MicroGrid/MicroGrid.{js,xml,scss}` : field widget OWL pour `one2many`
- Template avec grille colorée, banner case courante + animation
- Responsive 5→7→10→12 colonnes selon largeur écran
- Touch targets 65px minimum
- Appel `register_collection()` on tap
- Empty state "Aucune case — activez le cycle"
- Indicateur "Toutes les cases collectées !" quand cycle complet

---

## TODO-3 : Suite de tests métier ✅ FAIT

**Status: TERMINÉ — 2026-05-17, étendu à 76 tests le 2026-05-27**

76 tests répartis sur 6 fichiers :

| Fichier | Tests |
|---|---|
| `tests/test_micro_cycle.py` | 37 (+ 6 correction de cases) |
| `tests/test_savings_transfer.py` | 13 |
| `tests/test_micro_credit.py` | 8 |
| `tests/test_res_partner.py` | 3 |
| `tests/test_micro_zone.py` | 10 |
| `tests/test_res_users.py` | 5 |

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
- Corrigé 2026-05-27 : ligne `microflow_mobile.scss` décommentée dans `__manifest__.py`

---

## Règles d'enregistrement par agent ✅ FAIT

**Status: TERMINÉ — 2026-05-17**

- `security/record_rules.xml` : agent voit seulement ses cycles + transactions (domain `agent_id = user.id`)
- Manager override : domain `1=1` (voit tout)
- Pattern OR correct grâce aux `implied_ids` (manager ∈ agent group)

---

## Dashboard Manager OWL complet ✅ FAIT

**Status: TERMINÉ — 2026-05-22**

- Composant OWL `ManagerDashboard` : client action tag `microflow.manager_dashboard`
- 5 KPI cards : épargne, remboursements, frais, crédits en attente, crédits actifs
- Transactions terrain avec colonne "Reçu" (is_verified), checkboxes individuels + select-all
- Boutons "Valider la sélection (N)" et "Tout Valider" (méthode `_doValidate` partagée)
- Sections pliables via `state.txCollapsed` / `state.crCollapsed`

---

## Collection order (rang chronologique) ✅ FAIT

**Status: TERMINÉ — 2026-05-22**

- Champ `collection_order` (Integer, default=0) sur `micro.cycle.line`
- `register_collection()` affecte `max(collection_order des lignes payées) + 1`
- `unregister_collection()` remet à 0
- Affiché en exposant top-left sur cellule payée dans MicroGrid
- 3 tests dédiés : `test_collection_order_increments`, `test_collection_order_reset_on_unregister`, `test_collection_order_no_duplicate`

---

## Fenêtre annulation 2 minutes + escalade Manager ✅ FAIT

**Status: TERMINÉ — 2026-05-22**

- Champs `uncheck_pending`, `uncheck_requested_at`, `uncheck_requested_by` sur `micro.cycle.line`
- `unregister_collection()` → immédiat si Manager ou ≤ 120s, sinon `{status: 'pending'}`
- `action_approve_uncheck()` / `action_reject_uncheck()` sur `micro.cycle.line`
- Vue form `micro.cycle` : section "Demandes d'annulation en attente" (Manager only)
- Computed `pending_uncheck_count` + `pending_uncheck_line_ids` sur `micro.cycle`
- MicroGrid : cellule bordeaux `.mf-cell-approval-pending` + badge ⏳ si `uncheck_pending`

---

## Correction sens comptable épargne ✅ FAIT

**Status: TERMINÉ — 2026-05-23 (dette 6.6)**

- Avant (bugué) : épargne → Débit compte clients / Crédit caisse
- Après (correct) : épargne → Débit caisse / Crédit `micro_savings_account_id` (passif courant)
- Nouveau champ `micro_savings_account_id` dans `res.config.settings` + vue Config
- Helper `_get_savings_account()` + `_build_move_lines()` DRY sur `micro_transaction.py`
- 5 nouveaux tests T1-T5

---

## UX Mobile : workflow activation 2 étapes ✅ FAIT

**Status: TERMINÉ — 2026-05-23 (v0.9)**

- État `pre_active` ajouté à la machine à états du cycle
- `action_agent_start_collecting()` : Agent → crée N cases preview (configurable `microflow.draft_case_count`, défaut 5) + passe en `pre_active` ; Manager → redirige vers `action_activate()`
- `action_activate()` : Manager only → crée cases restantes + passe en `active`
- `kanban_urgency_state` (stored computed) : 5 valeurs — `correction_pending`, `uncheck_pending`, `to_process`, `active`, `closed`/`draft`
- Boutons mobile sticky dans le formulaire cycle
- Alertes contextuelles selon l'état (brouillon, pré-collecte)

---

## Fix MicroGrid — limite 40 cases ✅ FAIT

**Status: TERMINÉ — 2026-05-23 (v0.9)**

- Cause : Odoo 17/18 limite par défaut les One2many à 40 enregistrements côté frontend
- Fix : `limit="500"` sur le `<list>` subview dans `views/micro_cycle_views.xml`
- Règle : tout widget OWL custom sur un One2many doit avoir `limit="N"` explicite

---

## Devise par cycle/crédit ✅ FAIT

**Status: TERMINÉ — 2026-05-23 (v0.9)**

- `micro.cycle.currency_id` : éditable en `draft`/`pre_active`, verrouillé dès `amount_collected > 0`
- `micro.credit.currency_id` : éditable en `draft`, verrouillé dès `active/closed`
- `micro.cycle.line.currency_id` → `related='cycle_id.currency_id'` (bug corrigé : était une copie avec default company currency)
- `micro.credit.line.currency_id` → `related='credit_id.currency_id'`
- `register_collection()` → transaction reçoit `currency_id=cycle_id.currency_id`
- `register_payment()` → transaction reçoit `currency_id=credit_id.currency_id`
- Frais adhésion → transaction reçoit `currency_id=record.currency_id`

---

## Correction post_init_hook ✅ FAIT

**Status: TERMINÉ — 2026-05-23**

- Cause : `__init__.py` importait `hooks` comme sous-module sans ré-exporter `post_init_hook` au niveau package
- Fix : `from .hooks import post_init_hook` ajouté dans `__init__.py`

---

## Commission savings — suppression du champ formulaire ✅ FAIT

**Status: TERMINÉ — 2026-05-23**

- `commission_rate` retiré du formulaire de cycle (l'agent ne fixe pas de pourcentage)
- La convention métier est : 1 case réservée à la fin du cycle pour l'institution
- Le champ `commission_rate` reste dans le modèle (compatibilité) mais n'est plus utilisé dans les calculs
- Calcul commission retiré de `register_collection()`

---

## Wizard transfert épargne → crédit ✅ FAIT

**Status: TERMINÉ (non daté dans TODOS — détecté audit 2026-05-27)**

- `wizard/savings_repayment_wizard.py` : `savings.repayment.wizard`
- Sélection du cycle source (domain : même membre, état actif, solde > 0)
- Validations : montant > 0, ≤ solde épargne, ≤ reste dû échéance
- `credit_line_id.register_payment(amount, from_savings=True)` — met à jour l'échéance sans créer de transaction caisse
- Transaction `savings_withdrawal` créée pour audit trail (state=confirmed)
- Écriture comptable : DR Dépôts Membres / CR Créances Client (aucun mouvement de caisse — compensation interne)
- `withdrawal_ids` + `amount_withdrawn` + `savings_balance` sur `micro.cycle` pour traçabilité
- Smart button épargne sur le formulaire crédit (`partner_savings_total`, `action_view_savings`)
- 13 tests dans `tests/test_savings_transfer.py`

---

## Correction de cases ✅ FAIT

**Status: TERMINÉ (non daté dans TODOS — détecté audit 2026-05-27)**

- Champ `case_count_requested` (Integer) sur `micro.cycle` : l'agent saisit le nombre corrigé
- `action_request_correction()` : valide que la demande est cohérente (> 0, ≠ actuel, ≥ cases déjà payées)
- `action_approve_correction()` : Manager crée ou supprime les cases non payées pour atteindre le nouveau total, remet `case_count_requested = 0`
- `action_reject_correction()` : Manager rejette, remet `case_count_requested = 0`
- `kanban_urgency_state = 'correction_pending'` : prioritaire sur `uncheck_pending` dans le Kanban Manager

---

## NOT in scope (design déféré)

- Thème tiers (MuK IT) — Odoo standard suffisant pour v0
- App native (Flutter/React Native) — PWA couvre le besoin
- Reçu SMS pour agents — scope v1 (provider : MSG91 via `sms_msg91`, dépendance souple, toggle config, appel en fin de `action_bulk_confirm()`)
- ~~Hiérarchie de zones imbriquées~~ ✅ FAIT 2026-05-27
- ~~Tests E2E complets~~ ✅ FAIT 2026-05-27 — Option A : 76 tests backend (`test_micro_zone`, `test_res_users`, correction de cases ajoutés)
- Résolution de conflits offline sophistiqué — scope v1
- ~~Cartes agent agrégées dans le Kanban~~ ✅ FAIT 2026-05-27
- ~~Empty state "Tout validé!" Dashboard Manager~~ ✅ FAIT 2026-05-27
- ~~Multi-devise comptable (amount_currency dans account.move)~~ ✅ FAIT 2026-05-27 — Option B complète : `_build_move_lines` + `action_confirm_payment` + `action_bulk_confirm` (groupement par devise) + wizard transfert épargne→crédit
