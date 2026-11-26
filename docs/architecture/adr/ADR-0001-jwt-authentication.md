# ADR-0001 : Architecture d'authentification JWT et de rafraîchissement des jetons

## Statut

Accepté (en cours de synchronisation avec les équipes microservices — Groupe 2 : Auth, Fonctionnalité 12).

## Contexte

### Architecture du système et modèle de menaces (Threat Model)

Le système DWMS (*Distributed Waste Management System*) repose sur une architecture distribuée orientée microservices exposée via une API Gateway à des clients hétérogènes : applications mobiles citoyennes, terminaux des agents de terrain, et interfaces web d'administration. 

Dans cet environnement distribué, le sous-système d'authentification est exposé aux menaces suivantes :
* **Interception et rejeu de jetons (Token Replay / Hijacking) :** Un jeton volé sur un réseau mobile non sécurisé ou via une faille XSS peut être réutilisé par un attaquant pour usurper l'identité d'un citoyen ou d'un agent.
* **Usurpation de privilèges et cloisonnement multi-tenant :** Un utilisateur authentifié sur un district donné (`tenant_id`) pourrait tenter d'accéder aux ressources ou signalements d'un autre district, ou d'usurper un rôle supérieur (`supervisor`, `admin`).
* **Compromission d'un microservice interne ou mouvement latéral :** Le réseau interne entre microservices ne peut pas être considéré comme implicitement fiable ; un service compromis ne doit pas pouvoir forger de jetons valides pour d'autres services.
* **Indisponibilité en cascade (Single Point of Failure) :** Une vérification synchrone systématique auprès du service d'authentification pour chaque requête métier créerait un goulot d'étranglement et paralyserait l'ensemble de la plateforme en cas de latence du service Auth.

### Objectifs de sécurité et principes Zero-Trust

Pour répondre à ces menaces, l'architecture d'authentification s'appuie sur quatre piliers :
1. **Zéro confiance implicite (Zero-Trust) :** Chaque microservice valide cryptographiquement et localement l'authenticité et l'intégrité des jetons reçus, sans faire aveuglément confiance au périmètre réseau ni se reposer uniquement sur la passerelle d'entrée.
2. **Séparation des responsabilités cryptographiques :** Seul le service d'authentification détient la clé privée permettant d'émettre des jetons ; les autres services ne disposent que de la clé publique de vérification.
3. **Limitation de la fenêtre d'exposition :** Les jetons d'accès possèdent une durée de vie très courte, couplée à un mécanisme de renouvellement contrôlé et révocable.
4. **Révocabilité déterministe :** Toute compromission détectée d'une session doit entraîner l'invalidation immédiate de la chaîne de rafraîchissement associée.

## Décision

### Structure des jetons d'accès (Access Token) et de rafraîchissement (Refresh Token)

L'authentification repose sur une architecture à double jeton :

1. **Access Token (JWT signé — Stateless) :**
   * **Durée de vie (`exp`) :** 15 minutes (900 secondes).
   * **Transport :** En-tête HTTP `Authorization: Bearer <token>`.
   * **Contrat de claims obligatoire (Payload) :**
     ```json
     {
       "iss": "dwms-auth-service",
       "aud": "dwms-microservices",
       "sub": "550e8400-e29b-41d4-a716-446655440000",
       "role": "field_agent",
       "tenant_id": "district-douala-01",
       "iat": 1732588800,
       "exp": 1732589700,
       "jti": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
     }
     ```
   * **Spécification des champs métiers :**
     * `sub` : Identifiant unique immuable (UUID) de l'utilisateur authentifié.
     * `role` : Rôle RBAC strict parmi `citizen`, `field_agent`, `supervisor` et `admin`.
     * `tenant_id` : Identifiant du district administratif permettant le filtrage et l'isolation des données multi-tenants.
     * `exp` / `iat` : Horodatages Unix d'expiration et d'émission.
     * `jti` : Identifiant unique du jeton à des fins de traçabilité et d'audit.

2. **Refresh Token (Jeton opaque — Stateful) :**
   * **Format :** Chaîne aléatoire cryptographiquement sûre de 256 bits (encodée en Base64URL), sans données métiers embarquées.
   * **Durée de vie :** 7 jours (avec expiration glissante bornée à 30 jours maximum).
   * **Stockage :**
     * Côté client web : Cookie `HttpOnly`, `Secure`, `SameSite=Strict` restreint au chemin `/api/v1/auth/refresh`.
     * Côté client mobile : Stockage sécurisé matériel (*Keystore* Android / *Keychain* iOS).
     * Côté serveur (Auth Service) : Stocké uniquement sous forme de condensat cryptographique (**SHA-256**) dans Redis/base de données, associé à `user_id`, `family_id`, `expires_at` et un indicateur `revoked`.

### Validation en périphérie (Gateway) vs vérification dans les microservices internes

Conformément au principe Zero-Trust, la validation est opérée en **défense en profondeur** à deux niveaux :

* **Niveau 1 — API Gateway (Filtrage de périphérie) :**
  * Vérifie la présence de l'en-tête `Authorization`, la structure syntaxique du JWT, sa signature et son expiration (`exp`) avant de router la requête.
  * Rejette immédiatement (`401 Unauthorized`) tout trafic non authentifié ou expiré afin de protéger les services internes contre les requêtes invalides.
* **Niveau 2 — Microservices internes (ex. `services/locations`, `services/routing`) :**
  * Chaque microservice embarque un middleware de sécurité qui vérifie indépendamment la signature cryptographique du JWT, l'émetteur (`iss`), l'audience (`aud`) et l'expiration (`exp`).
  * Le microservice extrait ensuite directement les claims `sub`, `role` et `tenant_id` pour appliquer ses propres règles d'autorisation (RBAC) et d'isolation par district sans effectuer d'appel réseau vers le service Auth.

### Stratégie de rotation et de révocation des jetons de rafraîchissement

Afin de contrer le vol de Refresh Tokens tout en maintenant une expérience utilisateur fluide, le système applique une **rotation stricte à usage unique avec détection de réutilisation (Refresh Token Rotation & Reuse Detection)** :

1. **Rotation à chaque appel de `/auth/refresh` :**
   * Lorsqu'un client présente un Refresh Token valide, le service Auth émet une nouvelle paire `(Access Token, nouveau Refresh Token)` rattachée à la même famille de session (`family_id`) et marque immédiatement l'ancien Refresh Token comme consommé.
2. **Détection de réutilisation (Compromission) :**
   * Si un Refresh Token déjà consommé est présenté à nouveau, le service Auth considère qu'un attaquant ou le client légitime tente de rejouer un jeton volé.
   * Le service Auth **révoque immédiatement l'intégralité de la famille de jetons (`family_id`)**, invalide la session en base/cache, journalise une alerte de sécurité critique et force la ré-authentification complète de l'utilisateur.
3. **Révocation explicite :**
   * Lors d'une déconnexion (`/auth/logout`), d'un changement de mot de passe ou d'une suspension de compte par un `admin`, la famille de jetons correspondante est immédiatement invalidée dans le stockage serveur.

### Gestion des clés et algorithme de signature cryptographique

* **Algorithme retenu : `RS256` (RSASSA-PKCS1-v1_5 utilisant SHA-256 avec clés RSA de 2048 bits minimum).**
  * Ce choix asymétrique garantit que la compromission d'un microservice consommateur (qui ne détient que la clé publique) ne permet jamais de signer de faux jetons.
* **Distribution dynamique via JWKS (JSON Web Key Set) :**
  * Le service Auth expose un endpoint public standardisé : `GET /.well-known/jwks.json`.
  * Chaque clé publique exposée inclut un identifiant unique **`kid`** (*Key ID*), qui est également inscrit dans l'en-tête (*header*) de chaque JWT émis.
  * Les microservices mettent en cache le JWKS en mémoire (TTL de 1 heure) et rafraîchissent automatiquement ce cache s'ils rencontrent un JWT portant un `kid` inconnu.
  * *Repli en environnement de développement/test :* Une variable d'environnement `AUTH_PUBLIC_KEY` (format PEM) peut être injectée pour les tests unitaires et d'intégration isolés.
* **Cycle de rotation des clés :**
  * Rotation planifiée des paires de clés RSA tous les 90 jours avec période de chevauchement de 24 heures (publication simultanée de l'ancienne et de la nouvelle clé publique dans le JWKS jusqu'à expiration des derniers Access Tokens signés avec l'ancienne clé).

## Conséquences

### Avantages en matière de sécurité

* **Résilience Zero-Trust :** Aucune confiance implicite accordée au réseau interne ; chaque microservice vérifie cryptographiquement l'identité, le rôle et le district (`tenant_id`) de l'appelant.
* **Haute disponibilité et faible latence :** La vérification locale via JWKS élimine tout appel réseau synchrone vers le service Auth lors des opérations métiers courantes.
* **Containment rapide des compromissions :** La durée de vie courte des Access Tokens (15 min) combinée à la révocation par famille de Refresh Tokens neutralise rapidement tout vol de session.
* **Rotation des clés sans interruption de service :** L'utilisation du champ `kid` et de l'endpoint JWKS permet de renouveler les clés cryptographiques à chaud.

### Compromis opérationnels et mesures d'atténuation

* **Fenêtre de latence sur la révocation des Access Tokens (jusqu'à 15 minutes) :** Un Access Token déjà émis reste techniquement valide jusqu'à son expiration `exp`, même après révocation du Refresh Token.
  * *Atténuation :* Durée de vie strictement limitée à 15 minutes pour les opérations standard, et publication d'une liste de révocation d'urgence (`jti` denylist distribuée via Redis Pub/Sub) uniquement pour les événements critiques (ex. révocation d'un compte `admin` ou `supervisor`).
* **Complexité accrue côté client sur la gestion de la concurrence :** Des requêtes parallèles déclenchées simultanément au moment de l'expiration de l'Access Token pourraient provoquer deux appels concurrents à `/auth/refresh` et déclencher par erreur la détection de réutilisation.
  * *Atténuation :* Implémentation d'un verrou (*mutex* / file d'attente de promesses) dans l'intercepteur HTTP des clients mobiles et web afin de mutualiser le rafraîchissement, complétée par une fenêtre de grâce serveur de 5 secondes pour les requêtes simultanées légitimes.
* **Gestion des secrets cryptographiques :** La clé privée RSA représente un actif critique.
  * *Atténuation :* Stockage exclusif dans un gestionnaire de secrets sécurisé (Vault / variables d'environnement chiffrées en production) sans jamais figurer dans le dépôt Git.

## Considérations de sécurité liées aux systèmes distribués

* **Synchronisation des horloges (Clock Skew) :** Dans un cluster distribué, de légers décalages d'horloge entre les nœuds exécutant le service Auth et les microservices consommateurs peuvent entraîner le rejet prématuré de jetons valides (`iat` dans le futur ou `exp` dépassé). Tous les conteneurs et hôtes doivent être synchronisés via **NTP**, et les validateurs JWT doivent appliquer une tolérance maximale de dérive (`clockTolerance`) de **30 secondes**.
* **Validation stricte de l'en-tête JWT (Prévention des attaques par substitution d'algorithme) :** Les bibliothèques de vérification côté microservices doivent explicitement restreindre la liste blanche des algorithmes acceptés à `["RS256"]` afin de bloquer toute tentative d'attaque par contournement (`alg: "none"`) ou confusion de clé symétrique/asymétrique (`HS256` utilisant la clé publique RSA comme secret HMAC).
* **Protection de l'endpoint JWKS :** Bien que public, l'endpoint `/.well-known/jwks.json` doit être servi exclusivement via **HTTPS (TLS 1.2+)** avec des en-têtes `Cache-Control` appropriés afin d'éviter toute attaque de type *Man-in-the-Middle* visant à substituer la clé publique légitime.
