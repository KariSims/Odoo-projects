# ROADMAP — Microflow
> Plan de travail priorisé. Mis à jour : 2026-05-27 (v1.4)

---

## État actuel — v1.4 (livré)

Tout ce qui suit est **terminé et fonctionnel** :

| Composant | Description | Statut |
|---|---|---|
| Modèles de base | micro.zone, micro.cycle, micro.cycle.line, micro.credit, micro.credit.line, micro.transaction | ✅ |
| Extension res.partner | member_id auto (MF-ZONE-YYYY-MM-SEQ), zone_id, birthdate, GPS | ✅ |
| Zones hiérarchiques | parent_id + complete_name (cascade) + anti-récursion | ✅ v1.4 |
| Machine à états cycle | draft → pre_active → active → closed | ✅ |
| Activation 2 étapes | action_agent_start_collecting (preview N cases) + action_activate Manager (cases restantes) | ✅ |
| Config prévisualisation | microflow.draft_case_count (ir.config_parameter, défaut 5) | ✅ |
| Collecte terrain | register_collection() → micro.transaction + is_paid=True + collection_order | ✅ |
| Rang de collecte | collection_order (Integer) sur cycle.line — rang chronologique affiché en exposant | ✅ |
| Épargne variable | cycle_type=variable, register_collection(amount=X), amount_collected sur ligne | ✅ |
| Annulation 2-min | Fenêtre 120s agent ; au-delà → escalade Manager (uncheck_pending, approve/reject) | ✅ |
| Correction de cases | case_count_requested + approve/reject par Manager | ✅ |
| Paiement crédit | register_payment() + wizard plein écran mobile (48px montant, 56px bouton) | ✅ |
| Transfert épargne→crédit | savings.repayment.wizard : prélève sur épargne pour rembourser une échéance | ✅ |
| MicroGrid OWL | Widget grille tactile : double-tap cocher, dialog décocher, case approval-pending | ✅ |
| Limite MicroGrid | limit="500" sur subview — dépasse la limite Odoo 40 par défaut | ✅ |
| Devise par cycle/crédit | currency_id éditable à la création, verrouillé après 1er versement | ✅ |
| Multi-devise comptable | amount_currency + currency_id sur move lines ; groupement bulk_confirm par (agent, devise) | ✅ v1.4 |
| Dashboard Manager OWL | 5 KPI cards + transactions + sélection + validation + cartes agent agrégées | ✅ v1.4 |
| Empty state Dashboard | Bannière "Tout validé !" quand 0 transaction en attente | ✅ v1.4 |
| Kanban urgence | kanban_urgency_state (6 valeurs) : correction_pending > uncheck_pending > to_process > active | ✅ |
| Validation groupée | action_bulk_confirm : 1 account.move par (agent, devise) | ✅ |
| Sens comptable épargne | Débit caisse / Crédit compte Dépôts Membres (passif courant) | ✅ |
| Compte dépôts | micro_savings_account_id dans res.config.settings | ✅ |
| Commission épargne | Supprimé du formulaire agent — modèle métier = 1 case réservée | ✅ |
| Séquences auto | MF-TX/YYYY/00001 (transactions), MF/YYYY/00001 (membres) | ✅ |
| Récapitulatif agent | Vue "Mon Récapitulatif du Jour" (ses transactions draft du jour) | ✅ |
| Home actions | Connexion → ouvre MICRO FLOW (agent→Épargne, manager→Dashboard) | ✅ v1.4 |
| Règles d'accès | Record rules agent/manager + ACL par groupe | ✅ |
| Configuration | Journal + max cycles + cases preview + compte dépôts + bouton rattrapage home actions | ✅ |
| PWA Service Worker | Offline queue IndexedDB + Background Sync | ✅ |
| GPS capture | Patch FormController + bouton "Capturer la localisation" | ✅ |
| post_init_hook | Hook d'installation (home actions agent/manager) correctement exporté | ✅ |
| Tests unitaires | 76 tests sur 6 fichiers (cycles, crédits, zones, home actions, transfert épargne) | ✅ v1.4 |

---

## MODULE 1 — Dashboard Manager complet

**Priorité : P1 — Partiellement livré**

### Livré (v1.4)

- [x] **Empty state positif** : bannière verte "✓ Tout validé !" + badge cycles ouverts
- [x] **Cartes agent agrégées** : récapitulatif par agent avec total + barre progression reçus, section pliable

### Ce qui reste

- [ ] **Totaux par zone** dans le dashboard (filtre zone sur les transactions)
- [ ] **Rapport PDF journalier** à imprimer pour l'agent (récapitulatif signable)

**Fichiers à modifier :**
- `static/src/components/ManagerDashboard/ManagerDashboard.{js,xml,scss}`
- `report/micro_agent_daily_report.xml` (à créer)

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
- `views/micro_transaction_views.xml` — footer totaux dans la list view

---

## MODULE 3 — MicroGrid amélioré

**Priorité : P2**

### Ce qui reste

- [ ] **Case partielle** : versement partiel d'une case d'épargne → case orange `#FFF8E1` avec montant résiduel affiché
- [ ] **Champ `amount_paid` sur micro.cycle.line** : permettre un versement partiel (option configurable)
- [ ] **Spinner de chargement** : pendant `onCellTap` → désactiver visuellement la case
- [ ] **Indicateur progression** visible sur la liste des cycles (X/N cases, barre)

**Fichiers à modifier :**
- `static/src/components/MicroGrid/MicroGrid.{js,xml,scss}`
- `models/micro_cycle_line.py` — champ amount_paid optionnel

---

## MODULE 4 — SMS Agent (reçu de confirmation)

**Priorité : P2 — En attente**

Provider retenu : **MSG91** via `sms_msg91` (dépendance souple — si non installé, feature silencieusement ignorée).

### Ce qui reste

- [ ] Dans `action_bulk_confirm` : après `move.action_post()`, appeler `_notify_agents_sms()` si toggle activé
- [ ] `_notify_agents_sms()` : boucle par agent, construit message récapitulatif, appelle `msg91.sms.service`
- [ ] Guard : `'msg91.sms.service' in self.env` (soft dependency)
- [ ] Config : champ `microflow_sms_notify_agent` (Boolean) dans `res.config.settings` + vue

**Fichiers à modifier :**
- `models/micro_transaction.py` — action_bulk_confirm (ajout SMS)
- `views/res_config_settings_views.xml` — toggle SMS
- `models/res_config_settings.py` — champ `enable_sms_agent`

---

## MODULE 5 — Zones hiérarchiques ✅ LIVRÉ v1.4

**Priorité : P2 — Terminé**

- [x] `parent_id` + `_parent_name` + anti-récursion (`_check_recursion`)
- [x] `complete_name` (computed+stored, cascade sur renommage parent)
- [x] `child_ids` peuplé automatiquement
- [x] `member_id` utilise le code de la zone **feuille**
- [x] Vue liste + formulaire mis à jour (notebook "Sous-zones")
- [x] 10 tests dans `tests/test_micro_zone.py`

### Ce qui reste (scope v1)

- [ ] Filtre par zone dans le Dashboard Manager

---

## MODULE 6 — Analytique & Reporting

**Priorité : P3**

### Ce qui reste

- [ ] Vue pivot sur micro.transaction (group by agent, type, semaine)
- [ ] Export Excel : membres actifs, transactions du mois, portefeuille crédit
- [ ] Rapport PDF mensuel : synthèse globale manager (total épargne, total crédit, taux recouvrement)
- [ ] Tableau de bord analytique : KPIs clés en tiles (total membres actifs, épargne cumulée, encours crédit)
- [ ] Graphiques Odoo natifs (bar chart épargne/semaine, line chart remboursements, pie chart zones)

**Fichiers à créer :**
- `report/micro_monthly_report.xml`
- `views/micro_analytics_views.xml`

---

## MODULE 7 — Crédit avancé

**Priorité : P3**

### Ce qui reste

- [ ] **Statut automatique** : `micro.credit.state` passe en `closed` quand toutes les lignes `amount_residual == 0`
- [ ] **Taux de défaillance** : champ calculé sur `res.partner` (% de lignes en retard)
- [ ] **Scoring crédit simple** : score 0-100 basé sur historique paiements
- [ ] **Restructuration** : bouton "Proroger" → crée nouvelles lignes, annule les anciennes
- [ ] **Caution / garantie** : champ texte ou Many2one vers un autre `res.partner`

**Fichiers à modifier :**
- `models/micro_credit.py`
- `models/micro_credit_line.py`
- `models/res_partner.py` — credit_score, default_rate

---

## MODULE 8 — PWA avancé & Offline robuste

**Priorité : P3**

### Ce qui reste

- [ ] **Indicateur hors-ligne visible** dans l'UI Odoo (bandeau orange "Mode hors-ligne — X opérations en attente")
- [ ] **Sync manuelle** : bouton "Synchroniser maintenant" dans Mon Récapitulatif
- [ ] **Résolution de conflits** : si le même enregistrement a été modifié online et offline → diff + choix agent
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

### Ce qui reste

- [ ] **Photo membre** : champ `image_1920` — afficher dans la fiche Microflow
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

### Livré (v1.4) — 76 tests unitaires backend

| Fichier | Tests | Couverture |
|---|---|---|
| `test_micro_cycle.py` | 37 | cycles, collecte, comptabilité, variable, correction de cases |
| `test_savings_transfer.py` | 13 | transfert épargne→crédit, wizard, écritures |
| `test_micro_credit.py` | 8 | workflow crédit |
| `test_res_partner.py` | 3 | member_id, unicité, zone |
| `test_micro_zone.py` | 10 | hiérarchie, complete_name, anti-récursion |
| `test_res_users.py` | 5 | home actions, groupes, batch |

### Ce qui reste

- [ ] **Tests E2E Playwright** : parcours agent (activation cycle → collecte case → récapitulatif)
- [ ] **Tests E2E manager** : validation groupée → vérification account.move créé
- [ ] **Tests de charge** : 100 agents, 1000 transactions simultanées
- [ ] CI/CD : pipeline GitHub Actions avec `--test-enable`

---

## MODULE 11 — Multi-société & Scalabilité

**Priorité : P4 — v2**

- [ ] Multi-company : `company_id` sur tous les modèles, record rules par société
- [x] ~~Multi-devise comptable~~ : `amount_currency` dans account.move.line — **Livré v1.4**
- [ ] API REST externe : exposer `/microflow/api/v1/collections` pour intégration apps tierces
- [ ] App native Flutter (si PWA insuffisante pour le terrain)

---

## Récapitulatif des priorités

| # | Module | Priorité | Effort estimé | Statut |
|---|--------|---------|--------------|--------|
| 1 | Dashboard Manager complet (PDF) | **P1** | 1 jour | Partiel — empty state + cartes agent ✅ |
| 2 | Récapitulatif agent enrichi + PDF | **P1** | 2-3 jours | À faire |
| 3 | MicroGrid amélioré (case partielle + UX) | **P2** | 1-2 jours | À faire |
| 4 | SMS Agent (MSG91, reçu validation) | **P2** | 1 jour | En attente |
| 5 | Zones hiérarchiques | **P2** | — | ✅ Livré v1.4 |
| 6 | Analytique & Reporting | **P3** | 3-5 jours | À faire |
| 7 | Crédit avancé | **P3** | 3-4 jours | À faire |
| 8 | PWA avancé & Offline robuste | **P3** | 2-3 jours | En attente (conflits offline) |
| 9 | KYC & Documents membres | **P3** | 2-3 jours | À faire |
| 10 | Tests E2E & Qualité | **P3** | 3-5 jours | Partiel — 76 tests backend ✅ |
| 11 | Multi-société & Scalabilité | **P4** | 5-10 jours | Partiel — multi-devise ✅ |
