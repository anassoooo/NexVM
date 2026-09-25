# Chapitre 1 : Cadre général du projet

## 1.1 Présentation du lieu de stage

### 1.1.1 Présentation d'AttijariBank

AttijariBank est l'une des principales banques tunisiennes, filiale du groupe marocain Attijariwafa Bank. Créée en 2002, elle est cotée à la Bourse de Tunis et opère dans les domaines de la banque de détail, la banque d'investissement et les services financiers. AttijariBank dispose d'un réseau de plus de 150 agences réparties sur l'ensemble du territoire tunisien et emploie plusieurs milliers de collaborateurs.

La banque accompagne une clientèle diversifiée — particuliers, professionnels, entreprises et institutionnels — en proposant une gamme complète de produits et services bancaires : comptes courants, crédits, épargne, assurance, banque à distance et solutions de paiement électronique.

AttijariBank s'inscrit dans une démarche de modernisation continue de ses systèmes d'information, visant à améliorer la qualité de service, renforcer la sécurité des données et optimiser les processus opérationnels.

### 1.1.2 La Direction des Systèmes d'Information (DSI)

Le stage s'est déroulé au sein de la **Direction des Systèmes d'Information (DSI)** d'AttijariBank. Cette direction est chargée de la conception, du développement, du déploiement et de la maintenance de l'ensemble des solutions informatiques de la banque. Ses missions principales incluent :

- La gestion de l'infrastructure technique (serveurs, réseaux, postes de travail).
- Le développement et la maintenance des applications métiers.
- L'administration des bases de données et la sécurité de l'information.
- L'accompagnement technologique des projets de transformation digitale.

La DSI joue un rôle stratégique dans l'organisation, car elle garantit la disponibilité, la performance et la sécurité des systèmes sur lesquels reposent l'ensemble des activités bancaires.

### 1.1.3 Cadre du stage

Le stage a été effectué au sein de la DSI d'AttijariBank, sous l'encadrement de **M. Hosni Kricha**, encadrant professionnel au sein de la banque. L'encadrement académique a été assuré par **M. Samir Felhi**, enseignant à l'**ISET Kasserine** (Université de Kairouan).

La stagiaire, **Nour Riahi**, étudiante en fin de cycle à l'ISET Kasserine, a été amenée à travailler sur un projet de développement d'une application web de gestion de machines virtuelles, destinée à simplifier l'administration des environnements de virtualisation utilisés par les équipes techniques de la banque.

---

## 1.2 Étude de l'existant

### 1.2.1 La virtualisation dans les environnements professionnels

La virtualisation est une technologie fondamentale dans les infrastructures informatiques modernes. Elle permet de créer plusieurs environnements isolés — appelés machines virtuelles (VMs) — sur un seul serveur physique, optimisant ainsi l'utilisation des ressources matérielles.

Dans le contexte d'une institution bancaire comme AttijariBank, la virtualisation est utilisée pour :

- **Le développement et les tests** : créer des environnements isolés pour tester de nouvelles applications sans impacter les systèmes de production.
- **La formation** : mettre à disposition des environnements reproductibles pour les sessions de formation des collaborateurs.
- **L'expérimentation technique** : évaluer de nouvelles configurations, de nouveaux systèmes d'exploitation ou de nouveaux outils dans un cadre sécurisé.

Oracle VirtualBox est l'un des hyperviseurs les plus répandus dans les environnements de développement. Open source et multiplateforme, il permet de créer, gérer et exécuter des machines virtuelles sur des postes de travail standards.

### 1.2.2 Méthodes actuelles de gestion des machines virtuelles

Actuellement, la gestion des machines virtuelles VirtualBox au sein de la DSI s'effectue principalement par deux moyens :

**a) Via l'interface graphique de VirtualBox (GUI)**

L'interface graphique de VirtualBox offre une visualisation directe des machines virtuelles et permet d'effectuer les opérations de base : création, démarrage, arrêt et suppression. Toutefois, cette approche présente plusieurs limites significatives dans un contexte professionnel :

- Elle nécessite un accès physique ou une connexion Bureau à distance à la machine hôte.
- Elle ne permet pas une gestion centralisée depuis un navigateur web.
- Elle n'offre aucune traçabilité des actions effectuées (pas de journal d'audit).
- Elle est limitée à un seul utilisateur à la fois sur la machine hôte.

**b) Via la ligne de commande VBoxManage**

`VBoxManage` est l'outil en ligne de commande de VirtualBox. Il permet d'automatiser l'ensemble des opérations sur les machines virtuelles. Cependant, son utilisation présente des obstacles non négligeables :

- Elle requiert une connaissance approfondie de la syntaxe des commandes et de leurs paramètres.
- Elle nécessite un accès SSH ou terminal à la machine hôte, ce qui restreint son usage aux profils techniques.
- La documentation des commandes est exclusivement en anglais.
- Aucune interface conviviale ne guide l'utilisateur dans ses actions.

### 1.2.3 Limites de l'existant

L'analyse de l'existant met en évidence les insuffisances suivantes :

| Critère | Situation actuelle |
|---|---|
| Accessibilité | Limitée à la machine hôte ou via connexion SSH |
| Interface utilisateur | CLI technique ou GUI locale uniquement |
| Multi-utilisateurs | Non pris en charge nativement |
| Traçabilité | Aucun journal d'audit automatique |
| Interactivité | Commandes manuelles complexes à mémoriser |
| Visibilité globale | Aucun tableau de bord analytique |
| Accessibilité linguistique | Uniquement en anglais pour la CLI |

Ces constats mettent en évidence la nécessité de développer une solution moderne et centralisée permettant de pallier l'ensemble de ces limitations.

---

## 1.3 Problématique

La gestion des machines virtuelles dans un environnement professionnel multi-utilisateurs, tel que celui de la DSI d'AttijariBank, soulève plusieurs problèmes majeurs qui freinent l'efficacité opérationnelle des équipes techniques.

**Problème 1 — Barrière technique**

L'utilisation de `VBoxManage` nécessite une expertise technique avancée. Tout utilisateur souhaitant créer ou contrôler une machine virtuelle doit maîtriser une syntaxe de commandes complexe, ce qui exclut les profils non techniques (analystes fonctionnels, chefs de projet, collaborateurs en formation). Cette dépendance à l'égard des administrateurs système constitue un goulot d'étranglement opérationnel.

**Problème 2 — Absence d'interface centralisée**

Il n'existe actuellement aucune plateforme web permettant de gérer les machines virtuelles VirtualBox à distance, depuis un simple navigateur, avec authentification sécurisée et isolation des données entre utilisateurs. Chaque intervention requiert un accès direct à la machine hôte.

**Problème 3 — Manque de traçabilité**

Les opérations réalisées sur les machines virtuelles ne sont pas enregistrées automatiquement dans un journal d'audit. En cas d'incident — arrêt intempestif, suppression accidentelle, erreur de configuration — il est impossible de retracer l'historique des actions et d'identifier la cause.

**Problème 4 — Absence d'interaction naturelle**

Les utilisateurs doivent connaître exactement les commandes à exécuter et leurs paramètres. Il n'existe aucun système capable de comprendre des instructions formulées en langage naturel (ex. : « crée une VM Ubuntu avec 4 Go de RAM ») et de les traduire automatiquement en actions concrètes.

**Problème 5 — Manque de visibilité analytique**

Les administrateurs ne disposent d'aucune vue d'ensemble sur l'état du parc de machines virtuelles : nombre de VMs actives, répartition par statut, historique des erreurs, utilisation des ressources. Cette absence de visibilité complique la supervision et la prise de décision.

**Formulation de la problématique :**

Comment concevoir et développer une application web permettant aux utilisateurs de gérer leur parc de machines virtuelles VirtualBox de manière centralisée, sécurisée, traçable et accessible via une interface conversationnelle en langage naturel ?

---

## 1.4 Solution proposée

Pour répondre à cette problématique, nous proposons **NexVM** (*my Virtual Machine System*), une application web fullstack permettant la gestion complète du cycle de vie des machines virtuelles VirtualBox à travers une interface intelligente et conversationnelle.

La solution repose sur quatre piliers complémentaires :

### Pilier 1 — Authentification et sécurité

Un système d'authentification robuste basé sur **Supabase Auth** protège l'accès à toutes les fonctionnalités. Chaque utilisateur dispose d'un espace isolé grâce aux politiques de sécurité au niveau des lignes (Row Level Security) de PostgreSQL. Un mécanisme de rôles (utilisateur régulier / administrateur) différencie les droits d'accès : les utilisateurs gèrent leurs propres VMs via l'assistant IA, tandis que les administrateurs disposent d'un panneau de contrôle centralisé.

### Pilier 2 — Gestion du cycle de vie des machines virtuelles

Une API RESTful expose l'ensemble des opérations du cycle de vie des VMs — création, démarrage, arrêt, suppression — en encapsulant les appels à `VBoxManage` via un wrapper sécurisé. Chaque action est soumise à une machine à états stricte qui garantit la cohérence des transitions (ex. : une VM ne peut être démarrée que si elle est à l'état arrêté). Toute action est automatiquement journalisée dans la base de données.

### Pilier 3 — Interface en langage naturel par intelligence artificielle

Un module de traitement des commandes par intelligence artificielle, basé sur le modèle **Llama 4 Scout** via l'API **Groq**, interprète les instructions formulées en langage naturel par l'utilisateur — dans toutes les langues — et les traduit en appels à l'API de gestion des VMs. L'utilisateur n'a jamais besoin de connaître la syntaxe technique. L'assistant IA est également capable de mener des conversations générales et de répondre aux questions des utilisateurs sur la virtualisation.

### Pilier 4 — Tableau de bord analytique

Des tableaux de bord offrent une visibilité en temps réel sur le système. L'assistant IA salue l'utilisateur à chaque connexion avec un résumé de ses VMs (nombre total, actives, arrêtées, en erreur). Les administrateurs disposent d'un panneau dédié présentant les métriques globales du système : nombre total d'utilisateurs, de VMs, répartition par statut et historique des commandes IA.

---

## 1.5 Description du projet

### 1.5.1 Présentation générale

**NexVM** est une application web fullstack de gestion de machines virtuelles VirtualBox. Elle offre une interface moderne, sécurisée et intelligente permettant aux utilisateurs d'interagir avec leurs VMs via un assistant conversationnel en langage naturel, et aux administrateurs de superviser l'ensemble du parc depuis un panneau d'administration structuré.

Le projet a été développé en adoptant une approche itérative et incrémentale, inspirée des principes Agile, organisée en quatre sprints :

| Sprint | Module | Contenu |
|---|---|---|
| Sprint 1 | Authentification et base de données | Supabase Auth, schéma SQL, middleware JWT |
| Sprint 2 | Gestion des VMs | API REST, wrapper VBoxManage, interface admin |
| Sprint 3 | Interface IA | Intégration Groq, chat en langage naturel |
| Sprint 4 | Analytique | Tableaux de bord utilisateur et administrateur |

### 1.5.2 Architecture technique

L'application s'articule autour de trois couches distinctes :

```
    FRONTEND (Vercel)
    Next.js 14 - TypeScript 5.x
    /login  /signup  /ai (chat IA)  /admin
                |
                | REST API (JSON)
                v
    BACKEND (Render)
    FastAPI - Python 3.12 - Uvicorn
    Auth | VM Service | AI Service | Analytics
            |                      |
            v                      v
    Supabase Cloud          VirtualBox (hote)
    PostgreSQL + Auth       VBoxManage CLI
    (DB + RLS + JWT)
```

Les composants principaux sont les suivants :

| Composant | Technologie | Rôle |
|---|---|---|
| Frontend | Next.js 14, TypeScript 5.x | Interface utilisateur (chat IA + administration) |
| Backend | FastAPI, Python 3.12 | API REST, logique métier |
| Base de données | Supabase PostgreSQL | Persistance, authentification, RLS |
| Intelligence artificielle | Groq API (Llama 4 Scout) | Interprétation du langage naturel |
| Virtualisation | VirtualBox / VBoxManage | Exécution des machines virtuelles |
| Déploiement | Render + Vercel + Supabase Cloud | Infrastructure cloud |

### 1.5.3 Modèle de données

Le schéma de base de données comprend quatre tables principales :

- **profiles** : Extension du compte utilisateur, portant le rôle administrateur (`is_admin`).
- **vms** : Enregistrements des machines virtuelles (nom, système d'exploitation, RAM, statut, message d'erreur).
- **logs** : Journal d'audit immuable de toutes les actions effectuées sur le système.
- **ai_usage** : Historique des commandes IA (prompt utilisateur, réponse, nombre de tokens).

Chaque table est protégée par des politiques de sécurité au niveau des lignes (Row Level Security) garantissant qu'un utilisateur ne peut accéder qu'à ses propres données.

### 1.5.4 Parcours utilisateur

**Utilisateur régulier :**

1. S'inscrit ou se connecte via le formulaire d'authentification sécurisé.
2. Est automatiquement redirigé vers l'interface de chat IA (`/ai`).
3. Reçoit un résumé de ses VMs à l'ouverture de la session.
4. Interagit avec ses VMs en langage naturel (ex. : « crée une VM Ubuntu avec 2 Go de RAM nommée test-vm »).
5. L'IA répond dans la langue de l'utilisateur et confirme les actions effectuées.

**Administrateur :**

1. Se connecte et est redirigé vers le panneau d'administration (`/admin`).
2. Consulte les métriques système globales (utilisateurs, VMs, commandes IA).
3. Gère les VMs de tous les utilisateurs via une interface dédiée (`/admin/vms`) avec des contrôles visuels.

---

## 1.6 Description des besoins

### 1.6.1 Besoins fonctionnels

Les besoins fonctionnels expriment ce que le système doit accomplir :

**BF-01 — Authentification et gestion des comptes**

- Le système doit permettre l'inscription et la connexion via email et mot de passe.
- Les sessions doivent persister pendant 24 heures et survivre aux rechargements de page.
- Un mécanisme de blocage doit être activé après 10 tentatives de connexion échouées.
- Chaque utilisateur doit être isolé des données des autres (Row Level Security).
- La politique de mot de passe impose un minimum de 8 caractères avec au moins un chiffre.

**BF-02 — Gestion du cycle de vie des machines virtuelles**

- Créer une VM en spécifiant un nom (1 à 50 caractères), un système d'exploitation et une RAM (entre 512 Mo et 16 384 Mo).
- Démarrer une VM arrêtée avec transition d'état : `stopped` → `starting` → `running`.
- Arrêter une VM en cours d'exécution avec transition : `running` → `stopping` → `stopped`.
- Supprimer une VM (uniquement à l'état arrêté).
- Consulter la liste de ses VMs avec leur statut en temps réel.

**BF-03 — Traitement des commandes par intelligence artificielle**

- Accepter des commandes en langage naturel dans toutes les langues (français, anglais, arabe, etc.).
- Interpréter la commande via le modèle Llama 4 Scout (API Groq).
- Valider le résultat de l'IA avant toute exécution (schéma Pydantic strict).
- Répondre dans la langue de l'utilisateur.
- Permettre les conversations générales (questions techniques, conseils).
- Appliquer une limite de 10 commandes IA par minute par utilisateur.

**BF-04 — Analytique et supervision**

- Afficher pour l'utilisateur : nombre total de VMs, répartition par statut, total de commandes IA.
- Afficher pour l'administrateur : nombre total d'utilisateurs, total de VMs, répartition globale, total de commandes IA.
- L'interface IA doit ouvrir chaque session avec un résumé des VMs de l'utilisateur.

**BF-05 — Administration**

- L'administrateur peut voir et contrôler les VMs de tous les utilisateurs.
- Les actions administrateur respectent les mêmes règles de transition d'état.
- Toutes les actions sont journalisées dans la table `logs`.

### 1.6.2 Besoins non fonctionnels

Les besoins non fonctionnels définissent les contraintes de qualité du système :

| Catégorie | Exigence |
|---|---|
| **Sécurité** | Toutes les routes protégées par JWT Supabase ; aucune écriture directe depuis le frontend ; appels VBoxManage via liste d'arguments (pas de shell=True pour éviter les injections) |
| **Performance** | Inscription en moins de 60 secondes ; middleware d'authentification inférieur à 100 ms par requête ; timeout VBoxManage à 30 secondes |
| **Fiabilité** | 100 % des actions VM génèrent une entrée dans le journal d'audit avant la réponse HTTP ; aucune commande IA non journalisée |
| **Maintenabilité** | Code Python 3.12 (backend) et TypeScript 5.x (frontend) avec conventions standard |
| **Disponibilité** | Déploiement cloud : Render (backend), Vercel (frontend), Supabase Cloud (base de données) |
| **Isolation des données** | Row Level Security PostgreSQL garantit qu'un utilisateur ne peut pas accéder aux données d'un autre |

### 1.6.3 Contraintes techniques

- Le backend s'exécute sur la même machine hôte que VirtualBox (appels subprocess locaux).
- Le modèle de données est figé dès la migration initiale.
- L'IA ne maintient pas de mémoire conversationnelle entre les sessions (traitement mono-tour).
- La limitation de débit IA est en mémoire vive (reset au redémarrage du serveur), acceptable pour un MVP mono-tenant.

---

*Fin du Chapitre 1*
