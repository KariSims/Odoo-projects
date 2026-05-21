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

> **Important :** un utilisateur sans groupe verra les menus Épargne et Crédits mais ne pourra pas activer de cycle (le journal n'est pas configuré) et ne verra aucune donnée filtrée par agent.

---

## Configuration initiale obligatoire

Avant toute utilisation terrain, un **Manager** doit configurer dans **Settings > MICRO FLOW** :

| Paramètre | Description | Requis |
|-----------|-------------|--------|
| **Journal de collecte** | Journal comptable (caisse ou banque) utilisé pour toutes les transactions terrain | Oui |
| **Cycles actifs max par membre** | Nombre maximum de cycles d'épargne simultanés par membre (défaut : 1) | Non |

Sans le journal configuré, toute tentative d'activation de cycle ou de collecte lèvera une erreur explicite.

---

## Fonctionnalités

### 1. Membres (res.partner étendu)

- Identifiant unique auto-généré au format `MF-ZONE-ANNEE-MOIS-ORDRE` (ex. `MF-KIN-2026-05-00001`)
- Champs : type de client, statut membre, zone géographique, date de naissance, coordonnées GPS
- Capture GPS via le bouton "Capturer la localisation GPS" (Chrome Android)

### 2. Zones de collecte

Référentiel des zones géographiques avec code et taux de commission. Menu Configuration > Zones.

### 3. Cycles d'épargne (micro.cycle)

- Grille de cases (N cases × montant par case)
- Activation du cycle : génère les cases + transaction de frais d'adhésion si configurée
- Collecte terrain via le widget **MicroGrid** (interface mobile-first, cases colorées)
- Case courante mise en évidence avec bannière sticky et tap pour collecter
- Règle : un agent ne voit que ses propres cycles

### 4. Crédits (micro.credit)

- Génération d'échéancier (capital × taux d'intérêt / N échéances)
- Paiements partiels via wizard plein-écran sur mobile (montant 48px, bouton 56px)
- Limite de versements partiels par échéance configurable
- Suivi du résiduel par ligne

### 5. Transactions (micro.transaction)

- Créées automatiquement à chaque collecte de case ou paiement de crédit
- Référence auto-séquentielle `MF-TX/2026/00001`
- Statuts : `Collecté (Terrain)` → `Confirmé (Caisse)`
- Agents : voient uniquement leurs propres transactions du jour dans "Mon Récapitulatif"

### 6. Tableau de Bord Manager

Kanban des transactions en attente (`state=draft`) groupées par agent. Le manager coche "Versement Reçu" puis clique **"Tout Valider"** pour générer 1 écriture comptable groupée par agent.

### 7. Validation comptable groupée

`action_bulk_confirm` crée **1 `account.move` par agent** (au lieu de N écritures séparées) avec :
- 1 ligne débit/crédit par transaction
- 1 ligne de contrepartie caisse consolidée
- Auto-affectation du compte par défaut si le journal n'en a pas

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
│   ├── micro_zone.py           Zone géographique
│   ├── micro_cycle.py          Cycle d'épargne
│   ├── micro_cycle_line.py     Case de collecte
│   ├── micro_credit.py         Crédit
│   ├── micro_credit_line.py    Ligne d'échéancier
│   ├── micro_transaction.py    Transaction de caisse
│   ├── res_partner.py          Extension membre
│   └── res_config_settings.py  Paramètres module
├── wizard/
│   └── credit_payment_wizard.py  Assistant versement
├── controllers/
│   └── controllers.py          Route /microflow/sw.js (service worker)
├── security/
│   ├── security_groups.xml     Groupes Agent / Manager
│   ├── record_rules.xml        Agent voit ses propres données
│   └── ir.model.access.csv     Droits CRUD par groupe
├── views/                      Vues XML (list, form, kanban)
├── static/src/
│   ├── components/MicroGrid/   Widget OWL grille de cases
│   ├── js/
│   │   ├── gps_capture.js      Capture GPS (patch FormController)
│   │   ├── sw_register.js      Enregistrement service worker
│   │   └── service_worker.js   Logique offline + IndexedDB
│   └── css/
│       └── microflow_mobile.scss  Styles mobile-first
└── tests/
    ├── test_res_partner.py     3 tests ID membre
    ├── test_micro_cycle.py     6 tests cycles
    └── test_micro_credit.py    7 tests crédits
```

### Lancer les tests

```bash
python odoo-bin -d <nom_base> --test-enable --stop-after-init -i microflow
```

---

## Dépannage fréquent

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| Module invisible dans le menu | Installation cassée ou utilisateur sans groupe | `-u microflow` + assigner groupe Manager |
| "Configurez le journal" à l'activation | Journal non configuré | Settings > MICRO FLOW > Journal de collecte |
| Paramètres invisibles dans Settings | Utilisateur pas dans le groupe Manager | Settings > Users > assigner Manager |
| Service Worker insecure | (corrigé) — SW servi via contrôleur avec header `Service-Worker-Allowed: /` | N/A |
| "tracking=True sans mail.thread" | (corrigé) — supprimé | N/A |
| Cases toutes nommées "Nouveau" | (corrigé) — séquence MF-TX ajoutée | N/A |

---

*Version 0.3 — Auteur : KariSims*
