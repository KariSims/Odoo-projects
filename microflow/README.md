# Microflow — Module Microfinance Odoo 18

Gestion des cycles d'épargne et crédits avec collecte de terrain, workflow agent/manager et validation comptable groupée.

---

## Installation et lancement

### Prérequis

- Odoo 18.0 Community ou Enterprise
- Modules Odoo requis : `base`, `contacts`, `account`, `base_setup`
- Le dossier `microflow/` doit être dans le `addons_path` de ton `odoo.conf`

### Première installation

```bash
python odoo-bin -i microflow -d <nom_base> --dev=all
```

### Mise à jour après modification du code

```bash
python odoo-bin -u microflow -d <nom_base> --dev=all
```

### Vérification que le dossier est dans l'addons_path

Dans `odoo.conf` :
```ini
addons_path = /chemin/vers/Odoo-projects, /chemin/vers/odoo/addons
```

---

## Pourquoi le module n'apparaît plus dans le menu Odoo

L'icône de l'application disparaît du menu d'accueil Odoo si :

1. **Le module n'est pas installé** — vérifier dans Settings > Apps > chercher "Microflow" > statut "Installed"
2. **L'installation a échoué** — une erreur Python ou XML au chargement interrompt l'install. Relancer avec `--dev=all` pour voir les erreurs dans le terminal.
3. **L'utilisateur connecté n'a aucun menu visible** — si toutes les entrées de menu sont restreintes à des groupes auxquels l'utilisateur n'appartient pas, Odoo masque aussi l'icône racine.

### Résolution rapide

```bash
# Étape 1 : forcer la mise à jour
python odoo-bin -u microflow -d <nom_base> --dev=all

# Étape 2 : si erreur "module not found", réinstaller
python odoo-bin -i microflow -d <nom_base> --dev=all
```

Ensuite **assigner le groupe Manager** à ton utilisateur de test (voir section Groupes ci-dessous).

---

## Groupes et conditions de visibilité

Le module définit deux groupes dans **Settings > Users & Companies > Users > [utilisateur] > Access Rights > section "Micro Flow"** :

| Groupe | Rôle |
|--------|------|
| **Agent de Terrain** | Collecte sur le terrain, voit uniquement ses propres cycles et transactions |
| **Manager / Contrôleur** | Accès complet, validation comptable groupée, configuration |

> Le groupe Manager inclut automatiquement tous les droits du groupe Agent (`implied_ids`).

### Ce que voit chaque groupe

| Fonctionnalité | Agent | Manager | Sans groupe |
|----------------|-------|---------|-------------|
| Épargne (cycles) | ✓ ses cycles | ✓ tous | ✓ (vue vide) |
| Crédits | ✓ | ✓ | ✓ (vue vide) |
| Mon Récapitulatif | ✓ | — | ✗ |
| Tableau de Bord | ✗ | ✓ | ✗ |
| Toutes les Transactions | ✗ | ✓ | ✗ |
| Configuration > Zones | ✗ | ✓ | ✗ |
| Paramètres (Settings) | ✗ | ✓ | ✗ |
| Bouton "Tout Valider" | ✗ | ✓ | ✗ |
| Toggle "Versement Reçu" | ✗ | ✓ | ✗ |
| Activer le Cycle Complet | ✗ | ✓ | ✗ |

> **Important :** un utilisateur sans groupe verra les menus Épargne et Crédits mais ne pourra pas activer de cycle et ne verra aucune donnée.

---

## Configuration initiale obligatoire

Avant toute utilisation terrain, un **Manager** doit configurer dans **Settings > MICRO FLOW** :

| Paramètre | Description | Requis |
|-----------|-------------|--------|
| **Journal de collecte** | Journal comptable (caisse ou banque) utilisé pour toutes les transactions terrain | Oui |
| **Compte Dépôts Membres** | Compte passif courant crédité à chaque versement d'épargne | Oui |
| **Cycles actifs max par membre** | Nombre maximum de cycles d'épargne simultanés par membre (défaut : 1) | Non |
| **Cases preview (pré-activation)** | Nombre de cases créées à l'étape 1 Agent (défaut : 5) | Non |

Sans le journal ou le compte dépôts configurés, toute tentative d'activation de cycle ou de confirmation de transaction lèvera une erreur explicite.

---

## Fonctionnalités

### 1. Membres (res.partner étendu)

- Identifiant unique auto-généré au format `MF-ZONE-ANNEE-MOIS-ORDRE` (ex. `MF-KIN-2026-05-00001`)
- Champs : type de client, statut membre, zone géographique, date de naissance, coordonnées GPS
- Capture GPS via le bouton "Capturer la localisation GPS" (Chrome Android)

### 2. Zones de collecte

Référentiel hiérarchique des zones géographiques (jusqu'à 3 niveaux : Région / Quartier / Bloc).
- Champ `parent_id` : zone parente (optionnel)
- `complete_name` : chemin complet calculé automatiquement (ex. `Dakar / Médina / Bloc A`)
- Anti-récursion : Odoo bloque les hiérarchies circulaires
- Le `member_id` utilise le code de la **zone feuille** (zone de l'agent, pas la racine)
- Menu Configuration > Zones

### 3. Cycles d'épargne (micro.cycle) — activation en 2 étapes

Le cycle suit la machine à états : **Brouillon → Pré-collecte → Actif → Clôturé**

**Étape 1 — Agent : Pré-collecte**
- L'agent clique "Activer le Cycle" → N cases de preview sont créées (configurable, défaut 5)
- Le cycle passe en état `Pré-collecte`
- L'agent collecte les premiers versements et remet les fonds au Manager

**Étape 2 — Manager : Activation complète**
- Le Manager vérifie les fonds reçus puis clique "Activer le Cycle Complet"
- Les cases restantes sont créées (jusqu'à `case_count` total)
- Le cycle passe en état `Actif`

**Grille de collecte (MicroGrid) :**
- Interface mobile-first, cases tactiles colorées
- Double-tap pour cocher (1er tap = mise en évidence bleue, 2ème tap = collecte)
- Tap sur case cochée = demande d'annulation (dialog de confirmation)
- Rang chronologique affiché en exposant (1er versement = 1, etc.)
- Jusqu'à 500 cases affichées (limite configurable)

**Devise :** sélectionnable parmi les devises actives à la création, verrouillée après le premier versement.

**Annulation tardive (> 2 min) :** l'agent soumet une demande au Manager qui approuve ou rejette.

### 4. Crédits (micro.credit)

- Génération d'échéancier (capital × taux d'intérêt / N échéances)
- Paiements partiels via wizard plein-écran sur mobile (montant 48px, bouton 56px)
- Suivi du résiduel par ligne
- **Devise :** sélectionnable à la création, verrouillée à l'activation

### 5. Transactions (micro.transaction)

- Créées automatiquement à chaque collecte de case ou paiement de crédit
- Référence auto-séquentielle `MF-TX/2026/00001`
- Statuts : `Collecté (Terrain)` → `Confirmé (Caisse)`
- Agents : voient uniquement leurs propres transactions dans "Mon Récapitulatif"

**Sens comptable épargne :**
- Débit : compte caisse/journal
- Crédit : compte Dépôts Membres (passif courant, configurable)

### 6. Tableau de Bord Manager

Composant OWL dédié (`ManagerDashboard`) avec :
- **5 KPI cards** : épargne, remboursements, frais, crédits en attente, crédits actifs
- **Transactions terrain** : liste avec toggle "Versement Reçu", sélection individuelle ou masse
- **Validation groupée** : "Valider la sélection (N)" ou "Tout Valider"
- **Récapitulatif par agent** : cartes agrégées (total collecté, barre de progression X/Y reçus), section pliable
- **Empty state "Tout validé !"** : bannière verte quand 0 transaction en attente, avec indication des cycles encore ouverts

Le Kanban des cycles (`Épargne`) est groupé par urgence :
- Colonne "Corrections — À approuver" : cycles avec `case_count_requested ≠ 0`
- Colonne "Annulations — À approuver" : cycles avec `pending_uncheck_count > 0`
- Colonne "À traiter" : cycles `Pré-collecte` (activation Manager requise)
- Colonne "En cours" : cycles actifs sans action requise
- Colonne "Brouillon" / "Terminé" : états inactifs

### 7. Validation comptable groupée

`action_bulk_confirm` crée **1 `account.move` par agent et par devise** avec :
- 1 ligne débit/crédit par transaction
- 1 ligne de contrepartie caisse consolidée
- Auto-affectation du compte par défaut si le journal n'en a pas
- **Multi-devise** : si la devise de la transaction ≠ devise société, `amount_currency` + `currency_id` sont renseignés sur chaque ligne ; `debit`/`credit` contiennent les montants convertis au taux du jour via `res.currency._convert()`

### 8. PWA offline

- Service worker enregistré via `/microflow/sw.js` (scope `/`)
- Cache-first pour les assets statiques Microflow
- File d'attente IndexedDB pour les appels `register_collection` / `register_payment` hors ligne
- Background Sync automatique au retour du réseau

---

## Architecture technique

```
microflow/
├── models/
│   ├── micro_zone.py           Zone géographique (hiérarchique, parent_id + complete_name)
│   ├── micro_cycle.py          Cycle d'épargne (machine à états 4 niveaux)
│   ├── micro_cycle_line.py     Case de collecte + annulation 2-min + correction
│   ├── micro_credit.py         Crédit
│   ├── micro_credit_line.py    Ligne d'échéancier
│   ├── micro_transaction.py    Transaction de caisse + validation comptable multi-devise
│   ├── res_partner.py          Extension membre
│   ├── res_users.py            Sync home action (agent→Épargne, manager→Dashboard)
│   └── res_config_settings.py  Paramètres module
├── wizard/
│   ├── credit_payment_wizard.py       Assistant versement crédit
│   └── savings_repayment_wizard.py    Assistant transfert épargne → crédit
├── hooks.py                    post_init_hook (home actions agent/manager)
├── controllers/
│   └── controllers.py          Route /microflow/sw.js (service worker)
├── security/
│   ├── security_groups.xml     Groupes Agent / Manager
│   ├── record_rules.xml        Agent voit ses propres données
│   └── ir.model.access.csv     Droits CRUD par groupe
├── views/                      Vues XML (list, form, kanban)
├── static/src/
│   ├── components/
│   │   ├── MicroGrid/          Widget OWL grille de cases
│   │   └── ManagerDashboard/   Dashboard OWL client action
│   ├── js/
│   │   ├── gps_capture.js      Capture GPS (patch FormController)
│   │   ├── sw_register.js      Enregistrement service worker
│   │   └── service_worker.js   Logique offline + IndexedDB
│   └── css/
│       └── microflow_mobile.scss  Styles mobile-first
└── tests/
    ├── test_res_partner.py     3 tests — ID membre, unicité, code zone
    ├── test_micro_cycle.py     37 tests — cycles, collecte, comptabilité, correction de cases
    ├── test_micro_credit.py    8 tests — workflow crédit, wizard paiement
    ├── test_savings_transfer.py 13 tests — transfert épargne→crédit, wizard, écritures
    ├── test_micro_zone.py      10 tests — hiérarchie, complete_name, anti-récursion
    └── test_res_users.py       5 tests — sync home action, groupes, batch
```

### Lancer les tests (76 tests)

```bash
python odoo-bin -d <nom_base> --test-enable --stop-after-init -i microflow
```

---

## Dépannage fréquent

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| Module invisible dans le menu | Installation cassée ou utilisateur sans groupe | `-u microflow` + assigner groupe Manager |
| "Configurez le journal" à l'activation | Journal non configuré | Settings > MICRO FLOW > Journal de collecte |
| "Configurez le compte dépôts" à la confirmation | Compte épargne non configuré | Settings > MICRO FLOW > Compte Dépôts Membres |
| Paramètres invisibles dans Settings | Utilisateur pas dans le groupe Manager | Settings > Users > assigner Manager |
| Grille bloquée à 40 cases | Ancien sous-formulaire sans limit | Ajouter `limit="500"` au `<list>` subview MicroGrid |
| "post_init_hook" manquant à l'install | `__init__.py` manque `from .hooks import post_init_hook` | Ajouter cette ligne dans `__init__.py` |
| Service Worker insecure | (corrigé) — SW servi via contrôleur avec header `Service-Worker-Allowed: /` | N/A |
| Cases toutes nommées "Nouveau" | (corrigé) — séquence MF-TX ajoutée | N/A |

---

*Version 1.4 — Auteur : KariSims*
