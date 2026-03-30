# Rapport du Mini Projet Cloud

## Application de Gestion de Tâches — Architecture Microservices avec Docker

---

## 1. Architecture Générale

Ce projet implémente une **application web de gestion de tâches** (CRUD) déployée dans une architecture microservices conteneurisée avec Docker Compose. L'architecture suit le modèle **3-tiers** :

- **Couche Présentation** : Nginx agit comme reverse proxy et point d'entrée unique, gérant le SSL/TLS (HTTPS sur le port 443) et le routage HTTP (port 5000).
- **Couche Application** : Une API REST Flask (Python) expose les endpoints `/tasks` (GET, POST, DELETE) pour la gestion des tâches.
- **Couche Données** : PostgreSQL 14 assure la persistance des données, avec Redis 7 comme couche de cache pour optimiser les performances de lecture.

Un service de **monitoring** (cAdvisor) est ajouté pour surveiller les ressources des conteneurs en temps réel. Une pipeline **CI/CD** via GitHub Actions automatise le build et le push de l'image Docker vers Docker Hub.

### Schéma des flux :

```
Client → Nginx (443/5000) → Flask App (:5000) → PostgreSQL (:5432)
                                              → Redis (:6379)
cAdvisor (:8080) → Monitoring des conteneurs
GitHub Actions → Build & Push Docker Hub
```

---

## 2. Conteneurs

Le projet comprend **5 conteneurs** orchestrés par Docker Compose :

| Conteneur    | Image                                               | Rôle                             | Port exposé   |
| ------------ | --------------------------------------------------- | -------------------------------- | ------------- |
| **app1**     | Build depuis `./app1/Dockerfile` (python:3.11-slim) | API REST Flask — CRUD des tâches | Interne :5000 |
| **db**       | `postgres:14`                                       | Base de données relationnelle    | Interne :5432 |
| **redis**    | `redis:7`                                           | Cache en mémoire (TTL 60s)       | 6379          |
| **nginx**    | `nginx:latest`                                      | Reverse proxy, terminaison SSL   | 443, 5000     |
| **cadvisor** | `gcr.io/cadvisor/cadvisor:v0.47.0`                  | Monitoring des conteneurs        | 8080          |

### Détails de l'application Flask (app1)

L'application est construite à partir d'un `Dockerfile` personnalisé :

- Base : `python:3.11-slim` (image légère)
- Dépendances : Flask, Flask-SQLAlchemy, psycopg2-binary, redis
- Stratégie de résilience : retry automatique (10 tentatives) pour la connexion à la base de données au démarrage
- Cache Redis : les résultats GET sont mis en cache pendant 60 secondes, le cache est invalidé lors d'un POST ou DELETE

### Dépendances entre conteneurs

Les dépendances sont gérées via `depends_on` :

- **app1** dépend de `db` et `redis` (la base et le cache doivent démarrer avant l'app)
- **nginx** dépend de `app1` (le proxy ne démarre qu'une fois l'app prête)

---

## 3. Réseau

Docker Compose crée automatiquement un **réseau bridge par défaut** nommé `mini-projet-cloud_default`. Tous les conteneurs sont connectés à ce réseau et peuvent communiquer entre eux via leurs **noms de service** comme noms DNS :

| Communication    | Adresse DNS interne |
| ---------------- | ------------------- |
| App → PostgreSQL | `db:5432`           |
| App → Redis      | `redis:6379`        |
| Nginx → App      | `app1:5000`         |

### Ports exposés vers l'hôte

| Port hôte | Service       | Protocole                          |
| --------- | ------------- | ---------------------------------- |
| **443**   | Nginx (HTTPS) | TLS/SSL avec certificat auto-signé |
| **5000**  | Nginx (HTTP)  | HTTP proxifié vers Flask           |
| **6379**  | Redis         | TCP                                |
| **8080**  | cAdvisor      | HTTP (interface web monitoring)    |

### Sécurité réseau

- Nginx assure la **terminaison SSL** avec un certificat auto-signé (`selfsigned.crt` / `selfsigned.key`)
- Les en-têtes `X-Real-IP` et `Host` sont transmis par le proxy pour préserver l'IP client
- L'application Flask n'est **pas directement exposée** — seul Nginx est accessible de l'extérieur
- La communication inter-conteneurs reste sur le réseau Docker interne (non exposée)

---

## 4. Volumes

Le projet utilise **deux types de volumes** pour la persistance et la configuration :

### Volume nommé (Docker-managed)

| Volume    | Monté sur                  | Conteneur | Usage                              |
| --------- | -------------------------- | --------- | ---------------------------------- |
| `db-data` | `/var/lib/postgresql/data` | db        | Persistance des données PostgreSQL |

Ce volume nommé garantit que les données de la base de données **survivent aux redémarrages et suppressions** de conteneurs. Il est géré par Docker et stocké dans `/var/lib/docker/volumes/`.

### Bind Mounts (fichiers de l'hôte)

| Source (hôte)      | Destination (conteneur) | Conteneur | Mode | Usage                  |
| ------------------ | ----------------------- | --------- | ---- | ---------------------- |
| `./nginx.conf`     | `/etc/nginx/nginx.conf` | nginx     | rw   | Configuration Nginx    |
| `./certs/`         | `/etc/ssl/certs/`       | nginx     | rw   | Certificats SSL        |
| `/var/run`         | `/var/run`              | cadvisor  | ro   | Accès au daemon Docker |
| `/sys`             | `/sys`                  | cadvisor  | ro   | Métriques système      |
| `/var/lib/docker/` | `/var/lib/docker/`      | cadvisor  | ro   | Infos conteneurs       |

Les bind mounts de cAdvisor sont montés en **lecture seule** (`ro`) pour des raisons de sécurité — cAdvisor ne doit que lire les métriques, pas modifier le système.

---

## 5. Extensions et CI/CD

### Monitoring avec cAdvisor

**cAdvisor** (Container Advisor) est un outil open-source de Google qui fournit :

- Utilisation CPU, mémoire, réseau et disque par conteneur
- Interface web accessible sur `http://localhost:8080`
- Métriques en temps réel pour diagnostiquer les problèmes de performance

Le conteneur cAdvisor est exécuté en mode **privileged** pour pouvoir accéder aux informations du système hôte.

### Pipeline CI/CD — GitHub Actions

Le fichier `.github/workflows/docker.yml` définit une pipeline automatisée :

1. **Déclencheur** : Push sur la branche `main`
2. **Étapes** :
   - Checkout du code source
   - Build de l'image Docker : `docker build -t eyamodokerhub/flask-app1 ./app1`
   - Connexion à Docker Hub via secrets GitHub
   - Push de l'image : `docker push eyamodokerhub/flask-app1`

Les secrets `DOCKER_USERNAME` et `DOCKER_PASSWORD` sont configurés dans les paramètres du dépôt GitHub pour sécuriser l'authentification.

### Cache Redis

Redis est utilisé comme **extension de performance** :

- Les requêtes GET `/tasks` sont mises en cache avec un **TTL de 60 secondes**
- Lors d'un POST ou DELETE, le cache est **invalidé** (`cache.delete('tasks')`)
- Cela réduit significativement la charge sur PostgreSQL pour les lectures fréquentes

### Reverse Proxy Nginx avec SSL

Nginx sert d'extension de sécurité et de performance :

- **Terminaison SSL** : le trafic HTTPS est déchiffré par Nginx, le trafic interne reste en HTTP
- **Load balancing** : l'upstream `app_servers` permet de scaler horizontalement l'application
- **Sécurité** : l'application Flask n'est jamais exposée directement

---

## Commandes de Déploiement

```bash
# Générer les certificats SSL auto-signés
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/selfsigned.key -out certs/selfsigned.crt

# Lancer tous les services
docker-compose up -d --build

# Vérifier l'état des conteneurs
docker-compose ps

# Tester l'API
curl -k https://localhost/tasks
curl -X POST https://localhost/tasks -H "Content-Type: application/json" -d '{"title": "Ma tâche"}'

# Accéder au monitoring
# http://localhost:8080 (cAdvisor)

# Arrêter les services
docker-compose down

# Supprimer les volumes (attention: perte de données)
docker-compose down -v
```

---

_Projet réalisé dans le cadre du mini projet Cloud — Architecture conteneurisée avec Docker Compose_
