# CLAUDE.md — Microflow (contexte pour Claude Code)

> Fichier de contexte projet. À lire en début de session pour reprendre le travail sans perdre de temps.

---

## Identité du projet

**Nom technique :** `microflow`
**Version courante :** 0.3
**Odoo :** 18.0 Community
**Auteur :** KariSims
**Domaine :** Microfinance de terrain (Afrique subsaharienne)
**Devise par défaut :** CDF (Franc Congolais)

---

## Ce que fait le module

Microflow gère les **cycles d'épargne de tontine** et les **microcrédits** via des agents de terrain sur mobile :

1. Un **agent** visite les membres, collecte les versements case par case via une grille tactile (MicroGrid)
2. À la fin de journée, l'agent remet les fonds au **manager** (physiquement)
3. Le **manager** valide les remises via un Kanban, génère 1 écriture comptable groupée par agent

---

## Architecture des modèles

```
res.partner (étendu)
  └── member_id : MF-ZONE-ANNEE-MOIS-SEQ (auto-séquence)
  └── zone_id   : Many2one → micro.zone
  └── birthdate, entity_type, member_type, gps_coordinates

micro.zone
  └── name, code (max 10 chars), commission_rate, active

micro.cycle  (cycle d'épargne d'un membre)
  └── partner_id, agent_id (default=env.user, readonly)
  └── state: draft → active → closed
  └── case_count, amount_per_case, opening_fee, commission_rate
  └── line_ids → micro.cycle.line

micro.cycle.line  (1 case de la grille)
  └── sequence, amount_expected, is_paid
  └── register_collection() → crée micro.transaction

micro.credit  (crédit accordé à un membre)
  └── partner_id, capital, interest_rate, installment_count
  └── state: draft → active → closed
  └── line_ids → micro.credit.line

micro.credit.line  (1 échéance du crédit)
  └── amount_due, amount_paid, amount_residual (computed), payment_count
  └── register_payment(amount) → crée micro.transaction

micro.transaction  (toute opération de caisse terrain)
  └── name: MF-TX/YYYY/00001 (auto-séquence)
  └── agent_id (readonly), partner_id, journal_id, amount
  └── transaction_type: savings | credit_repayment | fees
  └── state: draft (terrain) → confirmed (caisse)
  └── is_verified: boolean — coché par le manager à la remise physique
  └── action_bulk_confirm() → 1 account.move par agent

credit.payment.wizard  (TransientModel)
  └── line_id, amount_to_pay → appelle line_id.register_payment()

res.config.settings (étendu)
  └── micro_flow_journal_id   → ir.config_parameter 'microflow.journal_id'
  └── max_active_cycles       → ir.config_parameter 'microflow.max_active_cycles'
```

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

## Composant OWL : MicroTabBar

**Fichiers :** `static/src/components/MicroTabBar/MicroTabBar.{js,xml,scss}`
**Rôle :** Barre de navigation entre Épargne et Crédits. Visible uniquement quand l'action courante est `micro.cycle` ou `micro.credit`.
**Enregistrement :** `registry.category("main_components").add("MicroTabBar", { Component })`
**Détection vue active :** écoute `ACTION_MANAGER:UI-UPDATED` sur `this.env.bus` + fallback `popstate`
**Mobile (<768px) :** `position: fixed; bottom: 0; height: 60px` — ajoute `body.mf-tabbar-active` pour le padding contenu
**Desktop (≥768px) :** `position: fixed; top: 56px; height: 48px` — `margin-top: 48px` sur `.o_main_content`
**Couleurs :** Épargne actif `#388E3C`, Crédits actif `#1976D2`, inactif `#f5f7fa`

**Structure du menu (post-refactor) :**
```
MICRO FLOW
├── Tableau de Bord    (Manager)
├── Épargne            (tous — niveau 1)
├── Crédits            (tous — niveau 1)
├── Opérations
│   ├── Mon Récapitulatif    (Agent)
│   └── Toutes les Transactions (Manager)
└── Configuration
    └── Zones          (Manager)
```

---

## Composant OWL : MicroGrid

**Fichiers :** `static/src/components/MicroGrid/MicroGrid.{js,xml,scss}`
**Utilisation :** `<field name="line_ids" widget="MicroGrid" nolabel="1"/>` dans `micro.cycle` form
**API Odoo 18 correcte :**
- `standardFieldProps` pour les props
- `staticList.records` pour accéder aux lignes one2many
- `useService('orm')` + `useService('notification')`
- Enregistré via `registry.category("fields").add("MicroGrid", { component, supportedTypes })`

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
Settings → MICRO FLOW → Journal de collecte (caisse ou banque)
```

Sans le journal, toute activation de cycle ou collecte lève un `UserError`.

---

## Conventions de code

- Journal lu depuis `ir.config_parameter` : `int(self.env['ir.config_parameter'].sudo().get_param('microflow.journal_id', 0))`
- Avant toute création d'account.move : appeler `self._ensure_journal_account(journal)` (auto-affecte le compte si absent)
- `@api.model_create_multi` sur tous les `create()` — pas `@api.model`
- Pas de `tracking=True` sur les champs Selection sans `_inherit = 'mail.thread'`

---

## Fichiers critiques à connaître

| Fichier | Rôle |
|---|---|
| `__manifest__.py` | Dépendances, ordre chargement, assets |
| `security/security_groups.xml` | Groupes (chargé en 1er) |
| `security/record_rules.xml` | Isolation données agent |
| `security/ir.model.access.csv` | Droits CRUD par groupe |
| `models/micro_transaction.py` | action_bulk_confirm, _ensure_journal_account |
| `models/micro_cycle.py` | action_activate (config_param + ligne fees) |
| `views/micro_transaction_views.xml` | Dashboard Kanban + action_micro_dashboard |
| `static/src/components/MicroGrid/MicroGrid.js` | Widget OWL terrain |
| `controllers/controllers.py` | Route /microflow/sw.js |

---

## Commandes utiles

```bash
# Installation fraîche
python odoo-bin -i microflow -d <base> --dev=all

# Mise à jour
python odoo-bin -u microflow -d <base> --dev=all

# Tests
python odoo-bin -d <base> --test-enable --stop-after-init -i microflow
```

---

## Roadmap complète

Voir `docs/ROADMAP.md` pour le plan de travail priorisé avec le statut de chaque module.
