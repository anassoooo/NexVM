# VM Module — Audit des fonctionnalités manquantes

> Date : 2026-04-21  
> Branche : 004-analytics  

---

## Bugs actuels (à corriger en priorité)

| Fichier | Problème |
|---|---|
| `ai_service.py:153` | `list_vms()` appelé **sans `user_id`** → `TypeError` au runtime |
| `ai_service.py:266` | `create_vm` via AI ne passe **pas `cpu`/`disk_size`** → valeurs par défaut systématiquement |
| `ai_service.py:259` | `list_vms` dans `_execute_action` sans `user_id` → liste toutes les VMs de tous les users |
| `admin_vm.py:19,26,33` | `body.vm_id` passé en `UUID` objet, service attend `str` → crash potentiel |
| `backend/.env` | `VM_STORAGE_PATH` absent → VMs créées dans `~/VirtualBox VMs` sans contrôle |

---

## Fonctionnalités manquantes

### Critique (le module est inutilisable sans ça)

| # | Fonctionnalité | Pourquoi critique |
|---|---|---|
| 1 | **ISO / boot media** | Les VMs démarrent mais n'ont **aucun OS** — elles bootent dans le vide. Il faut attacher une ISO pour installer le système. |
| 2 | **Accès distant (VRDE/VNC)** | Impossible d'**interagir** avec une VM en cours d'exécution. VirtualBox intègre VRDE (Remote Desktop) qu'on peut activer par `modifyvm --vrde on --vrdeport <port>`. |
| 3 | **Polling automatique du statut** | Le bouton Sync est manuel. Les états `starting`/`stopping` ne se résolvent **jamais automatiquement** sans refresh. |

### Important (lifecycle complet)

| # | Fonctionnalité | Détail |
|---|---|---|
| 4 | **Modifier une VM** | Changer RAM/CPU/disk pendant que la VM est arrêtée (`modifyvm --memory --cpus`) |
| 5 | **Pause / Resume** | `controlvm <name> pause` / `resume` — utile pour libérer des ressources sans perdre l'état |
| 6 | **Save State** | `controlvm <name> savestate` — hibernate la VM avec son état mémoire |
| 7 | **Gestion des port-forwarding** | Le port SSH `2222` est hardcodé. Il faut une API pour ajouter/supprimer des règles NAT |
| 8 | **Snapshots** | `snapshot take/restore/delete` — indispensable pour les environnements de test |

### Qualité / Production

| # | Fonctionnalité | Détail |
|---|---|---|
| 9 | **Clone VM** | `VBoxManage clonevm` — dupliquer une VM existante |
| 10 | **Import/Export OVA** | `VBoxManage import/export` — portabilité des machines |
| 11 | **Métriques temps réel** | `VBoxManage metrics query` — CPU%, RAM utilisée, I/O réseau |
| 12 | **Système de quotas disque** | Actuellement quota = nombre de VMs. Pas de limite de stockage total |
| 13 | **AI prompt : cpu/disk_size** | Le prompt système AI ne mentionne pas les nouveaux champs |
| 14 | **Logs frontend** | Aucune page pour consulter les `logs` et `ai_usage` de la DB |

---

## Résumé par priorité

```
P0 (bugs)      — corriger maintenant   : 5 bugs listés ci-dessus
P1 (critique)                          : ISO, VRDE, auto-polling
P2 (lifecycle)                         : Modify VM, Pause/Resume, SaveState, Port-forwarding, Snapshots
P3 (production)                        : Clone, Import/Export, Métriques, Quotas disque, Logs frontend
```
