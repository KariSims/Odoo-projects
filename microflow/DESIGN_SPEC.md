# MICRO FLOW — Design Specification
> Généré par /plan-design-review — 2026-05-17
> Basé sur CDC_TECHNIQUE_v0.docx

---

## 1. Palette & Thème

```
Primaire    : #1976D2  (Odoo Blue standard — cohérence backend)
Succès/Payé : #388E3C  (vert terrain — case payée, validation OK)
Attente     : #F57C00  (orange — brouillon, à valider)
Danger      : #D32F2F  (rouge — erreur, dépassement)
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

### Menu principal (màj 2026-05-19)
```
MICRO FLOW
├── Tableau de Bord       ← Vue Kanban Manager (priorité d'ouverture)
├── Épargne               ← Cycles d'épargne (onglet natif Odoo, fond vert #4e7a55 si actif)
├── Crédits               ← Gestion crédits  (onglet natif Odoo, fond bleu #2e6da4 si actif)
├── Opérations
│   ├── Mon Récapitulatif ← transactions du jour de l'agent (agent only)
│   └── Toutes les Transactions ← manager only
└── Configuration
    └── Zones             ← micro.zone
```

> MicroTabBar (composant OWL custom) supprimé — 2026-05-19.
> La coloration des onglets Épargne/Crédits est gérée par CSS pur dans
> `microflow_mobile.scss` via `.o_menu_sections [data-menu-xmlid].o_active`.
> Couleurs harmonisées avec le marron natif Odoo (#875A7B) :
> - Épargne : vert forêt chaud `#4e7a55`
> - Crédits  : bleu acier chaud `#2e6da4`

### Hiérarchie visuelle par écran

**Écran Terrain — Grille de Collecte (priorité 1 agent)**
```
PRIMAIRE  : Case courante (sticky top, surbrillance #1976D2, tap immédiat)
SECONDAIRE: Grille complète scrollable (cases colorées par état)
TERTIAIRE : Nom membre, ID (MF-...), compteur (X/31 payées), total collecté
```

**Écran Terrain — Wizard Versement (plein écran mobile)**
```
PRIMAIRE  : Champ montant (font 48px, inputmode="decimal", clavier numérique auto)
SECONDAIRE: Case n°X | Montant attendu | Reste dû (si partiel)
TERTIAIRE : [Valider paiement] (pleine largeur, 56px) | Annuler (text link)
```

**Écran Manager — Tableau de Bord Kanban**
```
PRIMAIRE  : Agents avec remises en attente (ordre: montant décroissant)
SECONDAIRE: Montant par carte, nombre clients, zone
TERTIAIRE : [Tout Valider], filtres zone
```

### Carte Kanban Agent (spec champs)
```
┌─────────────────────────────────────┐
│ 👤 [Nom Agent]                      │
│ Zone: [zone_id.name] | [N] clients  │
│ ─────────────────────────────────── │
│ Total remis: [X] CDF                │
│ ▓▓▓▓░░ [X]/[N] validés             │
│                      [Valider ✓]    │
└─────────────────────────────────────┘
```

---

## 3. Composant Grille de Collecte (OWL Custom)

**Décision 7C:** Composant OWL `<MicroGrid>` — remplace la `<list>` actuelle.

### États des cases
```
Vide              : background #F5F7FA, border 1px #CFD8DC
Courante          : background #E3F2FD, border 2px #1976D2, box-shadow pulse animé
Payée             : background #E8F5E9, checkmark ✓ vert #388E3C
Pending-uncheck   : background #FFF3E0, border 2px #F57C00, icône ↩, pulse orange animé
Partielle         : background #FFF8E1, border #F57C00 + montant résiduel
```

### Double-tap pour décocher (màj 2026-05-21)

Comportement : tap sur une case **payée** (verte) déclenche une confirmation avant annulation.

```
Tap 1 sur case payée
  → case passe en état "pending-uncheck" (orange pulsant, icône ↩)
  → toast "Case N — appuyez à nouveau pour annuler cette collecte"
  → minuterie 3 secondes

  Tap 2 sur la même case dans les 3 secondes
    → appel unregister_collection() côté serveur
    → case redevient vide / courante

  Aucun second tap (expiration)
    → case revient en état payée normal

Tap sur une autre case
  → annule la pending-uncheck en cours, coche la nouvelle case
```

**Règles serveur (`unregister_collection`) :**
- Bloqué si la transaction liée est `confirmed` (déjà validée par le Manager)
- Agent : peut décocher uniquement le jour même de la collecte (`create_date.date() == today`)
- Manager : peut décocher à tout moment (bypass de la règle de date)
- Back-référence via `micro.transaction.cycle_line_id` (Many2one → micro.cycle.line)

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
    MicroGrid.scss    ← styles cases
```

---

## 3b. Module Crédit — Workflow & Design (màj 2026-05-20)

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
| `date_granted` | micro.credit | Posée par Manager à l'accord |
| `installment_interval` + `installment_period` | micro.credit | Jours/Semaines/Mois |
| `amount_total` | micro.credit | Capital × (1 + rate%) — computed stored |
| `amount_residual_total` | micro.credit | Somme des residuals — computed stored |
| `sequence` | micro.credit.line | N° d'échéance |
| `date_due` | micro.credit.line | date_granted + N × intervalle |
| `is_overdue` | micro.credit.line | date_due < today AND residual > 0 |

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
| Grille collecte | Spinner Odoo | "Aucune case — activez le cycle" | Erreur réseau + retry | Case verte ✓ | Case orange + résiduel |
| Wizard versement | Bouton désactivé | N/A | Montant > dû → message inline | Case cochée, retour liste membres | Montant partiel accepté |
| Dashboard Manager | Skeleton cards | ✅ "Tout validé! Total: X CDF \| 12 agents \| 3 zones" | Toast erreur | Toast succès | X/Y validés |
| Validation masse | Barre progression X/Y | N/A | Item échoué isolé, reste continue | Toast "N transactions confirmées" | Partiel possible |
| GPS capture | "Localisation en cours..." | N/A | "GPS refusé — saisie manuelle" | Coords affichées readonly | N/A |
| Brouillon offline | Indicateur "Hors ligne" | N/A | N/A | Sync auto dès connexion | N/A |

---

## 5. Parcours Utilisateur

### Agent Terrain (journée type)
```
1. Ouvre l'app (PWA) → voit la liste de ses membres du jour
2. Tape un membre → grille de collecte s'ouvre (case courante en haut)
3. Tape la case courante → wizard plein écran (montant, [Valider])
4. Valide → case verte ✓, retour à la liste des membres
5. Fin de journée → récapitulatif (total collecté, N versements, N partiels)
6. Remet les fonds au Manager
```

### Manager (validation journalière)
```
1. Ouvre MICRO FLOW → Tableau de Bord (Kanban agents)
2. Cards triées par montant décroissant
3. Vérifie physiquement les fonds, coche is_verified
4. Clique "Tout Valider" → barre de progression X/Y
5. Toast "N transactions confirmées" → écritures comptables générées
6. Dashboard passe en état VIDE positif avec stats du jour
```

---

## 6. Décisions Techniques

### Cycles simultanés (décision 7B)
- N cycles actifs par membre autorisés
- Champ `max_active_cycles` dans `res.config.settings` (configurable Manager)
- Défaut: 1 (valeur conservatrice)

### Identifiant membre (décision 7A)
- **Deux champs séparés** sur `res.partner`:
  - `identifiant` → format recouvrement_vars (KIN_42) — géré par recouvrement_vars
  - `member_id` → format MF-ZONE-ANNEE-MOIS-SEQ — géré par microflow (déjà implémenté)

### Plateforme terrain (décision 6A)
- PWA (Progressive Web App)
- Brouillon local si hors ligne (service worker)
- Sync automatique à la reconnexion

### Post-paiement (décision 3A)
- Après validation wizard → retour à la liste des membres du jour

### Récapitulatif agent (décision 3B)
- Vue récapitulatif journalier avant remise de fonds
- Affiche: total collecté, N versements, N partiels

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

## 8. Bugs Critiques à Corriger

| Fichier | Ligne | Bug | Fix |
|---------|-------|-----|-----|
| `micro_credit.py` | 10 et 21 | `currency_id` défini 2× | Supprimer le doublon ligne 10 |
| `micro_transaction.py` | 12-16 et 18 | `currency_id` défini 2× | Supprimer le doublon lignes 12-16 |
| `micro_cycle_line.py` | 39 | Commentaire "Nouveau champ à ajouter" obsolète | Supprimer le commentaire (champ existe) |
| `micro_zone.py` | 1 | Fichier vide, modèle non défini | Définir le modèle (name, code, parent_id?) |
| `__manifest__.py` | 44 | `micro_transaction_views.xml` commenté | Décommenter quand la vue est prête |
| `__manifest__.py` | 56 | Asset path `micro_flow/` incorrect | Corriger en `microflow/` |

---

## 9. À Définir (questions ouvertes)

1. **`micro.zone`** : champs nécessaires ? (au minimum: `name`, `code`; optionnel: `parent_id`, `commission_rate`)
2. **Dashboard Kanban Manager** : groupé par `agent_id` (colonnes = agents) ou par `state` (colonnes = Brouillon/Confirmé) ?
3. **Nombre de `max_active_cycles`** par défaut dans la config ?

---

## 10. NOT in scope (design déféré)

- Thème tiers (MuK IT) — Odoo standard suffisant pour v0
- App native (Flutter/React Native) — PWA couvre le besoin terrain
- Reçu SMS/imprimable pour les agents — scope v1
- Hiérarchie de zones (zones imbriquées) — scope v1

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & stratégie | 0 | — | — |
| Codex Review | `/codex review` | 2ème opinion indépendante | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (requis) | 1 | issues_open | 14 issues, 4 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | issues_open | score 2/10 → 7/10, 8 décisions prises |
| DX Review | `/plan-devex-review` | Developer experience | 0 | — | — |

**UNRESOLVED:** 0 décisions — toutes les questions ont été répondues.
**VERDICT:** Design + Eng Review complètes. Corriger les P0 bugs avant implémentation des features.
