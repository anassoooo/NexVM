# NexVM — Description complète du projet

> **NexVM** (Next-generation Virtual Machine Manager) est une plateforme web fullstack de gestion centralisée de machines virtuelles Oracle VirtualBox, dotée d'un assistant IA conversationnel en langage naturel, d'un panneau d'administration, d'un système d'analytique avancé et d'un planificateur de tâches automatisé.

---

## Table des matières

1. [Présentation générale](#1-présentation-générale)
2. [Architecture du système](#2-architecture-du-système)
3. [Fonctionnalités détaillées](#3-fonctionnalités-détaillées)
4. [Base de données et modèle de données](#4-base-de-données-et-modèle-de-données)
5. [API REST — Référence complète](#5-api-rest--référence-complète)
6. [Assistant IA](#6-assistant-ia)
7. [Interface utilisateur](#7-interface-utilisateur)
8. [Sécurité](#8-sécurité)
9. [Technologies et outils](#9-technologies-et-outils)
10. [Tests](#10-tests)
11. [Déploiement](#11-déploiement)
12. [Structure des fichiers](#12-structure-des-fichiers)

---

## 1. Présentation générale

### 1.1 Contexte

Dans les environnements professionnels, la gestion de machines virtuelles repose généralement sur des outils en ligne de commande complexes (VBoxManage) ou des interfaces graphiques locales, ce qui pose plusieurs problèmes :

- **Barrière technique** : les commandes VBoxManage nécessitent une expertise avancée.
- **Absence d'accès distant** : les utilisateurs doivent avoir un accès physique ou SSH à la machine hôte.
- **Aucune traçabilité** : les opérations ne sont pas journalisées automatiquement.
- **Pas de multi-utilisateurs** : impossible d'isoler les données entre utilisateurs.
- **Pas de visibilité globale** : aucun tableau de bord pour superviser le parc de VMs.

### 1.2 Solution

**NexVM** résout ces problèmes en proposant une plateforme web centralisée offrant :

- Une **interface web moderne** accessible depuis n'importe quel navigateur.
- Un **assistant IA conversationnel** capable de comprendre des instructions en langage naturel (français, anglais, arabe, etc.) et de les traduire en actions sur les VMs.
- Un **panneau d'administration** permettant aux administrateurs de superviser et gérer l'ensemble du parc.
- Un **système d'analytique** avec des tableaux de bord et des graphiques temporels.
- Un **planificateur de tâches** basé sur des expressions cron pour automatiser le démarrage et l'arrêt des VMs.
- Un **journal d'audit** immuable enregistrant toutes les actions du système.

### 1.3 Acteurs du système

| Acteur | Description | Accès |
|---|---|---|
| **Utilisateur régulier** | Membre de la DSI (développeur, testeur, analyste) ayant besoin de VMs pour ses travaux | Gère ses propres VMs via le chat IA ou l'interface graphique |
| **Administrateur** | Responsable technique chargé de superviser le parc de virtualisation | Accès au panneau d'administration, gestion de toutes les VMs, métriques globales |

---

## 2. Architecture du système

### 2.1 Architecture en trois tiers

NexVM adopte une architecture **client-serveur en trois tiers** :

```
┌─────────────────────────────────────────────────┐
│              COUCHE PRÉSENTATION                 │
│         Frontend Web — Next.js 14               │
│    Login · Signup · Chat IA · VMs · Admin        │
│              Analytics · Logs · Profile          │
└──────────────────────┬──────────────────────────┘
                       │ HTTP/HTTPS — JSON (REST)
                       ▼
┌─────────────────────────────────────────────────┐
│              COUCHE MÉTIER                       │
│         Backend API — FastAPI / Python 3.12      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │Auth      │ │VM Service│ │AI Service        │ │
│  │Middleware│ │          │ │(Groq / Llama 4)  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │Analytics │ │Schedules │ │Logger            │ │
│  │Service   │ │Service   │ │                  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└──────┬──────────────┬───────────────┬───────────┘
       │              │               │
       ▼              ▼               ▼
┌───────────┐  ┌───────────┐  ┌───────────────┐
│  Supabase │  │ VirtualBox│  │  Groq API     │
│ PostgreSQL│  │ VBoxManage│  │ (Llama 4      │
│ + Auth    │  │ (local)   │  │  Scout)       │
│ + RLS     │  │           │  │               │
└───────────┘  └───────────┘  └───────────────┘
```

### 2.2 Flux de communication

1. L'utilisateur interagit avec le **frontend** via son navigateur.
2. Le frontend envoie des requêtes **HTTP/JSON** au backend FastAPI.
3. Le backend **valide le JWT** de l'utilisateur via le middleware d'authentification.
4. Le backend exécute la logique métier via les **services** appropriés.
5. Les services communiquent avec **VirtualBox** (appels subprocess locaux), **Supabase** (base de données) ou **Groq** (IA) selon les besoins.
6. La réponse est renvoyée au frontend en format JSON.

### 2.3 Cycle de vie d'une requête AI typique

```
Utilisateur → Frontend → POST /api/v1/ai/command
  → AI Service → Groq API (LLM)
  → Validation Pydantic
  → VM Service → VBoxManage (subprocess)
  → Base de données (insert log + ai_usage)
  → Réponse JSON → Frontend → Affichage
```

---

## 3. Fonctionnalités détaillées

### 3.1 Authentification et gestion des comptes

**Inscription :**

- Formulaire avec adresse email et mot de passe.
- Politique de mot de passe : minimum 8 caractères, au moins un chiffre.
- Création du compte via Supabase Auth.
- Création automatique du profil utilisateur dans la table `profiles` via un trigger PostgreSQL.

**Connexion :**

- Authentification par email/mot de passe via Supabase Auth.
- Génération d'un jeton JWT valide pendant 24 heures.
- Stockage du JWT dans un cookie HTTP sécurisé.
- Redirection automatique : utilisateur → `/vms`, administrateur → `/admin`.

**Sessions :**

- Persistance de la session via cookie (survit aux rechargements de page).
- Vérification du JWT à chaque requête API via le middleware.
- Profil auto-créé si manquant lors de la première connexion.

**Rôles :**

- **Utilisateur régulier** (`is_admin = false`) : gère ses propres VMs.
- **Administrateur** (`is_admin = true`) : accès au panneau d'administration, gestion de toutes les VMs.

### 3.2 Gestion des machines virtuelles — Cycle de vie de base

**Machine à états :**

```
        ┌─────────── Création ──────────┐
        ▼                               │
    [stopped] ──── start ──→ [starting] ──→ [running]
        ▲                               │     │
        │                           (erreur)  stop
        │                               │     │
        │                               ▼     ▼
        │                          [error]  [stopping]
        │                               │     │
        └─────── reset ◄────────────────┘     │
        ▲                                      │
        └──────────────────────────────────────┘
        │
    delete → (supprimé)
```

**États possibles :** `stopped`, `starting`, `running`, `stopping`, `paused`, `error`

**Opérations de base :**

| Opération | Description | Précondition |
|---|---|---|
| Créer une VM | Crée une VM avec nom, OS, RAM, CPU, disque | Nom unique pour l'utilisateur, quota non dépassé |
| Démarrer une VM | Démarre une VM arrêtée | VM à l'état `stopped` |
| Arrêter une VM | Arrête une VM en cours d'exécution | VM à l'état `running` |
| Supprimer une VM | Supprime une VM et ses fichiers | VM à l'état `stopped` |
| Synchroniser | Met à jour le statut depuis VirtualBox | Toute VM |
| Forcer la réinitialisation | Arrêt forcé + retour à `stopped` | Réservé aux administrateurs |

**Paramètres de création :**

| Paramètre | Contraintes | Valeur par défaut |
|---|---|---|
| Nom | 1 à 50 caractères, unique par utilisateur | — |
| Système d'exploitation | Choix parmi une liste prédéfinie (Ubuntu, Debian, CentOS, Fedora, Windows, etc.) | — |
| RAM | 512 Mo à 16 384 Mo | Variable selon l'OS |
| CPU | 1 à 8 cœurs | 2 |
| Disque | 1 Go à 200 Go | 20 Go |

**Quotas par utilisateur :**

- Nombre maximum de VMs : **5** (configurable via `VM_QUOTA_PER_USER`).
- Espace disque total maximum : **200 Go** (configurable via `VM_QUOTA_DISK_MB`).

**Systèmes d'exploitation supportés :**

Ubuntu (64-bit), Debian (64-bit), CentOS (64-bit), Fedora (64-bit), Arch Linux (64-bit), Kali Linux (64-bit), Linux Mint (64-bit), openSUSE (64-bit), Red Hat (64-bit), Windows 10 (64-bit), Windows 11 (64-bit), Windows Server 2019 (64-bit), Windows Server 2022 (64-bit), macOS Sonoma, macOS Ventura.

### 3.3 Fonctionnalités avancées — P1 : Média et accès distant

#### 3.3.1 Attachement/Détachement d'ISO

- Attacher un fichier ISO à une VM pour l'installation d'un système d'exploitation.
- Détacher l'ISO monté.
- Le chemin de l'ISO est stocké dans la base de données.

#### 3.3.2 VRDE (Virtual Remote Desktop Extension) / RDP

- Activer le bureau à distance sur une VM avec un port RDP configurable.
- Désactiver le VRDE.
- Indication visuelle dans l'interface quand le VRDE est actif.

### 3.4 Fonctionnalités avancées — P2 : Cycle de vie étendu

#### 3.4.1 Modification matérielle

- Modifier la RAM allouée à une VM.
- Modifier le nombre de CPU alloués.
- Uniquement possible quand la VM est à l'état `stopped`.

#### 3.4.2 Pause / Reprise / Sauvegarde d'état

| Action | Description | Transition |
|---|---|---|
| Pause | Suspend l'exécution de la VM | `running` → `paused` |
| Reprise | Reprend l'exécution d'une VM en pause | `paused` → `running` |
| Sauvegarder l'état | Sauvegarde l'état complet de la VM en mémoire | `running` → `stopped` (avec état sauvegardé) |

#### 3.4.3 Règles de transfert de ports (NAT)

- Ajouter une règle de transfert de port (protocole TCP/UDP, port hôte → port invité, IP).
- Supprimer une règle existante.
- Les règles sont stockées en JSON dans la colonne `nat_rules` de la VM.

#### 3.4.4 Snapshots (instantanés)

- **Prendre un instantané** : capture l'état complet d'une VM à un instant donné (nom et description optionnels).
- **Restaurer un instantané** : restaure la VM à l'état d'un instantané précédent.
- **Supprimer un instantané** : supprime un instantané spécifique.
- **Lister les instantanés** : affiche tous les instantanés d'une VM.

### 3.5 Fonctionnalités avancées — P3 : Clonage et export

#### 3.5.1 Clonage de VM

- Cloner une VM existante vers une nouvelle VM.
- Le clonage copie la configuration et le disque virtuel.
- La VM source doit être à l'état `stopped`.
- Le clone hérite des paramètres matériels de la source.
- Le quota est vérifié avant le clonage.

#### 3.5.2 Export au format OVA

- Exporter une VM sous forme d'archive OVA (Open Virtualization Format).
- La VM doit être à l'état `stopped`.
- Le fichier est sauvegardé dans le répertoire de stockage des VMs.

#### 3.5.3 Import au format OVA/OVF

- Importer une VM depuis un fichier OVA ou OVF.
- L'utilisateur spécifie le chemin du fichier.
- Le quota est vérifié avant l'import.
- Vérification de l'unicité du nom.

### 3.6 Métriques des VMs

- Récupération en temps réel des **métriques de performance** via VBoxManage :
  - **Charge CPU** (%) de la VM.
  - **Utilisation RAM** (Mo consommés) de la VM.
- Ces métriques ne sont disponibles que pour les VMs à l'état `running`.

### 3.7 Planification de tâches (Scheduling)

NexVM intègre un **planificateur de tâches** permettant d'automatiser le démarrage et l'arrêt des VMs selon des planifications cron.

**Fonctionnalités :**

- Créer une planification (schedule) pour une VM avec :
  - L'action à exécuter (`start` ou `stop`).
  - Une expression cron définissant la récurrence (ex. : `0 8 * * 1-5` = tous les jours ouvrés à 8h).
  - Un indicateur d'activation/désactivation.
- Activer/désactiver une planification existante.
- Supprimer une planification.
- Lister les planifications d'une VM ou de l'utilisateur.
- Les planifications sont persistées en base de données et rechargées automatiquement au redémarrage du serveur via **APScheduler**.

**Exemples d'usage :**

- Démarrer une VM de test tous les matins à 8h.
- Arrêter une VM tous les soirs à 18h pour économiser les ressources.
- Démarrer un environnement de formation uniquement les jours ouvrés.

### 3.8 Système d'analytique

NexVM propose des tableaux de bord analytiques complets, différents selon le rôle de l'utilisateur.

#### 3.8.1 Analytique utilisateur

L'utilisateur régulier accède à :

- **Statistiques agrégées** :
  - Nombre total de VMs.
  - VMs actives (running).
  - VMs arrêtées (stopped).
  - VMs en erreur.
  - Nombre total de commandes IA exécutées.
  - Espace disque total utilisé.
- **Données temporelles** (graphiques) :
  - Nombre cumulé de VMs au fil du temps (graphique en aire).
  - VMs créées par jour (graphique en barres).
  - Commandes IA par jour (graphique en barres).

#### 3.8.2 Analytique administrateur

L'administrateur accède à :

- **Statistiques globales du système** :
  - Nombre total d'utilisateurs inscrits.
  - Nombre total de VMs (tous utilisateurs confondus).
  - Répartition par statut (running, stopped, error, etc.).
  - Nombre total de commandes IA.
  - Espace disque total utilisé par le système.
- **Données temporelles globales** :
  - Tendances de création de VMs.
  - Évolution de l'utilisation de l'IA.

### 3.9 Journal d'audit (Logs)

Toutes les actions effectuées sur le système sont enregistrées de manière immuable dans la table `logs`.

**Informations enregistrées :**

| Champ | Description |
|---|---|
| `user_id` | Identifiant de l'utilisateur ayant effectué l'action |
| `action` | Type d'action (22 types possibles) |
| `target` | Cible de l'action (ID de la VM, etc.) |
| `status` | Succès ou échec |
| `message` | Détails supplémentaires |
| `created_at` | Horodatage précis |

**22 types d'actions journalisées :**

`create_vm`, `start_vm`, `stop_vm`, `delete_vm`, `attach_iso`, `detach_iso`, `enable_vrde`, `disable_vrde`, `modify_vm`, `pause_vm`, `resume_vm`, `save_state`, `add_port_rule`, `remove_port_rule`, `take_snapshot`, `restore_snapshot`, `delete_snapshot`, `clone_vm`, `export_vm`, `import_vm`, `force_reset`, `schedule_vm`

**L'interface des logs** présente deux onglets :

- **Activité** : journal des actions sur les VMs.
- **Utilisation IA** : historique des commandes envoyées à l'assistant IA, incluant le prompt, la réponse et les tokens consommés.

### 3.10 Profil utilisateur

La page de profil affiche :

- Informations du compte (email, rôle, date de création).
- Statistiques personnelles (nombre de VMs, commandes IA).
- Barre de progression du quota disque utilisé.

---

## 4. Base de données et modèle de données

### 4.1 Tables principales

#### Table `profiles`

| Colonne | Type | Description |
|---|---|---|
| `id` | UUID (PK, FK → auth.users) | Identifiant du compte Supabase Auth |
| `email` | TEXT | Adresse email de l'utilisateur |
| `is_admin` | BOOLEAN (défaut: false) | Indique si l'utilisateur est administrateur |
| `created_at` | TIMESTAMPTZ | Date de création du profil |

**Trigger :** Un trigger PostgreSQL (`handle_new_user`) crée automatiquement un profil lors de l'inscription via Supabase Auth.

#### Table `vms`

| Colonne | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Identifiant unique de la VM |
| `user_id` | UUID (FK → profiles.id) | Propriétaire de la VM |
| `name` | TEXT | Nom de la VM (1 à 50 caractères) |
| `os` | TEXT | Système d'exploitation |
| `ram` | INTEGER | Mémoire vive en Mo |
| `cpu` | INTEGER (défaut: 2) | Nombre de cœurs CPU |
| `disk_size` | INTEGER (défaut: 20480) | Taille du disque en Mo |
| `status` | TEXT (CHECK) | Statut : stopped, starting, running, stopping, paused, error |
| `vbox_id` | TEXT | Identifiant interne VirtualBox |
| `iso_path` | TEXT | Chemin de l'ISO attaché |
| `vrde_enabled` | BOOLEAN | VRDE/RDP activé |
| `vrde_port` | INTEGER | Port RDP |
| `nat_rules` | JSONB | Règles de transfert de ports |
| `error_message` | TEXT | Message d'erreur éventuel |
| `created_at` | TIMESTAMPTZ | Date de création |
| `updated_at` | TIMESTAMPTZ | Date de dernière mise à jour |

#### Table `logs`

| Colonne | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Identifiant unique |
| `user_id` | UUID (FK → profiles.id) | Utilisateur ayant effectué l'action |
| `action` | TEXT (CHECK enum) | Type d'action (22 valeurs possibles) |
| `target` | TEXT | Cible de l'action |
| `status` | TEXT (CHECK) | Succès ou échec |
| `message` | TEXT | Détails de l'action |
| `created_at` | TIMESTAMPTZ | Horodatage |

#### Table `ai_usage`

| Colonne | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Identifiant unique |
| `user_id` | UUID (FK → profiles.id) | Utilisateur |
| `prompt` | TEXT | Commande saisie par l'utilisateur |
| `response` | TEXT | Réponse générée par l'IA |
| `tokens` | INTEGER | Nombre de tokens consommés |
| `created_at` | TIMESTAMPTZ | Horodatage |

#### Table `vm_schedules`

| Colonne | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Identifiant unique |
| `user_id` | UUID (FK → profiles.id) | Propriétaire de la planification |
| `vm_id` | UUID (FK → vms.id) | VM concernée |
| `action` | TEXT (CHECK) | Action : start ou stop |
| `cron_expr` | TEXT | Expression cron (ex. : `0 8 * * 1-5`) |
| `enabled` | BOOLEAN (défaut: true) | Activation/désactivation |
| `last_run` | TIMESTAMPTZ | Dernière exécution |
| `created_at` | TIMESTAMPTZ | Date de création |

#### Table `vm_snapshots`

| Colonne | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Identifiant unique |
| `vm_id` | UUID (FK → vms.id) | VM parente |
| `name` | TEXT | Nom de l'instantané |
| `description` | TEXT | Description optionnelle |
| `created_at` | TIMESTAMPTZ | Date de création |

### 4.2 Relations entre les tables

```
profiles (1) ──── (* ) vms
profiles (1) ──── (* ) logs
profiles (1) ──── (* ) ai_usage
profiles (1) ──── (* ) vm_schedules
vms      (1) ──── (* ) vm_schedules
vms      (1) ──── (* ) vm_snapshots
```

### 4.3 Sécurité au niveau des lignes (Row Level Security)

Chaque table est protégée par des politiques RLS PostgreSQL :

- **Utilisateur régulier** : ne peut lire et modifier que les lignes où `user_id` correspond à son identifiant.
- **Administrateur** : peut lire toutes les lignes de toutes les tables.
- **Insertion automatique** : les logs et l'utilisation IA sont insérés côté serveur (backend), jamais depuis le frontend.

### 4.4 Fonction utilitaire

La fonction `is_admin()` (SECURITY DEFINER) permet aux politiques RLS de vérifier le rôle de l'utilisateur courant sans exposer la table `profiles`.

---

## 5. API REST — Référence complète

### 5.1 Préfixe de base

Tous les endpoints sont accessibles sous le préfixe `/api/v1/`.

### 5.2 Authentification

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | Non | Connexion (email + mot de passe) → JWT + user info |
| `POST` | `/auth/signup` | Non | Inscription → JWT ou message de confirmation |
| `GET` | `/auth/me` | Oui | Informations de l'utilisateur courant |

### 5.3 Machines virtuelles (utilisateur)

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/vm/` | Oui | Liste des VMs de l'utilisateur |
| `POST` | `/vm/create` | Oui | Créer une VM |
| `POST` | `/vm/start` | Oui | Démarrer une VM |
| `POST` | `/vm/stop` | Oui | Arrêter une VM |
| `POST` | `/vm/delete` | Oui | Supprimer une VM |
| `POST` | `/vm/status` | Oui | Obtenir le statut d'une VM |
| `POST` | `/vm/sync` | Oui | Synchroniser le statut depuis VirtualBox |

### 5.4 Fonctionnalités P1 — Média et accès distant

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/vm/iso` | Oui | Attacher un ISO |
| `DELETE` | `/vm/iso` | Oui | Détacher l'ISO |
| `POST` | `/vm/vrde` | Oui | Activer le VRDE/RDP |
| `DELETE` | `/vm/vrde` | Oui | Désactiver le VRDE/RDP |

### 5.5 Fonctionnalités P2 — Cycle de vie étendu

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/vm/modify` | Oui | Modifier la RAM/CPU |
| `POST` | `/vm/pause` | Oui | Mettre en pause |
| `POST` | `/vm/resume` | Oui | Reprendre |
| `POST` | `/vm/savestate` | Oui | Sauvegarder l'état |
| `POST` | `/vm/portfwd` | Oui | Ajouter une règle de port |
| `DELETE` | `/vm/portfwd` | Oui | Supprimer une règle de port |
| `GET` | `/vm/snapshots` | Oui | Lister les instantanés |
| `POST` | `/vm/snapshot` | Oui | Prendre un instantané |
| `POST` | `/vm/snapshot/restore` | Oui | Restaurer un instantané |
| `DELETE` | `/vm/snapshot` | Oui | Supprimer un instantané |

### 5.6 Fonctionnalités P3 — Clonage et export

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/vm/clone` | Oui | Cloner une VM |
| `POST` | `/vm/export` | Oui | Exporter en OVA |
| `POST` | `/vm/import` | Oui | Importer un OVA/OVF |

### 5.7 Métriques

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/vm/metrics` | Oui | Métriques CPU/RAM d'une VM |

### 5.8 Administration

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/vm/` | Admin | Liste de toutes les VMs |
| `POST` | `/admin/vm/start` | Admin | Démarrer n'importe quelle VM |
| `POST` | `/admin/vm/stop` | Admin | Arrêter n'importe quelle VM |
| `POST` | `/admin/vm/delete` | Admin | Supprimer n'importe quelle VM |
| `POST` | `/admin/vm/force-reset` | Admin | Réinitialisation forcée |

### 5.9 Assistant IA

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/ai/command` | Oui | Envoyer une commande en langage naturel |

### 5.10 Analytique

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/analytics/` | Oui | Statistiques de l'utilisateur |
| `GET` | `/analytics/admin` | Admin | Statistiques globales |
| `GET` | `/analytics/timeseries` | Oui | Données temporelles utilisateur |
| `GET` | `/analytics/timeseries/admin` | Admin | Données temporelles globales |

### 5.11 Logs

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/logs/` | Oui | Journal d'activité (100 dernières entrées) |
| `GET` | `/logs/ai-usage` | Oui | Journal d'utilisation IA (100 dernières entrées) |

### 5.12 Planification

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/schedules/` | Oui | Planifications de l'utilisateur |
| `GET` | `/schedules/{vm_id}` | Oui | Planifications d'une VM |
| `POST` | `/schedules/` | Oui | Créer une planification |
| `DELETE` | `/schedules/{id}` | Oui | Supprimer une planification |
| `POST` | `/schedules/{id}/toggle` | Oui | Activer/désactiver |

### 5.13 Santé du système

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | Non | Vérification de l'état + version VBoxManage |

---

## 6. Assistant IA

### 6.1 Fonctionnement

L'assistant IA constitue l'interface principale d'interaction entre l'utilisateur et ses machines virtuelles. Il permet de contrôler les VMs en utilisant du langage naturel, sans jamais avoir besoin de connaître la syntaxe technique de VBoxManage.

**Pipeline de traitement :**

1. L'utilisateur saisit un message en langage naturel (ex. : « crée une VM Ubuntu avec 4 Go de RAM nommée serveur-web »).
2. Le message est envoyé au backend avec le contexte des VMs de l'utilisateur.
3. Le service IA construit un prompt système contenant :
   - La liste des VMs de l'utilisateur avec leur statut.
   - Les 12 actions possibles avec leurs schémas JSON.
   - Les règles de validation (plages de valeurs, préconditions).
   - Les synonymes courants (ex. : « allume » = « démarre »).
4. Le prompt est envoyé au modèle **Llama 4 Scout** via l'API **Groq** avec température 0 (réponses déterministes).
5. La réponse JSON du modèle est validée par un **schéma Pydantic strict**.
6. Si l'action est valide, elle est exécutée par le service VM approprié.
7. Le résultat est renvoyé à l'utilisateur dans sa langue.

### 6.2 Actions supportées par l'IA

| Action | Description | Exemple de commande |
|---|---|---|
| `create_vm` | Créer une nouvelle VM | « crée une VM Ubuntu avec 2 Go de RAM nommée test » |
| `start_vm` | Démarrer une VM | « démarre la VM test » |
| `stop_vm` | Arrêter une VM | « arrête la VM serveur-web » |
| `delete_vm` | Supprimer une VM | « supprime test » |
| `list_vms` | Lister les VMs | « montre-moi mes machines virtuelles » |
| `modify_vm` | Modifier la RAM/CPU | « change la RAM de test à 4 Go » |
| `attach_iso` | Attacher un ISO | « monte l'ISO ubuntu-22.04 sur test » |
| `detach_iso` | Détacher l'ISO | « enlève l'ISO de test » |
| `pause_vm` | Mettre en pause | « mets test en pause » |
| `resume_vm` | Reprendre | « reprends test » |
| `query_analytics` | Consulter les statistiques | « combien de VMs j'ai ? » |
| `chat` | Conversation générale | « c'est quoi Docker ? » |

### 6.3 Sécurité et validation

- **Whitelist d'actions** : seules les 12 actions définies sont autorisées. Toute autre action est rejetée.
- **Validation Pydantic** : chaque réponse IA est validée contre un schéma strict avant exécution.
- **Limitation de débit** : maximum **10 commandes IA par minute** par utilisateur (en mémoire).
- **Pas d'injection** : les commandes VBoxManage sont construites par liste d'arguments (pas de shell=True).
- **Journalisation** : chaque échange est enregistré dans `ai_usage`.

### 6.4 Multilinguisme

L'assistant IA comprend et répond dans la langue de l'utilisateur. Il supporte notamment :

- Français
- Anglais
- Arabe
- Toute autre langue supportée par le modèle Llama 4 Scout

### 6.5 Message d'accueil

À chaque ouverture de la session de chat, l'IA génère automatiquement un message de bienvenue résumant l'état des VMs de l'utilisateur :

- Nombre total de VMs.
- Nombre de VMs actives.
- Nombre de VMs arrêtées.
- Nombre de VMs en erreur.

---

## 7. Interface utilisateur

### 7.1 Design et thème

L'interface utilise un thème **cyberpunk** moderne avec :

- Fond sombre (`#0a0f0d`).
- Couleur d'accent verte néon (`#00e676`).
- Effets de transparence (glass-morphism).
- Effets de lueur (glow) sur les boutons et les cartes.
- Typographie Geist (variable font).
- Design responsive adaptatif.

### 7.2 Pages de l'application

#### Page d'accueil (Landing)

- Page marketing présentant NexVM avec :
  - Section héro avec titre et appel à l'action.
  - Grille des fonctionnalités principales.
  - Section « Comment ça marche » en 3 étapes.
  - Badges technologiques.
  - Liste des capacités.
  - Boutons d'inscription/connexion.

#### Pages d'authentification

- `/login` : formulaire de connexion (email + mot de passe).
- `/signup` : formulaire d'inscription avec validation côté client.

#### Portail utilisateur (sidebar de navigation)

- `/vms` : **Gestion des VMs** — page principale affichant :
  - Grille de cartes VM avec actions contextuelles.
  - Formulaire de création de VM (OS, RAM, CPU, disque).
  - Formulaire d'import OVA.
  - Barre de quota disque.
  - Rafraîchissement automatique : 5 secondes pour les VMs en transition, 30 secondes pour les VMs stables.

- `/ai` : **Chat IA** — interface conversationnelle avec :
  - Zone de messages (bulles utilisateur/IA).
  - Champ de saisie avec compteur de caractères.
  - Message d'accueil automatique avec résumé des VMs.
  - Historique de la session courante.

- `/analytics` : **Analytique** — tableaux de bord avec :
  - Cartes de statistiques (VMs, commandes IA, disque).
  - Graphique en aire (évolution du nombre de VMs).
  - Graphiques en barres (VMs créées/jour, commandes IA/jour).

- `/logs` : **Journal** — historique des actions avec :
  - Onglet « Activité » : journal des opérations sur les VMs.
  - Onglet « Utilisation IA » : historique des commandes IA.

- `/profile` : **Profil** — informations du compte avec :
  - Email, rôle, date de création.
  - Statistiques (VMs, commandes IA).
  - Barre de quota disque.

#### Portail administrateur

- `/admin` : **Tableau de bord admin** — vue globale du système :
  - Résumé système (utilisateurs, VMs, commandes IA).
  - Répartition des VMs par statut.
  - Utilisation du disque.

- `/admin/vms` : **Gestion des VMs (admin)** — toutes les VMs de tous les utilisateurs avec :
  - Liste complète des VMs.
  - Actions administrateur (démarrer, arrêter, supprimer, forcer la réinitialisation).

### 7.3 Composant VM Card (carte de VM)

Chaque VM est affichée sous forme de carte riche contenant :

- **En-tête** : nom, statut (badge coloré), badges ISO/RDP.
- **Informations** : OS, RAM, CPU, disque, statut, erreur éventuelle.
- **Boutons d'action rapides** : Démarrer, Arrêter, Pause, Reprise, Sauvegarder, Synchroniser, Supprimer.
- **Sections dépliables** :
  - ISO : attachement/détachement.
  - RDP : activation/désactivation avec port.
  - Matériel : modification RAM/CPU.
  - Ports : ajout/suppression de règles de transfert.
  - Snapshots : prise, restauration, suppression, liste.
  - Métriques : CPU et RAM en temps réel.
  - Clonage/Export : cloner ou exporter en OVA.
  - Planification : créer des schedules cron.

### 7.4 Composants réutilisables

| Composant | Description |
|---|---|
| `Logo` | Logo NexVM avec texte, taille configurable |
| `GlassCard` | Carte avec effet glass-morphism |
| `BackgroundLayer` | Arrière-plan décoratif (gradients, icônes flottantes) |
| `Toast` | Notifications (succès, erreur, avertissement) |
| `Modal` | Boîte de dialogue de confirmation (supporte Escape) |
| `VMCreateForm` | Formulaire de création de VM avec presets |
| `VMList` | Grille de cartes VM avec skeletons de chargement |

### 7.5 Navigation

Le portail utilisateur dispose d'une **sidebar latérale** avec les liens suivants :

- VMs (icône ordinateur)
- AI Assistant (icône robot)
- Analytics (icône graphique)
- Logs (icône document)
- Profile (icône utilisateur)
- Administration (icône bouclier, uniquement visible pour les admins)

---

## 8. Sécurité

### 8.1 Authentification

- **JWT (JSON Web Tokens)** via Supabase Auth avec expiration à 24h.
- **Vérification JWT** : clé publique asymétrique Supabase obtenue via JWKS.
- **Middleware d'authentification** sur toutes les routes protégées.
- **Création automatique du profil** si manquant lors de la première requête authentifiée.

### 8.2 Autorisation

- **Row Level Security (RLS)** au niveau de la base de données PostgreSQL.
- **Vérification du rôle admin** via `get_current_admin_user()` pour les routes d'administration.
- **Protection des routes frontend** via middleware Next.js :
  - Redirection des utilisateurs non authentifiés vers `/login`.
  - Redirection des admins vers `/admin` au lieu de `/vms`.
  - Vérification du cookie `nexvm_admin` pour les routes admin.

### 8.3 Protection contre les injections

- **Pas de shell=True** : toutes les commandes VBoxManage sont exécutées via une liste d'arguments subprocess.
- **Whitelist de commandes** : seules les commandes VBoxManage autorisées peuvent être exécutées.
- **Validation Pydantic** : toutes les données entrantes sont validées par des schémas stricts.

### 8.4 Validation IA

- **Whitelist d'actions** : seules les 12 actions prédéfinies sont acceptées.
- **Schéma Pydantic** : la réponse JSON de l'IA est validée structurellement avant exécution.
- **Limitation de débit** : 10 commandes IA par minute par utilisateur.

### 8.5 CORS

- Le backend n'accepte les requêtes que depuis l'URL du frontend configurée (`FRONTEND_URL`).
- Les en-têtes CORS sont préservés même en cas d'erreur 500.

---

## 9. Technologies et outils

### 9.1 Stack technique complète

| Couche | Technologie | Version |
|---|---|---|
| **Langage backend** | Python | 3.12 |
| **Framework backend** | FastAPI | Dernière version |
| **Serveur ASGI** | Uvicorn | Dernière version |
| **Validation de données** | Pydantic | V2 |
| **Client base de données** | Supabase Python | >= 2.0.0 |
| **JWT** | python-jose[cryptography] | Dernière version |
| **Client HTTP** | httpx | >= 0.27.0 |
| **Client IA** | Groq Python SDK | >= 0.11.0 |
| **Planification** | APScheduler | >= 3.10.0 |
| **Langage frontend** | TypeScript | 5.x |
| **Framework frontend** | Next.js | 14.2 |
| **UI** | React | 18 |
| **Styles** | Tailwind CSS | 3.4 |
| **Graphiques** | Recharts | 3.8 |
| **Base de données** | PostgreSQL (Supabase) | — |
| **Authentification** | Supabase Auth | — |
| **IA** | Groq API / Llama 4 Scout | — |
| **Virtualisation** | Oracle VirtualBox / VBoxManage | — |

### 9.2 Configuration backend

Variables d'environnement (fichier `.env`) :

| Variable | Obligatoire | Description |
|---|---|---|
| `SUPABASE_URL` | Oui | URL du projet Supabase |
| `SUPABASE_KEY` | Oui | Clé anonyme Supabase |
| `SUPABASE_SERVICE_KEY` | Oui | Clé de service Supabase |
| `GROQ_API_KEY` | Oui | Clé API Groq |
| `FRONTEND_URL` | Non | URL du frontend (défaut : `http://localhost:3000`) |
| `VBOXMANAGE_PATH` | Non | Chemin de VBoxManage (défaut : `VBoxManage`) |
| `VM_STORAGE_PATH` | Non | Répertoire de stockage des VMs (défaut : `~/VirtualBox VMs`) |
| `VM_QUOTA_PER_USER` | Non | Quota de VMs par utilisateur (défaut : 5) |
| `VM_QUOTA_DISK_MB` | Non | Quota disque par utilisateur en Mo (défaut : 200 000) |

### 9.3 Configuration frontend

Variables d'environnement :

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL du projet Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clé anonyme Supabase |
| `NEXT_PUBLIC_API_URL` | URL du backend API |

---

## 10. Tests

### 10.1 Tests backend

Le projet comprend **78 tests unitaires et d'intégration** organisés comme suit :

| Fichier | Tests | Couverture |
|---|---|---|
| `test_auth.py` | 3 | Authentification JWT (valide, expiré, manquant) |
| `test_vm_service.py` | 15 | Cycle de vie de base (créer, démarrer, arrêter, supprimer, quota, erreurs) |
| `test_ai_service.py` | 17 | Pipeline IA (12 actions, validation, rate limit, multilingue, chat) |
| `test_analytics_service.py` | 7 | Statistiques utilisateur et admin |
| `test_vm_p1_service.py` | 10 | ISO et VRDE/RDP |
| `test_vm_p2_service.py` | 11 | Modification, pause/reprise, ports, snapshots |
| `test_vm_p3_service.py` | 8 | Clonage, export OVA, import OVA |
| `test_vm_spec011_service.py` | 7 | Métriques CPU/RAM, quotas disque |
| `test_integration_vbox.py` | 7 | Tests d'intégration réels avec VirtualBox |

### 10.2 Exécution des tests

```bash
cd backend
pytest                              # Tous les tests unitaires
pytest -m integration               # Tests d'intégration VirtualBox uniquement
pytest tests/test_ai_service.py     # Tests du service IA uniquement
```

### 10.3 Configuration de test

Les tests utilisent des **mocks** pour les dépendances externes (Supabase, Groq, VBoxManage), permettant une exécution rapide et fiable sans infrastructure réelle.

---

## 11. Déploiement

### 11.1 Architecture de déploiement

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Vercel    │     │   Render    │     │ Supabase Cloud  │
│  (Frontend) │────▶│  (Backend)  │────▶│ (DB + Auth)     │
│  Next.js    │     │  FastAPI    │     │ PostgreSQL      │
└─────────────┘     └──────┬──────┘     └─────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Machine     │
                    │ hôte locale │
                    │ VirtualBox  │
                    └─────────────┘
```

### 11.2 Docker — Conteneurisation complète

NexVM est entièrement conteneurisable via Docker. Chaque composant possède son propre `Dockerfile` et un `docker-compose.yml` à la racine orchestre les deux services.

#### 11.2.1 Dockerfile du backend

```dockerfile
FROM python:3.12-slim
# Utilisateur non-root pour la sécurité
# Installe les dépendances Python depuis requirements.txt
# Copie le code applicatif (app/)
# Expose le port 8000 — Uvicorn en point d'entrée
```

Caractéristiques :
- Image de base : `python:3.12-slim` (légère).
- Utilisateur non-root (`appuser`) pour la sécurité.
- Point de montage `/vm-storage` pour le stockage des VMs.
- Port exposé : `8000`.

#### 11.2.2 Dockerfile du frontend

```dockerfile
# Build multi-étapes (multi-stage build) :
# 1. deps   — installation des dépendances npm
# 2. builder— compilation Next.js (next build)
# 3. runner — image finale minimale avec le standalone output
```

Caractéristiques :
- Image de base : `node:20-alpine` (ultra-légère).
- **Build multi-étapes** optimisé pour la taille de l'image finale.
- Utilisation du mode `standalone` de Next.js (configuration `output: "standalone"`).
- Utilisateur non-root (`nextjs`).
- Port exposé : `3000`.

#### 11.2.3 Docker Compose (orchestration)

Un fichier `docker-compose.yml` à la racine du projet orchestre les deux services :

| Service | Image | Port | Dépendances |
|---|---|---|---|
| `backend` | Backend Dockerfile | `8000:8000` | Montage VirtualBox + VM storage depuis l'hôte |
| `frontend` | Frontend Dockerfile | `3000:3000` | Dépend de `backend` |

**Volumes montés :**

- `${VBOX_INSTALL_PATH}:/vbox:ro` — accès en lecture seule au binaire VirtualBox de l'hôte.
- `${VM_STORAGE_HOST_PATH}:/vm-storage` — stockage des fichiers de VMs partagé avec l'hôte.

**Réseau :** Les deux services communiquent via un réseau bridge dédié (`nexvm-network`).

#### 11.2.4 Lancement

```bash
# Copier et remplir les fichiers d'environnement
cp .env.example .env
cp backend/.env.example backend/.env

# Construire et démarrer les deux services
docker-compose up --build

# Démarrer en arrière-plan
docker-compose up -d --build

# Arrêter les services
docker-compose down
```

Après démarrage :
- **Frontend** accessible sur `http://localhost:3000`
- **Backend** accessible sur `http://localhost:8000`
- **API health check** sur `http://localhost:8000/api/v1/health`

#### 11.2.5 Variables d'environnement Docker

Fichier `.env` à la racine du projet :

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL du projet Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clé anonyme Supabase |
| `VBOX_INSTALL_PATH` | Chemin de l'installation VirtualBox sur l'hôte (ex. : `C:\Program Files\Oracle\VirtualBox`) |
| `VM_STORAGE_HOST_PATH` | Chemin du répertoire de stockage des VMs sur l'hôte |

### 11.3 Prérequis d'installation

1. **Machine hôte** : Oracle VirtualBox installé.
2. **Backend** : Python 3.12+, dépendances via `pip install -r requirements.txt`.
3. **Frontend** : Node.js 18+, dépendances via `npm install`.
4. **Base de données** : Projet Supabase configuré avec les migrations appliquées.
5. **Docker (optionnel)** : Docker et Docker Compose pour le déploiement conteneurisé.

---

## 12. Structure des fichiers

```
NexVM/
├── docker-compose.yml              # Orchestration Docker (backend + frontend)
├── .env.example                    # Variables d'environnement Docker Compose
├── .gitignore
├── CLAUDE.md                       # Instructions pour l'assistance IA
├── README.md                       # Documentation du projet
│
├── backend/
│   ├── .env                        # Variables d'environnement (non versionné)
│   ├── .env.example                # Template des variables d'environnement
│   ├── requirements.txt            # Dépendances Python
│   ├── dev-requirements.txt        # Dépendances de développement
│   ├── Dockerfile                  # Image Docker du backend (Python 3.12-slim)
│   ├── pytest.ini                  # Configuration pytest
│   ├── test_vbox.py                # Test manuel VirtualBox
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Point d'entrée FastAPI + lifespan
│   │   ├── config.py               # Configuration Pydantic Settings
│   │   ├── db.py                   # Client Supabase global
│   │   ├── dependencies.py         # Dépendances d'authentification (JWT)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── enums.py            # Énumérations (VMStatus, LogAction)
│   │   │   └── schemas.py          # Schémas Pydantic (392 lignes)
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Routes d'authentification
│   │   │   ├── health.py           # Route de santé
│   │   │   ├── vm.py               # Routes de gestion des VMs (25 endpoints)
│   │   │   ├── admin_vm.py         # Routes d'administration VM
│   │   │   ├── ai.py               # Route de l'assistant IA
│   │   │   ├── analytics.py        # Routes analytiques
│   │   │   ├── logs.py             # Routes des logs
│   │   │   └── schedules.py        # Routes de planification
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── vm_service.py       # Service de gestion des VMs (1009 lignes)
│   │   │   ├── ai_service.py       # Service IA (478 lignes)
│   │   │   ├── analytics_service.py# Service analytique
│   │   │   ├── schedule_service.py # Service de planification
│   │   │   └── vbox_wrapper.py     # Wrapper VirtualBox
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── logger.py           # Logger structuré JSON
│   └── tests/
│       ├── __init__.py
│       ├── test_auth.py
│       ├── test_vm_service.py
│       ├── test_ai_service.py
│       ├── test_analytics_service.py
│       ├── test_vm_p1_service.py
│       ├── test_vm_p2_service.py
│       ├── test_vm_p3_service.py
│       ├── test_vm_spec011_service.py
│       └── test_integration_vbox.py
│
├── frontend/
│   ├── .env.example                # Template des variables d'environnement
│   ├── .env.local                  # Variables d'environnement (non versionné)
│   ├── .eslintrc.json              # Configuration ESLint
│   ├── Dockerfile                  # Image Docker du frontend (multi-stage, Node 20-alpine)
│   ├── package.json                # Dépendances et scripts
│   ├── next.config.mjs             # Configuration Next.js (standalone output)
│   ├── postcss.config.mjs          # Configuration PostCSS
│   ├── tailwind.config.ts          # Configuration Tailwind (thème cyberpunk)
│   ├── tsconfig.json               # Configuration TypeScript
│   ├── middleware.ts                # Middleware de protection des routes
│   ├── public/
│   │   ├── favicon.ico
│   │   └── logo.png
│   ├── app/
│   │   ├── layout.tsx              # Layout racine
│   │   ├── globals.css             # Styles globaux
│   │   ├── icon.png
│   │   ├── fonts/
│   │   │   ├── GeistVF.woff
│   │   │   └── GeistMonoVF.woff
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx      # Page de connexion
│   │   │   └── signup/page.tsx     # Page d'inscription
│   │   ├── (landing)/
│   │   │   ├── layout.tsx          # Layout landing
│   │   │   └── page.tsx            # Page d'accueil marketing
│   │   └── (portal)/
│   │       ├── layout.tsx          # Layout portail (sidebar)
│   │       ├── admin/page.tsx      # Tableau de bord admin
│   │       ├── admin/vms/page.tsx  # Gestion VMs admin
│   │       ├── ai/page.tsx         # Chat IA
│   │       ├── analytics/page.tsx  # Analytique
│   │       ├── logs/page.tsx       # Journal
│   │       ├── profile/page.tsx    # Profil utilisateur
│   │       └── vms/page.tsx        # Gestion des VMs
│   ├── components/
│   │   ├── Logo.tsx                # Logo NexVM
│   │   ├── admin-vms-client.tsx    # Gestion VMs admin (client)
│   │   ├── ai-chat.tsx            # Interface de chat IA
│   │   ├── analytics-client.tsx   # Graphiques analytiques
│   │   ├── background-layer.tsx   # Arrière-plan décoratif
│   │   ├── glass-card.tsx         # Carte glass-morphism
│   │   ├── logs-client.tsx        # Journal d'activité
│   │   ├── modal.tsx              # Modal de confirmation
│   │   ├── profile-client.tsx     # Profil utilisateur
│   │   ├── toast.tsx              # Notifications toast
│   │   ├── vm-card.tsx            # Carte de VM (571 lignes)
│   │   ├── vm-create-form.tsx     # Formulaire de création de VM
│   │   ├── vm-list.tsx            # Liste de VMs
│   │   └── vms-client.tsx         # Page VMs principale (client)
│   ├── hooks/
│   │   └── use-auth.ts            # Hook d'authentification React
│   ├── lib/
│   │   ├── api.ts                 # Client API avec injection JWT
│   │   ├── auth.ts                # Gestion des cookies d'auth
│   │   └── supabase/
│   │       ├── client.ts          # Client Supabase navigateur
│   │       ├── middleware.ts       # Gestion session middleware
│   │       └── server.ts          # Client Supabase serveur
│   └── types/
│       └── index.ts               # Types TypeScript
│
├── supabase/
│   ├── config.toml                 # Configuration Supabase locale
│   └── migrations/
│       ├── 001_initial_schema.sql  # Schéma initial (profiles, vms, logs, ai_usage)
│       ├── 002_vm_hardware_fields.sql # Ajout cpu, disk_size, vbox_id
│       └── 003_vm_schedules.sql    # Table vm_schedules + actions étendues
│
├── specs/                          # Spécifications de fonctionnalités (12 features)
├── docs/
│   └── implementation-plan.md      # Plan d'implémentation
└── rapport/                        # Rapport de stage (Markdown + PDF)
    ├── description-complete.md     # Description complète du projet
    ├── chapitre1.md
    ├── chapitre2.md
    ├── chapitre1.pdf
    ├── chapitre2.pdf
    ├── toc-newpage.tex
    └── README.md
```

---

## Annexe — Chiffres clés du projet

| Métrique | Valeur |
|---|---|
| Endpoints API | 47 |
| Tests automatisés | 78 |
| Tables de base de données | 5 (+ vm_snapshots) |
| Actions IA supportées | 12 |
| Systèmes d'exploitation supportés | 14 |
| Lignes de code backend (services) | ~2 200 |
| Lignes de code frontend (components) | ~2 500 |
| Fonctionnalités VM | 25+ opérations |
| Types d'actions journalisées | 22 |
| Planification (sprints) | 4 sprints |
