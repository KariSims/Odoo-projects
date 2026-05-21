# ROADMAP — Microflow
> Plan de travail priorisé. Mis à jour : 2026-05-19
> On attaque du plus prioritaire au moins prioritaire.

---

## État actuel — v0.3 (livré)

Tout ce qui suit est **terminé et fonctionnel** :

| Composant | Description | Statut |
|---|---|---|
| Modèles de base | micro.zone, micro.cycle, micro.cycle.line, micro.credit, micro.credit.line, micro.transaction | ✅ |
| Extension res.partner | member_id auto (MF-ZONE-YYYY-MM-SEQ), zone_id, birthdate, GPS | ✅ |
| Activation cycle | Génère les cases + transaction frais adhésion + guard max_active_cycles | ✅ |
| Collecte terrain | register_collection() → micro.transaction + is_paid=True | ✅ |
| Paiement crédit | register_payment() + wizard plein écran mobile (48px montant, 56px bouton) | ✅ |
| MicroGrid OWL | Widget grille tactile : case courante sticky, tap=collecte, cases colorées | ✅ |
| Dashboard Kanban | Transactions draft groupées par agent, toggle is_verified | ✅ |
| Validation groupée | action_bulk_confirm : 1 account.move par agent, auto-affectation compte journal | ✅ |
| Séquences auto | MF-TX/YYYY/00001 (transactions), MF/YYYY/00001 (membres) | ✅ |
| Récapitulatif agent | Vue "Mon Récapitulatif du Jour" (ses transactions draft du jour) | ✅ |
| Règles d'accès | Record rules agent/manager + ACL par groupe | ✅ |
| Configuration | Journal collecte + max cycles via res.config.settings | ✅ |
| PWA Service Worker | Offline queue IndexedDB + Background Sync | ✅ |
| GPS capture | Patch FormController + bouton "Capturer la localisation" | ✅ |
| Tests unitaires | 16 tests : partenaires, cycles, crédits | ✅ |
| README | Installation, groupes, dépannage | ✅ |

---

## LIVRÉ — Navigation onglets Épargne / Crédits

**Sprint v0.4 — 2026-05-19 — TERMINÉ**

| Composant | Description | Statut |
|---|---|---|
| `views/menus.xml` restructuré | Épargne et Crédits au niveau 1 sous MICRO FLOW ; Opérations garde Mon Récapitulatif + Toutes les Transactions | ✅ |
| `MicroTabBar` OWL (`main_components`) | Tab bar Épargne (vert #388E3C) / Crédits (bleu #1976D2), fond coloré sur l'actif | ✅ |
| Mobile : barre fixe en bas (60px) | `position: fixed; bottom: 0` — app-like, `padding-bottom` auto sur le contenu | ✅ |
| Desktop : barre en haut (48px) | `top: 56px` sous la navbar Odoo, décalage `margin-top: 48px` sur le contenu | ✅ |
| Détection automatique de la vue active | Via `ACTION_MANAGER:UI-UPDATED` bus + fallback `popstate` | ✅ |

---

## MODULE 1 — Dashboard Manager complet

**Priorité : P1 — À faire en premier**

Le Kanban existe mais les cartes sont basiques (1 carte = 1 transaction). Le DESIGN_SPEC demande des **cartes agrégées par agent**.

### Ce qui reste

```
┌─────────────────────────────────────┐
│ 👤 [Nom Agent]                      │
│ Zone: [zone_id.name] | [N] membres  │
│ ─────────────────────────────────── │
│ Total remis: [X] CDF                │
│ ▓▓▓▓░░░ [X]/[N] validés            │
│                      [Valider ✓]    │
└─────────────────────────────────────┘
```

**Tâches :**
- [ ] Composant OWL `AgentSummaryCard` ou aggregation via `t-set` dans le template kanban
- [ ] Afficher par colonne/groupe : total CDF collecté, nb membres distincts, zone
- [ ] Barre de progression `is_verified` : X validés / N total
- [ ] **Empty state positif** : quand 0 transactions draft → "✅ Tout validé ! Total : X CDF | Y agents | Z zones"
- [ ] Tri des colonnes par montant décroissant (`default_order` sur le kanban)

**Fichiers à modifier :**
- `views/micro_transaction_views.xml` — template kanban
- `static/src/css/microflow_mobile.scss` — styles cartes agrégées

---

## MODULE 2 — Récapitulatif agent enrichi (end-of-day)

**Priorité : P1**

La vue "Mon Récapitulatif" existe mais n'est qu'une liste. L'agent a besoin de **stats** avant de remettre les fonds.

### Ce qui reste

- [ ] Totaux en pied de page : total collecté CDF, nb versements, nb partiels
- [ ] Sous-total par type (épargne / remboursement / frais)
- [ ] Bouton "Prêt à remettre" → affiche un résumé chiffré à montrer au manager
- [ ] **Rapport PDF imprimable** (qweb template) : récapitulatif journalier signable par agent + manager

**Fichiers à créer/modifier :**
- `report/micro_agent_daily_report.xml` — template QWeb PDF
- `report/micro_agent_daily_report_action.xml` — action rapport
- `views/micro_transaction_views.xml` — footer totaux dans la list view

---

## MODULE 3 — MicroGrid amélioré

**Priorité : P2**

Le widget fonctionne mais manque 2 états prévus au DESIGN_SPEC.

### Ce qui reste

- [ ] **Case partielle** : un crédit payé partiellement → case orange `#FFF8E1` avec montant résiduel affiché (DESIGN_SPEC §3 état PARTIEL)
- [ ] **Champ `amount_paid` sur micro.cycle.line** : permettre un versement partiel d'une case d'épargne (option configurable)
- [ ] **Spinner de chargement** : pendant `onCellTap` → désactiver visuellement la case au lieu d'un simple `state.saving`
- [ ] **Indicateur progression** visible sur la liste des cycles (X/N cases, barre)
- [ ] `inputmode="decimal"` sur le champ montant du wizard (accessibilité mobile, DESIGN_SPEC §7)

**Fichiers à modifier :**
- `static/src/components/MicroGrid/MicroGrid.{js,xml,scss}`
- `models/micro_cycle_line.py` — champ amount_paid optionnel
- `wizard/credit_payment_wizard_views.xml` — inputmode

---

## MODULE 4 — SMS Agent (reçu de confirmation)

**Priorité : P2**

Après validation par le manager (`action_bulk_confirm`), chaque agent reçoit un SMS de confirmation avec le total validé.

### Ce qui reste

- [ ] Dépendance sur `sms_dexchange` (déjà dans le dépôt)
- [ ] Dans `action_bulk_confirm` : après `move.action_post()`, envoyer SMS à `agent.partner_id.mobile`
- [ ] Template SMS : "Microflow: [N] versements validés — Total [X] CDF. Agent: [Nom]. Date: [J/M/A]"
- [ ] Guard : SMS seulement si `sms_dexchange` installé (vérification via `self.env['ir.module.module'].search`)
- [ ] Config : activer/désactiver les SMS dans res.config.settings

**Fichiers à modifier :**
- `models/micro_transaction.py` — action_bulk_confirm (ajout SMS)
- `views/res_config_settings_views.xml` — toggle SMS
- `models/res_config_settings.py` — champ `enable_sms_agent`

---

## MODULE 5 — Zones hiérarchiques

**Priorité : P2**

Le modèle `micro.zone` est plat. Les zones terrain ont souvent une hiérarchie (Ville → Quartier → Rue).

### Ce qui reste

- [ ] Ajouter `parent_id = fields.Many2one('micro.zone', string="Zone parente")`
- [ ] `_parent_name = 'parent_id'` pour le tree ORM
- [ ] Adapter la génération de `member_id` : utiliser la zone racine ou la zone feuille selon config
- [ ] Vue : afficher l'arborescence dans la liste (indentation)
- [ ] Filtre par zone dans le Dashboard Manager (colonne filtrée)

**Fichiers à modifier :**
- `models/micro_zone.py`
- `views/micro_zone_views.xml`

---

## MODULE 6 — Analytique & Reporting

**Priorité : P3**

Tableaux de bord et exports pour le suivi global de l'activité.

### Ce qui reste

- [ ] **Graphiques OWL (ou vues graph Odoo)** :
  - Épargne collectée par semaine (bar chart)
  - Taux de remboursement crédits (line chart)
  - Répartition par zone (pie chart)
- [ ] **Vue pivot** sur micro.transaction (group by agent, type, semaine)
- [ ] **Export Excel** : membres actifs, transactions du mois, portefeuille crédit
- [ ] **Rapport PDF mensuel** : synthèse globale manager (total épargne, total crédit, taux recouvrement)
- [ ] **Tableau de bord analytique** : KPIs clés en tiles (total membres actifs, épargne cumulée, encours crédit)

**Fichiers à créer :**
- `report/micro_monthly_report.xml`
- `views/micro_analytics_views.xml`
- `models/micro_analytics.py` (modèle read-only avec SQL custom si besoin)

---

## MODULE 7 — Crédit avancé

**Priorité : P3**

Le moteur de crédit de base est en place. Cette phase l'enrichit.

### Ce qui reste

- [ ] **Statut automatique** : `micro.credit.state` passe en `closed` quand toutes les lignes `amount_residual == 0`
- [ ] **Taux de défaillance** : champ calculé sur `res.partner` (% de lignes en retard sur ses crédits)
- [ ] **Scoring crédit simple** : score 0-100 basé sur historique paiements (ponctualité, défaillances)
- [ ] **Restructuration** : bouton "Proroger" → crée nouvelles lignes, annule les anciennes
- [ ] **Date d'échéance** : ajouter `date_due` sur `micro.credit.line`, alertes en retard
- [ ] **Caution / garantie** : champ texte ou Many2one vers un autre `res.partner`

**Fichiers à modifier :**
- `models/micro_credit.py`
- `models/micro_credit_line.py`
- `models/res_partner.py` — credit_score, default_rate

---

## MODULE 8 — PWA avancé & Offline robuste

**Priorité : P3**

Le service worker de base est fonctionnel. Cette phase le rend production-ready.

### Ce qui reste

- [ ] **Indicateur hors-ligne visible** dans l'UI Odoo (bandeau orange "Mode hors-ligne — X opérations en attente")
- [ ] **Sync manuelle** : bouton "Synchroniser maintenant" dans Mon Récapitulatif
- [ ] **Résolution de conflits** : si le même enregistrement a été modifié online et offline → afficher diff, laisser l'agent choisir
- [ ] **Notifications push PWA** : rappel quotidien "Vous avez X membres à collecter aujourd'hui"
- [ ] **Mode installation PWA** : manifest.json, icônes, splash screen

**Fichiers à créer/modifier :**
- `static/src/js/service_worker.js` — gestion conflits
- `static/manifest.json` — PWA manifest
- `controllers/controllers.py` — route `/microflow/manifest.json`
- Composant OWL `OfflineBanner`

---

## MODULE 9 — KYC & Gestion documentaire membres

**Priorité : P3**

Identification formelle des membres (requis pour certaines réglementations).

### Ce qui reste

- [ ] **Photo membre** : champ `image_1920` (déjà dans res.partner) — afficher dans la fiche Microflow
- [ ] **Pièce d'identité** : type (CNI/Passeport), numéro, date expiration
- [ ] **Contrat d'adhésion** : PDF généré à la création du membre, signable
- [ ] **Import CSV** : wizard d'import membres en masse avec validation zone + séquence

**Fichiers à créer :**
- `models/micro_member_document.py`
- `report/micro_member_contract.xml`
- `wizard/micro_import_members.py`

---

## MODULE 10 — Tests E2E & Qualité

**Priorité : P3**

Les 16 tests unitaires couvrent la logique métier. Les tests E2E valident l'interface.

### Ce qui reste

- [ ] **Tests E2E Playwright** : parcours agent (activation cycle → collecte case → récapitulatif)
- [ ] **Tests E2E manager** : validation groupée → vérification account.move créé
- [ ] **Tests de charge** : 100 agents, 1000 transactions simultanées
- [ ] Couverture tests unitaires : cas limites (amount=0, installment_count=0 déjà fait, max_cycles)
- [ ] CI/CD : pipeline GitHub Actions avec `--test-enable`

---

## MODULE 11 — Multi-société & Scalabilité

**Priorité : P4 — v2**

- [ ] Multi-company : `company_id` sur tous les modèles, record rules par société
- [ ] Multi-devise : conversion CDF ↔ USD en temps réel
- [ ] API REST externe : exposer `/microflow/api/v1/collections` pour intégration apps tierces
- [ ] App native Flutter (si PWA insuffisante pour le terrain)

---

## Récapitulatif des priorités

| # | Module | Priorité | Effort estimé | Dépendances |
|---|--------|---------|--------------|-------------|
| 1 | Dashboard Manager complet | **P1** | 1-2 jours | aucune |
| 2 | Récapitulatif agent enrichi + PDF | **P1** | 2-3 jours | aucune |
| 3 | MicroGrid amélioré (partiel + UX) | **P2** | 1-2 jours | aucune |
| 4 | SMS Agent (reçu validation) | **P2** | 1 jour | sms_dexchange installé |
| 5 | Zones hiérarchiques | **P2** | 1 jour | aucune |
| 6 | Analytique & Reporting | **P3** | 3-5 jours | modules 1 et 2 |
| 7 | Crédit avancé | **P3** | 3-4 jours | aucune |
| 8 | PWA avancé & Offline robuste | **P3** | 2-3 jours | module 3 |
| 9 | KYC & Documents membres | **P3** | 2-3 jours | aucune |
| 10 | Tests E2E & Qualité | **P3** | 3-5 jours | tous modules stables |
| 11 | Multi-société & Scalabilité | **P4** | 5-10 jours | tous modules livrés |

---

## Ce qu'on attaque en prochain sprint

**Sprint v0.4 — Semaine courante :**

1. Stabiliser l'installation (fix res_partner_views.xml) ← FAIT
2. **MODULE 1** : Dashboard Manager cartes agrégées + empty state
3. **MODULE 2** : Récapitulatif agent + PDF journalier

**Sprint v0.5 — Sprint suivant :**

4. **MODULE 3** : MicroGrid case partielle + inputmode
5. **MODULE 4** : SMS confirmation agent
6. **MODULE 5** : Zones hiérarchiques (si besoin terrain identifié)
