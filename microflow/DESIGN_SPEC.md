# MICRO FLOW — Design Specification
> Généré par /plan-design-review — 2026-05-17
> Mis à jour : 2026-05-27 (v1.4)

---

## 1. Palette & Thème

```
Primaire    : #1976D2  (Odoo Blue standard — cohérence backend)
Succès/Payé : #388E3C  (vert terrain — case payée, validation OK)
Attente     : #F57C00  (orange — brouillon, à valider)
Danger      : #D32F2F  (rouge — erreur, dépassement)
Annulation  : #B71C1C  (bordeaux — case en attente d'approbation annulation)
Surface     : #FFFFFF
Fond app    : #F5F7FA
Texte       : #212121  (contraste fort, lisible en plein air)

Typographie : Odoo v18 standard (Lato/system). Ne pas surcharger.
Taille min body terrain : 16px
Taille chiffres montants : 20px minimum
```

**Pas de thème tiers** — Odoo Community standard.

---

## 2. Architecture d'Information

### Menu principal

```
MICRO FLOW
├── Tableau de Bord       ← OWL client action Manager (KPI cards + transactions)
├── Épargne               ← Cycles d'épargne (kanban urgence + list + form)
├── Crédits               ← Gestion crédits
├── Opérations
│   ├── Mon Récapitulatif ← transactions du jour de l'agent (agent only)
│   └── Toutes les Transactions ← manager only
└── Configuration
    └── Zones             ← micro.zone
```

### Hiérarchie visuelle par écran

**Écran Terrain — Grille de Collecte (priorité 1 agent)**
```
PRIMAIRE  : Devise + montant par case + cases payées / total
SECONDAIRE: Grille complète scrollable (cases colorées par état)
TERTIAIRE : Nom membre, ID (MF-...), indicateur pré-collecte si applicable
```

**Écran Terrain — Wizard Versement (plein écran mobile)**
```
PRIMAIRE  : Champ montant (font 48px, inputmode="decimal", clavier numérique auto)
SECONDAIRE: Case n°X | Montant attendu | Reste dû (si partiel)
TERTIAIRE : [Valider paiement] (pleine largeur, 56px) | Annuler (text link)
```

**Écran Manager — Tableau de Bord OWL**
```
PRIMAIRE  : 5 KPI cards (épargne, remboursements, frais, crédits en attente, crédits actifs)
SECONDAIRE: Transactions terrain avec toggle "Reçu" + checkboxes sélection
TERTIAIRE : [Valider la sélection (N)] | [Tout Valider]
```

**Écran Manager — Kanban Cycles (Épargne)**
```
Colonne "Corrections — À approuver" : cycles actifs avec case_count_requested ≠ 0 (badge 🔢 violet)
Colonne "Annulations — À approuver" : cycles actifs avec pending_uncheck_count > 0 (badge ⚠️ rouge)
Colonne "À traiter"  : cycles pre_active, activation Manager requise (badge ⚡ bleu)
Colonne "En cours"   : cycles actifs sans action requise
Colonne "Brouillon" / "Terminé" : états passifs
```

**Écran Manager — Dashboard (all-clear)**
```
Si 0 transaction draft ET 0 crédit en attente :
  Bannière verte "✓ Tout validé !" + sous-titre + badge orange si cycles encore ouverts
Sinon :
  KPI cards + tableau transactions + récapitulatif par agent (cartes pliables)
```

---

## 3. Composant Grille de Collecte (OWL Custom)

**Composant OWL `<MicroGrid>`** — widget field `one2many`.

### États des cases

```
Vide              : background #F5F7FA, border 1px #CFD8DC
Pending-check     : background #E3F2FD, border 2px #1565C0, icône ☑, pulse bleu animé
Payée             : background #E8F5E9, checkmark ✓ vert #388E3C + rang chronologique
Approval-pending  : background #FFEBEE, border 2px #B71C1C, badge ⏳ (annulation Manager requise)
```

### Flux de tap (màj v0.9)

```
Case vide :
  Tap 1 → pendingCheckId (bleu pulsant, icône ☑, timer 2s)
         → toast "Double-tap pour confirmer la collecte"
  Tap 2 (même case, dans 2s) → register_collection() côté serveur
         → animation justPaidId (scale + halo vert 450ms)
         → notification "Case N ✓ — X CDF / Total : Y / Z CDF"

Case payée :
  Tap → ConfirmationDialog Odoo natif ("Annuler la collecte ? — Confirmer / Garder")
    Confirmer → unregister_collection()
      Si status='done'  → toast info "Collecte annulée"
      Si status='pending' → toast warning "Demande soumise au Manager"

Case approval-pending :
  Tap → toast warning "Demande d'annulation déjà soumise au Manager" + return immédiat
```

### Règles serveur (`unregister_collection`)

- Bloqué si la transaction liée est `confirmed` (déjà validée par le Manager) → UserError
- Manager → annulation immédiate à tout moment
- Agent + ≤ 120s depuis `transaction.create_date` → annulation immédiate
- Agent + > 120s → `uncheck_pending=True`, retourne `{'status': 'pending'}`

### Affichage `collection_order`

Rang chronologique (1, 2, 3…) affiché en exposant top-left sur chaque case payée.
`.mf-cell-order` : position absolute, 7px, couleur vert #388E3C.

### Responsive grille

```
Mobile 375px  : 5 colonnes × N lignes, cases 65×65px
Tablet 768px  : 7 colonnes, cases 72×72px
Desktop 1024+ : vue form Odoo standard (non prioritaire)
```

### Architecture OWL

```
static/src/components/
  MicroGrid/
    MicroGrid.js      ← composant principal
    MicroGrid.xml     ← template
    MicroGrid.scss    ← styles cases + animations
```

**Limite One2many (important) :** Ajouter `limit="500"` sur le `<list>` subview pour dépasser la limite Odoo de 40 enregistrements par défaut.

---

## 3b. Module Crédit — Workflow & Design

### State machine

```
draft ──[Soumettre]──▶ pending ──[Accorder]──▶ active ──[Solder]──▶ closed
  ↑                       │
  └───────[Rejeter]────────┘
```

### Champs clés

| Champ | Modèle | Notes |
|-------|--------|-------|
| `agent_id` | micro.credit | Défaut = créateur. Réassignable par Manager uniquement |
| `currency_id` | micro.credit | Éditable en draft, verrouillé dès active/closed |
| `date_granted` | micro.credit | Posée par Manager à l'accord |
| `installment_interval` + `installment_period` | micro.credit | Jours/Semaines/Mois |
| `amount_total` | micro.credit | Capital × (1 + rate%) — computed stored |
| `amount_residual_total` | micro.credit | Somme des residuals — computed stored |
| `sequence` | micro.credit.line | N° d'échéance |
| `date_due` | micro.credit.line | date_granted + N × intervalle |
| `is_overdue` | micro.credit.line | date_due < today AND residual > 0 |
| `currency_id` | micro.credit.line | related='credit_id.currency_id' |

### Couleurs tableau échéancier

```
Vert   (decoration-success) : amount_residual == 0          → payée
Orange (decoration-warning) : not is_overdue AND residual>0 → à venir
Rouge  (decoration-danger)  : is_overdue                    → dépassée impayée
```

### Sécurité crédits

- Agent : voit uniquement ses crédits (`agent_id = user`) — miroir cycles
- Manager : voit tout + peut réaffecter `agent_id`
- Écriture `agent_id` bloquée côté serveur (`write()` override) pour les non-managers

---

## 4. États d'Interaction

| Fonctionnalité | LOADING | EMPTY | ERROR | SUCCESS | PARTIEL |
|---------------|---------|-------|-------|---------|---------|
| Grille collecte | Spinner Odoo | "Aucune case — activez le cycle" | Erreur réseau + retry | Case verte ✓ + rang | N/A |
| Wizard versement | Bouton désactivé | N/A | Montant > dû → message inline | Case cochée, retour | Montant partiel accepté |
| Dashboard Manager | Skeleton cards | N/A | Toast erreur | Toast succès N tx | X/Y validés |
| Validation masse | Barre progression X/Y | N/A | Item échoué isolé | Toast "N transactions confirmées" | Partiel possible |
| GPS capture | "Localisation en cours..." | N/A | "GPS refusé — saisie manuelle" | Coords affichées readonly | N/A |
| Brouillon offline | Indicateur "Hors ligne" | N/A | N/A | Sync auto dès connexion | N/A |

---

## 5. Parcours Utilisateur

### Agent Terrain (journée type)

```
1. Ouvre l'app (PWA) → voit ses cycles actifs
2. Crée un nouveau cycle → saisit devise, membre, nombre de cases, montant/case
3. Clique "Activer le Cycle" → N cases preview créées (pré-collecte)
4. Collecte les premiers versements via MicroGrid (double-tap pour cocher)
5. Remet les fonds au Manager + montre l'écran "Pré-collecte en cours"
6. Après activation Manager : collecte les cases restantes au fil des jours
7. Fin de journée → récapitulatif "Mon Récapitulatif" avant remise de fonds
```

### Manager (validation journalière)

```
1. Ouvre MICRO FLOW → Tableau de Bord (KPI cards + transactions)
2. Vérifie physiquement les fonds reçus, coche "Versement Reçu" par agent
3. Clique "Tout Valider" ou "Valider la sélection" → écritures comptables générées
4. Vérifie le Kanban Épargne : cycles "À traiter" (pré-collecte en attente)
5. Pour chaque cycle pre_active : inspecte les versements et clique "Activer le Cycle Complet"
6. Traite les demandes d'annulation en attente dans les formulaires de cycle
```

---

## 6. Décisions Techniques

### Cycles simultanés (décision 7B)

- N cycles actifs par membre autorisés
- Champ `max_active_cycles` dans `res.config.settings` (configurable Manager)
- Défaut: 1 (valeur conservatrice)

### Identifiant membre (décision 7A)

- **`member_id`** → format MF-ZONE-ANNEE-MOIS-SEQ — géré par microflow

### Plateforme terrain (décision 6A)

- PWA (Progressive Web App)
- Brouillon local si hors ligne (service worker)
- Sync automatique à la reconnexion

### Devise par cycle/crédit (décision D1 — v0.9)

- Devise choisie à la création (cycle ou crédit), parmi les devises actives Odoo
- Verrouillée après premier versement (épargne) ou à l'activation (crédit)
- `currency_id` = premier champ visible du formulaire (avant membre, montant, etc.)
- Les lignes (cycle.line, credit.line) héritent via `related` — pas de default autonome

### Commission épargne (décision D2 — v0.9)

- Pas de pourcentage de commission pour l'épargne
- L'institution réserve 1 case à la fin du cycle (convention terrain, non computée)
- `commission_rate` retiré du formulaire agent ; champ conservé dans le modèle pour compatibilité

### Sens comptable épargne (décision D3 — v0.9)

- Débit caisse / Crédit compte Dépôts Membres (passif courant, configurable)
- Contra-exemple banni : ne jamais débiter le compte client pour une collecte épargne

### Multi-devise comptable (décision D4 — v1.4)

- `_build_move_lines()` gère désormais la multi-devise complète
- Si devise groupe ≠ devise société : `debit`/`credit` = montants convertis ; `amount_currency` (négatif côté crédit) + `currency_id` sur toutes les lignes
- `action_bulk_confirm()` groupe par `(agent, currency)` — une `account.move` par combinaison
- `savings_repayment_wizard` applique le même pattern
- La `account.move` reçoit `currency_id` si devise étrangère

### Post-paiement (décision 3A)

- Après validation wizard → retour à la liste des membres du jour

---

## 7. Responsive & Accessibilité

```
Touch targets : minimum 44×44px (cases 65px — OK)
Contraste    : minimum 4.5:1 WCAG AA sur tous les textes
Labels       : tous les champs <label> visible (pas de placeholder-seul)
Focus        : outline Odoo standard (ne pas supprimer)
inputmode    : "decimal" sur le champ montant wizard
Wizard mobile: full-screen (pas de pop-up sur 375px)
```

---

## 8. Dette Technique Connue

| Réf | Description | Impact | Décision |
|-----|-------------|--------|---------|
| 6.1 | Pas de verrou optimiste sur les cases (double-collecte concurrente) | Faible — PostgreSQL garantit | Acceptable |
| 6.2 | `transaction.create_date` comparé en UTC pour la fenêtre 2-min | Risque si déploiement multi-fuseau | À corriger si multi-timezone |
| 6.3 | `len(self.line_ids)` au lieu de `max(sequence)` dans `action_activate()` | Mineur | Acceptable |
| 6.4 | `_do_unregister()` supprime physiquement la transaction (`unlink`) — pas d'audit trail | Pas de traçabilité annulation | À corriger avant production |
| 6.5 | Commission épargne non imputée en compta (reporting seul) | Faible si 1 case réservée | Décision maintenue |
| 6.6 | `_build_move_lines()` ne gère pas le multi-devise (`amount_currency`) | Erreur si devise cycle ≠ devise société | **Résolu v1.4** — Option B complète |

---

## 9. Questions résolues

Toutes les questions ouvertes des versions antérieures ont été tranchées :

1. **`micro.zone`** : champs `name`, `code`, `commission_rate`, `active` — suffisant pour v0
2. **Dashboard Kanban** : groupé par urgence (`kanban_urgency_state`) — cycles à traiter en priorité
3. **`max_active_cycles`** par défaut : 1
4. **Devise** : par cycle/crédit, verrouillée après 1er versement
5. **Commission** : pas de % pour l'épargne — 1 case réservée (convention)

---

## 10. NOT in scope (design déféré)

- Thème tiers (MuK IT) — Odoo standard suffisant pour v0
- App native (Flutter/React Native) — PWA couvre le besoin terrain
- Reçu SMS/imprimable pour les agents — scope v1 (provider : MSG91 via `sms_msg91`, dépendance souple)
- ~~Hiérarchie de zones (zones imbriquées)~~ — **Livré v1.4** (`parent_id`, `complete_name`, anti-récursion)
- ~~Multi-devise comptable dans account.move~~ — **Livré v1.4** (Option B complète)
- Résolution de conflits offline sophistiqué — scope v1

## GSTACK REVIEW REPORT

| Review | Trigger | Runs | Status |
|--------|---------|------|--------|
| Eng Review | `/plan-eng-review` | 1 | Résolu (v0.9) |
| Design Review | `/plan-design-review` | 1 | Résolu (v0.9) |
