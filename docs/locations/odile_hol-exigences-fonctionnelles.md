
# 📍 Service de signalement des déchets : exigences

| | |
|---|---|
| **Service** | `services/locations` (Location Reporting Service) |
| **Objectif du projet** | Objectif 1 : collecter les emplacements de déchets |
| **Auteure** | Odile Hol |
| **Cours** | Systèmes distribués et Cloud Computing (ISN 4131), semaine 1 |
| **Statut** | Brouillon soumis à relecture |

---

## 🎯 1. Rôle du service

Ce service permet de **signaler un dépôt de déchets** (où il se trouve, de quel type, en quelle quantité), de **l'enregistrer** de façon fiable et de **le partager** avec les autres services du système : la carte, les demandes de collecte au SPF et le temps réel.

C'est la **source de vérité** des données de déchets : la carte n'affiche que ce qui est signalé ici, et une demande de collecte concerne toujours un emplacement signalé ici.

## 👥 2. Utilisateurs

| Utilisateur | Rôle |
|---|---|
| **Citoyen** | Signale un dépôt de déchets depuis un formulaire web. |
| **Agent de terrain** | Signale sur place, parfois sans connexion Internet. |
| **Superviseur** | Vérifie, corrige et met à jour les signalements de son district. |
| **Administrateur** | Gère les comptes, les rôles et les districts. |
| **Poubelle connectée (IoT)** | Envoie automatiquement son niveau de remplissage. |

## ✅ 3. Exigences fonctionnelles

**Priorité :** 🔴 indispensable · 🟠 importante · 🟢 souhaitable

| ID | Exigence | Priorité |
|----|----------|:--------:|
| EF-1 | **Créer un signalement** avec la position (latitude, longitude), le type de déchet et la quantité estimée. La date, la source et l'auteur sont ajoutés par le serveur. | 🔴 |
| EF-2 | **Choisir la position** avec le GPS de l'appareil ou en plaçant un point sur la carte (solution de secours si le GPS est imprécis). | 🔴 |
| EF-3 | **Valider les données** : coordonnées valides, champs obligatoires présents, valeurs autorisées. Sinon, renvoyer une erreur claire au format unique. | 🔴 |
| EF-4 | **Consulter** un signalement à partir de son identifiant. | 🔴 |
| EF-5 | **Lister et rechercher** les signalements par zone, type de déchet, quantité, statut et ancienneté, avec pagination. | 🔴 |
| EF-6 | **Modifier** la quantité et le statut d'un signalement (utilisateur autorisé). | 🔴 |
| EF-7 | **Conserver un historique** des modifications : qui, quand, ancienne et nouvelle valeur. | 🟠 |
| EF-8 | **Prévenir les autres services** à chaque création ou modification, par un événement. | 🔴 |
| EF-9 | **Gérer les droits** selon le rôle (citoyen, agent, superviseur, administrateur). | 🔴 |
| EF-10 | **Recevoir les mesures des poubelles connectées** (MQTT), les valider et mettre à jour le signalement correspondant. | 🟠 |
| EF-11 | **Enregistrer hors ligne** : un agent envoie plus tard ses signalements, sans créer de doublons. | 🟠 |
| EF-12 | **Détecter les doublons** : un signalement très proche d'un signalement ouvert est marqué comme doublon potentiel. | 🟠 |
| EF-13 | **Séparer par district** : un utilisateur ne voit que les signalements de son district. | 🟠 |
| EF-14 | **Joindre une photo** et une description libre. | 🟢 |
| EF-15 | **Fournir une route de santé** `GET /healthz` pour vérifier que le service fonctionne. | 🔴 |

### 📊 Quantité estimée

| Tranche | Estimation |
|---|---|
| Vide | 0 à 10 % |
| Faible | 11 à 40 % |
| Modérée | 41 à 70 % |
| Élevée | 71 à 90 % |
| Débordement | plus de 90 % |

Un signalement sans mise à jour depuis plus de **7 jours** est considéré comme **périmé**.

### 🔄 Statuts d'un signalement (proposition)

`OUVERT` → `COLLECTE_DEMANDEE` → `COLLECTE`

Un signalement erroné passe à `INVALIDE` : il est conservé et jamais supprimé en silence.

## ⚙️ 4. Exigences non fonctionnelles

| Domaine | Exigence |
|---|---|
| ⚡ **Performance** | Les recherches par zone restent rapides quand le nombre de signalements augmente : index spatial GiST, pagination et nombre maximal de résultats par requête. |
| 🔒 **Sécurité** | Authentification par la passerelle (JWT), droits selon le rôle, validation stricte des entrées, aucun secret ni fichier `.env` dans le dépôt, aucune donnée personnelle de citoyen dans les journaux. |
| 🛡️ **Fiabilité** | Reprise automatique après une perte de connexion (base de données, Redis, MQTT), sans arrêt du service. Un message invalide est rejeté et journalisé, sans bloquer le reste. |
| 🌐 **Disponibilité** | Service sans état : plusieurs instances peuvent tourner en parallèle derrière la passerelle. |
| 🔁 **Cohérence** | Deux modifications simultanées d'un même signalement ne corrompent pas les données (transactions et numéro de version). |
| 🧱 **Isolation** | Le service ne lit jamais la base d'un autre service. Il communique uniquement par HTTP ou par événements. |
| 🔧 **Maintenabilité** | Code Python typé (mypy), vérifié par Ruff, tests avec `pytest`, migrations Alembic réversibles, interface décrite en OpenAPI dans `docs/api/`. |
| 🔍 **Observabilité** | Journaux structurés avec un identifiant de requête pour suivre un appel à travers plusieurs services. |
| 🐳 **Déploiement** | Le service dispose d'un `Dockerfile` et fonctionne avec `docker compose up` depuis un clone propre. |
| ♿ **Utilisabilité** | Messages d'erreur compréhensibles ; formulaire utilisable sur téléphone, y compris avec une connexion lente. |

## 📌 5. Contraintes du projet

- Base de données **PostgreSQL + PostGIS**.
- Aucune couleur codée en dur : les couleurs de la carte viennent de `palette.json`.
- Chaque pull request indique l'objectif concerné (ici : **Objectif 1**).

## 🛠️ 6. Comment je compte résoudre le problème

1. **Documenter** : ce document, le schéma de la base de données et la liste des routes de l'API.
2. **Préparer l'environnement** : fork, branche, `docker compose up`, route `/healthz`.
3. **Créer la base** : table des signalements avec une colonne de position PostGIS et un index.
4. **Construire l'API** (FastAPI) : créer, consulter, rechercher et modifier, avec validation des données.
5. **Ajouter ensuite** : historique, événements, réception MQTT, mode hors ligne, rôles et districts.
6. **Tester** : tests unitaires, tests d'intégration et test de modifications simultanées.
7. **Livrer par petites étapes** : une pull request par sujet, relue par d'autres étudiants avant la fusion.

## ❓ 7. Questions pour l'enseignant

1. L'état des routes doit-il aussi être signalé dans ce service, ou est-ce un autre service ?
2. Quelles fonctions sont obligatoires et lesquelles sont facultatives (hors ligne, photos, doublons) ?
3. Quelle technologie suivre : **Node.js/Express** (plan de 100 tâches) ou **Python/FastAPI** (CONTRIBUTING.md) ?
4. La documentation peut-elle être rédigée en français ?
5. La quantité est-elle une tranche (vide à débordement) ou une valeur numérique ?
6. Un citoyen peut-il signaler sans compte ?
7. Un signalement doit-il être validé par un superviseur avant d'apparaître sur la carte ?
8. Qui reçoit les messages MQTT des poubelles : ce service ou le composant IoT ?
9. Les photos sont-elles demandées, et où les stocker ?
10. Pour un même service, chaque étudiant rédige-t-il son propre document ?
