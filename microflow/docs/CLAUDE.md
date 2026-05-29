# CLAUDE.md — Microflow (contexte pour Claude Code)

> Fichier de contexte projet. À lire en début de session pour reprendre le travail sans perdre de temps.

---

## Identité du projet

**Nom technique :** `microflow`
**Version courante :** 1.4
**Odoo :** 18.0 Community
**Auteur :** KariSims
**Domaine :** Microfinance de terrain (Afrique subsaharienne)
**Devise par défaut :** CDF (Franc Congolais)

---

## Ce que fait le module

Microflow gère les **cycles d'épargne de tontine** et les **microcrédits** via des agents de terrain sur mobile :

1. Un **agent** crée un cycle (état brouillon) puis clique "Activer le Cycle" → génère N cases de pré-collecte (configurable, défaut 5) et passe en `pre_active`
2. L'agent collecte les premiers versements sur ces cases de prévisualisation et remet les fonds au **manager** (physiquement)
3. Le **manager** vérifie, clique "Activer le Cycle Complet" → crée les cases restantes, passe en `active`
4. L'agent continue la collecte sur le cycle complet via la grille tactile (MicroGrid)
5. Le **manager** valide les remises via un Kanban, génère 1 écriture comptable groupée par agent

---

## Architecture des modèles

```
res.partner (étendu)
  └── member_id : MF-ZONE-ANNEE-MOIS-SEQ (auto-séquence)
  └── zone_id   : Many2one → micro.zone
  └── birthdate, entity_type, member_type, gps_coordinates

micro.zone
  └── name, code (max 10 chars), commission_rate, active
  └── parent_id : Many2one → micro.zone (optionnel, hiérarchie jusqu'à N niveaux)
  └── child_ids : One2many (sous-zones)
  └── complete_name : computed+stored, cascade — ex. "Dakar / Médina / Bloc A"
  └── _check_recursion() : anti-cycle garanti par contrainte

micro.cycle  (cycle d'épargne d'un membre)
  └── partner_id, agent_id (default=env.user, readonly)
  └── state: draft → pre_active → active → closed
  └── case_count, amount_per_case, opening_fee
  └── currency_id (éditable jusqu'au 1er versement ou activation complète)
  └── amount_expected_total, amount_collected, amount_remaining (computed+stored)
  └── amount_projected (computed : case_count × amount_per_case)
  └── duration_months
  └── kanban_urgency_state (computed+stored Selection) : urgency|normal
  └── pending_uncheck_count (computed via line_ids.uncheck_pending)
  └── pending_uncheck_line_ids (One2many filtré sur uncheck_pending=True)
  └── case_count_requested (Integer, demande correction de l'agent)
  └── line_ids → micro.cycle.line
  └── action_agent_start_collecting() → pré-activation (Agent ou Manager)
  └── action_activate() → activation complète (Manager only)

micro.cycle.line  (1 case de la grille)
  └── sequence, amount_expected
  └── currency_id : related='cycle_id.currency_id' (NE PAS mettre de default ici)
  └── is_paid (Boolean)
  └── collection_order (Integer, rang chronologique de collecte, 0 = non payé)
  └── uncheck_pending (Boolean, demande d'annulation en attente Manager)
  └── uncheck_requested_at (Datetime, horodatage de la demande)
  └── uncheck_requested_by (Many2one → res.users)
  └── register_collection() → crée micro.transaction + assigne collection_order
  └── unregister_collection() → retourne {'status': 'done'|'pending'}
  └── _do_unregister() → helper partagé (annulation réelle)
  └── action_approve_uncheck() → Manager approuve l'annulation tardive
  └── action_reject_uncheck() → Manager rejette l'annulation tardive

micro.credit  (crédit accordé à un membre)
  └── partner_id, capital, interest_rate, installment_count
  └── currency_id (éditable tant que state = draft)
  └── state: draft → pending → active → closed
  └── line_ids → micro.credit.line

micro.credit.line  (1 échéance du crédit)
  └── currency_id : related='credit_id.currency_id'
  └── amount_due, amount_paid, amount_residual (computed), payment_count
  └── register_payment(amount) → crée micro.transaction

micro.transaction  (toute opération de caisse terrain)
  └── name: MF-TX/YYYY/00001 (auto-séquence)
  └── agent_id (readonly), partner_id, journal_id, amount, currency_id
  └── transaction_type: savings | credit_repayment | fees | savings_withdrawal
  └── state: draft (terrain) → confirmed (caisse)
  └── is_verified: boolean — coché par le manager à la remise physique
  └── cycle_line_id: Many2one → micro.cycle.line (back-référence collecte)
  └── cycle_id: Many2one → micro.cycle (pour savings_withdrawal — transfert épargne)
  └── action_bulk_confirm() → 1 account.move par (agent, devise) — multi-devise géré

credit.payment.wizard  (TransientModel)
  └── line_id, amount_to_pay → appelle line_id.register_payment()
  └── currency_id: related='line_id.currency_id'

savings.repayment.wizard  (TransientModel)
  └── credit_line_id, cycle_id (source épargne), amount_to_transfer
  └── action_validate() → register_payment(from_savings=True) + savings_withdrawal tx + account.move
  └── Écriture : DR Compte Dépôts Membres / CR Créances Client (aucun mouvement de caisse)
  └── Multi-devise : amount_currency + currency_id sur les lignes si devise ≠ société

res.users  (héritage)
  └── write() override : si 'groups_id' change → _sync_microflow_home_action()
  └── _sync_microflow_home_action() : manager → action_manager_dashboard ; agent → action_micro_cycle ; retiré → False

res.config.settings (étendu)
  └── micro_flow_journal_id      → ir.config_parameter 'microflow.journal_id'
  └── max_active_cycles          → ir.config_parameter 'microflow.max_active_cycles'
  └── draft_case_count           → ir.config_parameter 'microflow.draft_case_count' (défaut 5)
  └── micro_savings_account_id   → ir.config_parameter 'microflow.savings_account_id'
```

---

## Machine à états micro.cycle

```
draft
  │  action_agent_start_collecting()
  │  (Agent → crée N cases preview ; Manager → redirige vers action_activate)
  ▼
pre_active   ← cases preview créées, pré-collecte possible
  │  action_activate()  [Manager only]
  │  (crée les cases restantes pour atteindre case_count total)
  ▼
active       ← cycle complet, collecte normale
  │  (toutes les cases payées ou clôture manuelle)
  ▼
closed
```

Le champ `kanban_urgency_state` groupe dans la colonne "À traiter" les cycles `pre_active`
(activation Manager requise) et les cycles `active` ayant des annulations en attente.

---

## Groupes de sécurité

| Groupe XML ID | Nom affiché | Droits |
|---|---|---|
| `microflow.group_micro_flow_agent` | Agent de Terrain | Voit ses propres cycles et transactions seulement |
| `microflow.group_micro_flow_manager` | Manager / Contrôleur | Voit tout, valide, configure |

Manager a `implied_ids` sur Agent (un manager appartient aussi au groupe agent).

**Record rules :**
- `micro.cycle` : agent filtre sur `agent_id = user.id` / manager voit tout (1=1)
- `micro.transaction` : idem

---

## Devise par cycle / crédit

Chaque cycle et crédit a son propre `currency_id` (parmi les devises actives).

- `micro.cycle.currency_id` : éditable en `draft` et `pre_active`, verrouillé dès `amount_collected > 0`
- `micro.credit.currency_id` : éditable en `draft`, verrouillé dès `active/closed`
- `micro.cycle.line.currency_id` → `related='cycle_id.currency_id'` — **ne jamais mettre de default ici**
- `micro.credit.line.currency_id` → `related='credit_id.currency_id'`
- Toutes les transactions terrain reçoivent `currency_id` depuis le cycle ou crédit parent

**Multi-devise (v1.4) :** `_build_move_lines(txns, journal, label, date=None)` gère désormais la conversion.
Si `group_currency != company_currency` : `debit`/`credit` = montants convertis, `amount_currency` (négatif côté CR) + `currency_id` sur toutes les lignes. `action_bulk_confirm()` groupe par `(agent, currency)` — un move par combinaison.

---

## Fenêtre d'annulation de collecte (2 minutes)

- **Manager** → annulation immédiate à tout moment
- **Agent, ≤ 120s** depuis la transaction → annulation immédiate
- **Agent, > 120s** → `uncheck_pending=True` + retourne `{'status': 'pending'}`

Le Manager voit les demandes en attente dans le formulaire du cycle (section dédiée, visible si `pending_uncheck_count > 0`).

---

## Composant OWL : MicroGrid

**Fichiers :** `static/src/components/MicroGrid/MicroGrid.{js,xml,scss}`
**Utilisation :** `<field name="line_ids" widget="MicroGrid" nolabel="1"/>` dans `micro.cycle` form
**API Odoo 18 correcte :**
- `standardFieldProps` pour les props
- `staticList.records` pour accéder aux lignes one2many
- `useService('orm')` + `useService('notification')`
- Enregistré via `registry.category("fields").add("MicroGrid", { component, supportedTypes })`

**IMPORTANT — Limite One2many :** Odoo 17/18 limite par défaut le chargement des One2many à **40 enregistrements**.
Toujours ajouter `limit="N"` sur le `<list>` subview (N ≥ taille max attendue) :
```xml
<field name="line_ids" widget="MicroGrid" nolabel="1">
    <list limit="500">
        <field name="sequence"/>
        <field name="amount_expected"/>
        <field name="is_paid"/>
        <field name="collection_order"/>
        <field name="uncheck_pending"/>
    </list>
</field>
```

**Flux onCellTap :**
- Case vide → 1er tap : `pendingCheckId` (bleu pulsant, icône ☑, timer 2s) → 2ème tap : `register_collection()`
- Case payée → tap : `ConfirmationDialog` Odoo natif → "Annuler la collecte ?" → `unregister_collection()`
- Case `uncheck_pending` → toast "demande déjà soumise au Manager" + return

**Affichage `collection_order` :** exposant top-left sur cellule payée (`.mf-cell-order`, 7px vert).

---

## Dashboard Manager (OWL client action)

**Tag :** `microflow.manager_dashboard`
**Composant :** `static/src/components/ManagerDashboard/ManagerDashboard.{js,xml,scss}`
**Action :** `action_manager_dashboard` (menu Manager only, seq=5)

Cards KPI (5) : épargne, remboursements, frais, crédits en attente, crédits actifs.

Transactions terrain : tri, filtres, checkboxes individuels, select-all, boutons "Valider sélection (N)" et "Tout Valider".

---

## Service Worker PWA

- **Fichier SW :** `static/src/js/service_worker.js` — JAMAIS dans le bundle assets
- **Servi via contrôleur :** `GET /microflow/sw.js` avec header `Service-Worker-Allowed: /`
- **Enregistrement :** `static/src/js/sw_register.js` (dans `web.assets_backend`)
- **Fonctions :** cache-first assets, queue IndexedDB pour les write ops offline, Background Sync

---

## Configuration initiale requise (à faire avant tout test)

```
Settings → Access Rights → Micro Flow → assigner Manager à l'utilisateur de test
Settings → MICRO FLOW → Journal de collecte (caisse ou banque)          ← obligatoire
Settings → MICRO FLOW → Compte Dépôts Membres (account.account)         ← obligatoire pour confirmer épargne
Settings → MICRO FLOW → Max cycles actifs par membre                     ← défaut 1
Settings → MICRO FLOW → Cases preview (pré-activation agent)             ← défaut 5
```

Sans le journal → UserError à l'activation ou collecte.
Sans le compte dépôts → UserError à la confirmation des transactions épargne.

---

## Conventions de code

- Journal lu depuis `ir.config_parameter` : `int(self.env['ir.config_parameter'].sudo().get_param('microflow.journal_id', 0))`
- Avant toute création d'account.move : appeler `self._ensure_journal_account(journal)` (auto-affecte le compte si absent)
- `@api.model_create_multi` sur tous les `create()` — pas `@api.model`
- Pas de `tracking=True` sur les champs Selection sans `_inherit = 'mail.thread'`
- `currency_id` sur les lignes (cycle.line, credit.line) → toujours `related=` vers le parent — pas de `default=`
- Sens comptable épargne : Débit caisse / Crédit `micro_savings_account_id` (passif courant)

---

## Fichiers critiques à connaître

| Fichier | Rôle |
|---|---|
| `__manifest__.py` | Dépendances, ordre chargement, assets |
| `__init__.py` | Doit exporter `post_init_hook` au niveau package |
| `hooks.py` | `post_init_hook` : définit home actions agent/manager |
| `security/security_groups.xml` | Groupes (chargé en 1er) |
| `security/record_rules.xml` | Isolation données agent |
| `security/ir.model.access.csv` | Droits CRUD par groupe |
| `models/micro_transaction.py` | action_bulk_confirm (groupement agent+devise), _build_move_lines (multi-devise) |
| `models/res_users.py` | _sync_microflow_home_action, write() override |
| `wizard/savings_repayment_wizard.py` | Transfert épargne → crédit |
| `models/micro_cycle.py` | action_agent_start_collecting, action_activate, kanban_urgency_state |
| `models/micro_cycle_line.py` | register_collection, unregister_collection, _do_unregister |
| `views/micro_cycle_views.xml` | Formulaire cycle + kanban urgence |
| `views/micro_transaction_views.xml` | Dashboard Manager OWL client action |
| `static/src/components/MicroGrid/MicroGrid.js` | Widget OWL terrain |
| `static/src/components/ManagerDashboard/ManagerDashboard.js` | Dashboard OWL |
| `controllers/controllers.py` | Route /microflow/sw.js |

---

## Commandes utiles

```bash
# Installation fraîche
python odoo-bin -i microflow -d <base> --dev=all

# Mise à jour
python odoo-bin -u microflow -d <base> --dev=all

# Tests (76 tests sur 6 fichiers)
python odoo-bin -d <base> --test-enable --stop-after-init -i microflow
```

---

## Roadmap complète

Voir `docs/ROADMAP.md` pour le plan de travail priorisé avec le statut de chaque module.
