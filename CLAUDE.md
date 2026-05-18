# CLAUDE.md — Odoo-projects

> Contexte de travail pour Claude Code. Mis à jour : 2026-04-27.

---

## 1. Description générale

Dépôt de modules Odoo personnalisés (v18) couvrant la comptabilité, le commerce électronique, le point de vente (POS), l'immobilier, la gestion hôtelière et l'intégration SMS. Développé principalement par KariSims + modules tiers (Cybrosys, OCA, MuK IT).

**Branche principale :** `main`
**Version Odoo cible :** 18.0

---

## 2. Hiérarchie des dossiers

```
Odoo-projects/
│
├── CLAUDE.md                          ← ce fichier
├── SECURITY.md                        ← audit sécurité détaillé
│
├── # === COMPTABILITÉ & FINANCES ===
├── accounting_pdf_reports/            Rapports PDF comptables (Odoo Mates, LGPL-3)
├── base_accounting_kit/               Kit comptabilité complet v18 (Cybrosys, LGPL-3)
├── base_account_budget/               Gestion budgétaire analytique (Cybrosys, LGPL-3)
├── om_account_accountant/             Module principal comptabilité (Odoo Mates, LGPL-3)
├── om_account_asset/                  Gestion des actifs & amortissements
├── om_account_budget/                 Budget vs. réel
├── om_account_daily_reports/          Rapports journaliers (Cash/Day/Bank book)
├── om_account_followup/               Relances clients
├── om_fiscal_year/                    Gestion exercice fiscal
├── om_recurring_payments/             Paiements récurrents automatisés
├── customer_partner_ledger/           Grand livre partenaires
├── origin_invoice_required/           Règle : facture obligatoire avec origine devis
│
├── # === VENTES & E-COMMERCE ===
├── canadadici_addons/                 Canada D'Ici — module principal (KariSims)
├── canadadici_account/                Canada D'Ici — comptabilité
├── canadadici_sales/                  Canada D'Ici — ventes & tarification
├── canadadici_stock/                  Canada D'Ici — stock & livraison
├── canadadici_website/                Canada D'Ici — frontend website
├── harmony/                           Harmony — gestion ventes & paiements (KariSims)
├── harmony_vars/                      Harmony — variables, SMS, champs custom
├── jallow_addons/                     Jallow Motors — POS & inventaire (KariSims)
├── jallow_addons_emab/                Jallow Motors — extension EMAB
├── jallow_addons_food/                Jallow — industrie alimentaire
├── jallow_vars/                       Jallow — variables & configurations
├── emab_gn/                           EMAB Guinée — facturation & rapports
├── website_sale_address_management/   Gestion adresses checkout (Cybrosys, AGPL-3)
├── basic_sale_stock_restrict/         Restriction vente hors stock (basique)
├── sale_stock_restrict/               Restriction vente hors stock (avancée + website)
│
├── # === POINT DE VENTE ===
├── bi_pos_restrict_zero_qty/          Blocage vente qté=0 au POS (BrowseInfo, OPL-1)
├── pos_cash_restriction/              Restriction retrait cash POS
├── pos_receipt_extend/                Tickets POS enrichis avec infos client
│
├── # === SMS & COMMUNICATION ===
├── sms_dexchange/                     Intégration SMS Dexchange API (KariSims)
├── sms_msg91/                         Intégration SMS MSG91 API (KariSims)
│
├── # === IMMOBILIER ===
├── hungpb_real_estate/                Annonces immobilières (basique)
├── real_estate_management_advanced/   Gestion immobilière avancée (contrats, maintenance)
│
├── # === HÔTELLERIE ===
├── at_hotel_management/               Gestion hôtelière (réservations, facturation)
│
├── # === THÈME & UI ===
├── muk_web_theme/                     Thème backend Odoo Community (MuK IT, LGPL-3)
├── muk_web_appsbar/                   Barre navigation apps
├── muk_web_chatter/                   Chatter amélioré
├── muk_web_colors/                    Personnalisation couleurs thème
├── muk_web_dialog/                    Dialogues plein écran
├── report_qweb_element_page_visibility/ Visibilité éléments rapport par page
│
├── # === IA & SCAN ===
│   └── account_invoice_scan_llm/      Scan factures par LLM (langchain)
│
├── # === GESTION IMMOBILIÈRE AVANCÉE ===
│   └── max_immo/                       MaxImmo — disponibilité chambres, occupations (KariSims)
│
└── # === DASHBOARD BI ===
    └── synconics_bi_dashboard/         Dashboard BI interactif v1.0.3 (Synconics, OPL-1) — MODIFIÉ KariSims
```

---

## 3. Analyse fonctionnelle

### 3.1 Comptabilité (modules `om_*` + `base_accounting_kit`)

| Module | Fonctionnalité clé |
|--------|-------------------|
| `om_account_accountant` | Point d'entrée — agrège tous les sous-modules |
| `base_accounting_kit` | PDC, actifs, budgets, rapports, récurrents, limites crédit |
| `om_account_asset` | Cycle de vie actifs, calcul amortissement, écritures journal |
| `om_account_budget` | Comparatif budget/réel par compte analytique |
| `om_fiscal_year` | Verrou de clôture périodique |
| `om_recurring_payments` | Templates paiements planifiés (CRON) |
| `om_account_followup` | Workflow relances automatiques (mail) |
| `accounting_pdf_reports` | Grand livre, Balance, Balance âgée, Audit journal |
| `customer_partner_ledger` | Relevé de compte partenaire avec soldes O/C |

### 3.2 Ventes & E-commerce (modules `canadadici_*`, `harmony*`, `jallow*`)

Trois ensembles clients distincts :

- **Canada D'Ici** : site web Odoo + caisse POS, personnalisation adresses checkout, logique tarification spécifique, gestion stock livraison.
- **Harmony** : module vente avec modes de paiement custom, suivi commandes, intégration SMS via `harmony_vars`.
- **Jallow Motors** : POS + gestion produits, extension EMAB et alimentaire, variables partagées via `jallow_vars`.

### 3.3 SMS (modules `sms_dexchange`, `sms_msg91`)

Deux providers SMS :

| Aspect | sms_dexchange | sms_msg91 |
|--------|--------------|-----------|
| Provider | Dexchange (Afrique) | MSG91 (Inde/International) |
| Endpoint API | `https://api-v2.dexchange-sms.com/api/v1/send/sms` | `https://api.msg91.com/api/v5/flow/` |
| Auth | Bearer token | authkey header |
| Webhook | POST `/dexchange/status` | POST `/msg91/status` |
| Déclencheurs | Confirmation commande vente + commande POS | Confirmation commande vente |
| Config modèle | `dexchange.sms.config` | `msg91.sms.config` |

### 3.4 POS (modules `bi_pos_restrict_zero_qty`, `pos_cash_restriction`, `pos_receipt_extend`)

Extensions du POS Odoo :
- Blocage des articles à stock zéro ou négatif (JS côté client)
- Limitation retrait cash selon solde disponible
- Tickets enrichis avec nom/téléphone/email client

### 3.5 Immobilier & Hôtellerie

- **`hungpb_real_estate`** : Modèle CRUD basique pour annonces (tutoriel Odoo adapté)
- **`real_estate_management_advanced`** : Contrats loyer/vente, suivi maintenance, tableau de bord
- **`at_hotel_management`** : Réservations, gestion chambres, facturation, numérotation séquentielle

---

## 4. Cartographie des dépendances inter-modules

```
om_account_accountant
 ├─ accounting_pdf_reports ─ account
 ├─ om_account_asset ─ account
 ├─ om_account_budget ─ account
 ├─ om_fiscal_year ─ account
 ├─ om_recurring_payments ─ account
 ├─ om_account_daily_reports ─ accounting_pdf_reports
 └─ om_account_followup ─ mail

base_accounting_kit ─ account, sale, account_check_printing, analytic, base_account_budget

canadadici_account ─ canadadici_sales ─ account, delivery, product, sale
canadadici_website ─ website_sale
canadadici_addons ─ account, product, website_sale

harmony ─ harmony_vars ─ base, product, web
sms_dexchange ─ base, base_automation, sale, point_of_sale, sms
sms_msg91 ─ base, base_automation, account, sms

jallow_addons_emab ─ jallow_vars ─ account, sale, stock_delivery, sale_stock
jallow_addons_food ─ account, sale, stock_delivery, sale_stock

muk_web_theme ─ muk_web_chatter, muk_web_dialog, muk_web_appsbar, muk_web_colors
website_sale_address_management ─ website_sale
sale_stock_restrict ─ sale_management, stock, account, website_sale

real_estate_management_advanced ─ base, mail, web
at_hotel_management ─ base, mail, account
account_invoice_scan_llm ─ (aucune dépendance Odoo)
```

---

## 5. Modèles personnalisés notables

| Modèle | Module | Description |
|--------|--------|-------------|
| `dexchange.sms.config` | sms_dexchange | Config API (clé, sender, url) |
| `dexchange.sms.service` | sms_dexchange | Service d'envoi SMS |
| `msg91.sms.config` | sms_msg91 | Config MSG91 |
| `msg91.sms.service` | sms_msg91 | Service d'envoi MSG91 |
| `sms.api.queue.message` | sms_dexchange | File d'attente/historique SMS |
| `estate_property` | hungpb_real_estate | Annonce immobilière |
| `estate_property_offer` | hungpb_real_estate | Offre d'achat/location |
| `hotel_booking` | at_hotel_management | Réservation hôtelière |
| `hotel_room` | at_hotel_management | Inventaire chambres |

---

## 6. Endpoints HTTP exposés

### Publics / non authentifiés (ATTENTION)

| Route | Méthode | Auth | CSRF | Module |
|-------|---------|------|------|--------|
| `/dexchange/status` | POST | none | False | sms_dexchange |
| `/msg91/status` | POST | none | False | sms_msg91 |
| `/shop/send_order_message` | POST | public | False | sms_dexchange, harmony_vars |
| `/shop/get_order_info` | GET/POST | public | False | sms_dexchange |

### Authentifiés

| Route | Méthode | Auth | Module |
|-------|---------|------|--------|
| `/pos/sp/send_sms` | POST | user | sms_dexchange |
| `/shop/address/submit` | POST | public+website | website_sale_address_management |

---

## 7. Intégrations externes

| Service | URL | Auth | Module |
|---------|-----|------|--------|
| Dexchange SMS API | `https://api-v2.dexchange-sms.com/api/v1/send/sms` | Bearer token | sms_dexchange |
| MSG91 API | `https://api.msg91.com/api/v5/flow/` | authkey header | sms_msg91 |

---

## 8. Assets JavaScript notables

- `base_accounting_kit/static/src/js/` — Widgets réconciliation bancaire (KanbanController, ListController)
- `bi_pos_restrict_zero_qty/static/src/app/models/models.js` — Restriction zéro stock POS
- `pos_receipt_extend/static/src/js/PosOrder.js` — Template ticket POS enrichi
- `website_sale_address_management/static/src/js/website_sale_address.js` — Validation adresse
- `muk_web_*/static/` — Thème backend (SCSS + JS intensifs)

---

## 9. Fichiers de sécurité & droits d'accès

- Chaque module produit contient `security/ir.model.access.csv` (droits CRUD par groupe)
- Modules avec `security/security.xml` (groupes + règles d'enregistrement) :
  - `base_accounting_kit`, `sms_dexchange`, `sms_msg91`, `real_estate_management_advanced`, `website_sale_address_management`
- **Voir `SECURITY.md` pour l'audit complet de sécurité**

---

## 10. CRON jobs définis

| Module | Tâche |
|--------|-------|
| `base_accounting_kit` | Création d'écritures récurrentes |
| `om_recurring_payments` | Traitement paiements planifiés |

---

## 11. Conventions de développement observées

- Python : PEP8, héritage Odoo (`models.Model`, `http.Controller`)
- XML : vues nommées `module_name.view_model_type`, IDs préfixés par module
- Pas de tests unitaires dans aucun module custom
- Logging via `_logger = logging.getLogger(__name__)`
- Appels API externes via la bibliothèque `requests` (synchrone, bloquant)

---

## 12. Points d'attention pour les développements futurs

1. Les modules SMS (`sms_dexchange`, `sms_msg91`) sont en cours d'évolution active (fichiers non-commités)
2. Le module `account_invoice_scan_llm` n'a aucune dépendance Odoo déclarée — à compléter
3. Les modules `canadadici_*`, `harmony*`, `jallow*` sont des développements client — coordonner avant modification
4. `muk_web_theme` est incompatible avec `web_enterprise` (exclusion déclarée dans le manifest)

---

## 13. Référence rapide

- **Audit sécurité complet** → `SECURITY.md`
- **Mémoire Claude** → `C:\Users\Incognito\.claude\projects\E--oldPc2-MyGit-Odoo-projects\memory\`

---

## 14. Module `synconics_bi_dashboard` — Extensions KariSims (2026-04-30, màj 2026-04-30)

### 14.1 Feature — Filtre Global de Dashboard

Panneau de filtres de session (non persisté) appliqué simultanément à tous les charts.

**Composant OWL :** `static/src/components/GlobalFilterPanel/GlobalFilterPanel.{js,xml,scss}`

**Filtres disponibles :**
| Filtre | UI | Comportement backend |
|--------|---|---------------------|
| Partenaire direct | Autocomplete `res.partner` (≥2 chars, limit 8) | `('partner_id', '=', id)` sur tout modèle ayant `partner_id` |
| Champ partenaire | Dropdown de 8 champs hardcodés + saisie selon type | `('partner_id.champ', '=', val)` — `'in'` pour many2many |
| Période | Presets : Aujourd'hui / Semaine / Mois / Année en cours / Personnalisé | `(date_filter_field, '>=', date_from)` + `('...', '<=', date_to)` |
| État facture | Dropdown draft/posted/cancel | `('state', '=', val)` uniquement sur `account.move` |

**Champs partenaire exposés (liste fixe dans `get_partner_filter_fields`) :**
| Clé | Label affiché | Type | Notes |
|-----|---------------|------|-------|
| `name` | Nom Entreprise | char | |
| `state_id` | Province | many2one | domain filtré sur pays RDC (`res.country.code='CD'`) |
| `company_id` | Société / Maison mère | many2one | |
| `identifiant` | Numéro d'identification | char/sélection | champ custom |
| `legal_status_code` | Statut juridique | char/sélection | champ custom |
| `legal_status_detail` | Précision statut juridique | char | champ custom |
| `categorie_cotisant` | Catégorie de cotisant | char/sélection | champ custom |
| `secteur` | Secteur d'activité | char/sélection | champ custom |

> Les champs absents de `res.partner` sont silencieusement ignorés (pas d'erreur).

**Payload envoyé au backend (`applyFilters`) :**
```js
{
  partner_id: Number|null,            // id partenaire direct
  partner_field: String,              // nom du champ partenaire sélectionné
  partner_field_value: any,           // valeur brute ou id (M2O)
  date_from: "YYYY-MM-DD"|null,       // calculé par le preset ou saisi manuellement
  date_to:   "YYYY-MM-DD"|null,
  invoice_state: "draft"|"posted"|"cancel"|null
}
```

> `datePeriod` (preset) est purement UI : il auto-remplit `dateFrom`/`dateTo`. Seuls `date_from`/`date_to` partent au backend.

**Flux technique :**
```
GlobalFilterPanel → onApplyFilters → DashboardAmcharts.state.globalFilters
  → DashboardChartWrapper (prop globalFilters)
    → get_chart_data(global_filters=...) [RPC]
      → _build_global_filter_domain(model_name, global_filters) → domain étendu
```

**Méthodes backend ajoutées (`models/dashboard_chart.py`) :**
- `_build_global_filter_domain(model_name, global_filters)` — construit le domain additionnel ; champ M2M → opérateur `in`
- `get_partner_filter_fields()` — retourne la liste fixe des 8 champs (type, comodel, domain) pour le frontend
- `get_chart_data()` accepte le paramètre `global_filters=None`

**Comportement date override :** Quand `date_from`/`date_to` sont présents dans les filtres globaux, `conf.use_global_date = True` est positionné dans `get_chart_data`. Les 4 handlers suivants vérifient ce flag et sautent leur propre filtre de date pour éviter le double-filtrage :
- `get_measurement_group_data` (≈ligne 1973)
- `get_category_value_data` (≈ligne 2572)
- `get_tile_data` (≈ligne 2744)
- `get_list_view_data` (≈ligne 2982)

Les handlers `get_kpi_data`, `get_todo_data`, `get_map_chart_data`, `get_meter_chart_data` **n'ont pas** ce guard.

---

### 14.2 Feature — Groupby multi-dimensionnel V0 (remplace Feature 2)

Permet de croiser **2 axes de regroupement provenant de modèles Odoo différents** avec agrégation SQL directe (performances pour centaines de milliers de lignes).

**Architecture :**
- ORM → filtrage domaine + récupération des IDs : `Model.search(domain).ids`
- SQL direct → agrégation multi-dim : `WHERE id IN %s GROUP BY dim1, dim2`
- Output → format pivot compatible AmCharts grouped bar/column (pas de nouveau composant frontend)

**Nouveaux champs sur `dashboard.chart` (`models/dashboard_chart.py` ≈ligne 515) :**

*Dimension 1 (obligatoire pour activer le multi-dim) :*
| Champ | Type | Description |
|-------|------|-------------|
| `dim1_link_field_id` | Many2one → `ir.model.fields` | Champ M2O du modèle de base vers un modèle lié (ex: `partner_id`) |
| `dim1_related_model_id` | Many2one → `ir.model` (computed+store) | Modèle lié, déduit de `dim1_link_field_id.relation` |
| `dim1_group_field_id` | Many2one → `ir.model.fields` | Champ de regroupement sur le modèle lié (ex: `industry_id`). Si Many2one : 2e JOIN automatique sur le libellé |

*Dimension 2 (optionnelle) :*
| Champ | Type | Description |
|-------|------|-------------|
| `enable_dim2` | Boolean | Activation dim 2 (défaut False) |
| `dim2_link_field_id` | Many2one → `ir.model.fields` | Liaison vers un 2e modèle (optionnel, laissez vide pour champ direct) |
| `dim2_related_model_id` | Many2one → `ir.model` (computed+store) | Modèle lié dim 2 |
| `dim2_target_model_id` | Many2one → `ir.model` (computed, non store) | Modèle effectif pour domain de `dim2_group_field_id` |
| `dim2_group_field_id` | Many2one → `ir.model.fields` | Champ de regroupement dim 2 (ex: `invoice_date`) |
| `dim2_time_granularity` | Selection | day/week/month/quarter/year — applique `DATE_TRUNC` + `TO_CHAR` |

**Activation :** `conf.use_multidim = bool(dim1_link_field_id AND dim1_group_field_id)` — calculé dans `_init_configuration`.

**Méthodes Python ajoutées :**
- `_get_multidim_data_sql(conf_obj, record_ids)` — construit et exécute la requête SQL avec JOINs dynamiques (≤3 JOINs max : dim1_rel, dim1_target si M2O, dim2_rel/dim2_target)
- `_format_multidim_prepared_data(rows, conf_obj)` — pivote les lignes SQL en format `[{category, " - série1": val, " - série2": val}]` compatible AmCharts
- `get_multidim_chart_data(conf_obj)` — handler principal : validation → ORM search → SQL → format

**Dispatch dans `get_chart_data` :**
```python
if conf.use_multidim and chart_type in _multidim_compatible:
    prepared_data = self.get_multidim_chart_data(conf)
else:
    prepared_data = chart_handlers[chart_type](conf)  # chemin classique inchangé
```
`_multidim_compatible` = `{area, bar, column, doughnut, line, stackedcolumn, radial, scatter}`

**Bug fix inclus — `check_conf_obj` :** fallback `measurement_field_id` (singular) accepté quand `measurement_field_ids` (plural M2M) est vide, pour les charts bar/column qui utilisaient parfois un seul champ.

**Charts supportés :** Tous sauf `kpi`, `tile`, `meter_chart`, `map_chart`, `to_do`, `list`.

**Vue XML** (`views/dashboard_chart_view.xml` ≈ligne 153) : Section "Regroupement multi-dimensionnel" avec sous-sections Dim 1 et Dim 2. `dim2_target_model_id` (champ invisible) pilote le domain de `dim2_group_field_id` selon que `dim2_link_field_id` est renseigné ou non.

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
