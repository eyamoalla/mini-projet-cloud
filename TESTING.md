# Guide de Tests — Mini Projet Cloud

Ce fichier contient toutes les étapes pour tester chaque composant du projet.

> **Note :** Sur Windows PowerShell, utilisez `\"` pour échapper les guillemets dans les commandes curl.

---

## Étape 0 — Prérequis

```bash
# Vérifier que Docker est installé et fonctionne
docker --version
docker-compose --version
```

---

## Étape 1 — Générer les certificats SSL

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/selfsigned.key -out certs/selfsigned.crt
```

Vérifier que les fichiers existent :

```bash
ls certs/
# Attendu : selfsigned.crt  selfsigned.key
```

---

## Étape 2 — Lancer tous les services

```bash
docker-compose up -d --build
```

Vérifier que tous les conteneurs tournent :

```bash
docker-compose ps
```

**Résultat attendu :** 5 services `running` — app1, db, redis, nginx, cadvisor.

---

## Étape 3 — Tester la base de données (PostgreSQL)

```bash
# Se connecter à la base de données
docker-compose exec db psql -U admin -d tasks

# Dans le shell psql, vérifier que la table existe
\dt
# Attendu : la table "task" apparaît

# Quitter psql
\q
```

---

## Étape 4 — Tester Redis

```bash
# Se connecter au CLI Redis
docker-compose exec redis redis-cli

# Tester la connectivité
PING
# Attendu : PONG

# Vérifier qu'il n'y a pas encore de cache (avant un GET /tasks)
GET tasks
# Attendu : (nil)

# Quitter
EXIT
```

---

## Étape 5 — Tester l'API Flask (via Nginx HTTPS — port 443)

### 5.1 — GET /tasks (liste vide)

```bash
curl -k https://localhost/tasks
```

**Attendu :** `[]`

### 5.2 — POST /tasks (créer une tâche)

```bash
curl -k -X POST https://localhost/tasks -H "Content-Type: application/json" -d "{\"title\": \"Tache 1\"}"
```

**Attendu :** `{"id": 1, "title": "Tache 1"}` avec code HTTP 201.

### 5.3 — POST /tasks (créer une deuxième tâche)

```bash
curl -k -X POST https://localhost/tasks -H "Content-Type: application/json" -d "{\"title\": \"Tache 2\"}"
```

**Attendu :** `{"id": 2, "title": "Tache 2"}`

### 5.4 — GET /tasks (vérifier les tâches créées)

```bash
curl -k https://localhost/tasks
```

**Attendu :** `[{"id": 1, "title": "Tache 1"}, {"id": 2, "title": "Tache 2"}]`

### 5.5 — DELETE /tasks/1 (supprimer une tâche)

```bash
curl -k -X DELETE https://localhost/tasks/1
```

**Attendu :** Réponse vide avec code HTTP 204.

### 5.6 — DELETE tâche inexistante

```bash
curl -k -X DELETE https://localhost/tasks/999
```

**Attendu :** Réponse vide avec code HTTP 404.

### 5.7 — GET /tasks (vérifier la suppression)

```bash
curl -k https://localhost/tasks
```

**Attendu :** `[{"id": 2, "title": "Tache 2"}]`

### 5.8 — POST /tasks sans titre (validation)

```bash
curl -k -X POST https://localhost/tasks -H "Content-Type: application/json" -d "{}"
```

**Attendu :** `{"error": "title is required"}` avec code HTTP 400.

---

## Étape 6 — Tester l'accès HTTP via le port 5000 (Nginx → Flask)

```bash
curl -k http://localhost:5000/tasks
```

**Attendu :** La même liste de tâches que via HTTPS.

---

## Étape 7 — Tester le cache Redis

```bash
# 1. Faire un GET pour remplir le cache
curl -k https://localhost/tasks

# 2. Vérifier dans les logs Flask que la requête venait de la DB
docker-compose logs app1 | tail -5
# Attendu : "FROM DB" ou "FROM CACHE"

# 3. Faire un deuxième GET immédiatement
curl -k https://localhost/tasks

# 4. Vérifier dans les logs que cette fois c'est le cache
docker-compose logs app1 | tail -5
# Attendu : "FROM CACHE"

# 5. Vérifier directement dans Redis
docker-compose exec redis redis-cli GET tasks
# Attendu : la liste des tâches en JSON

# 6. Créer une tâche (le cache doit être invalidé)
curl -k -X POST https://localhost/tasks -H "Content-Type: application/json" -d "{\"title\": \"Tache cache\"}"

# 7. Vérifier que le cache a été supprimé
docker-compose exec redis redis-cli GET tasks
# Attendu : (nil) — le cache a été invalidé
```

---

## Étape 8 — Tester le reverse proxy Nginx + SSL

```bash
# Vérifier le certificat SSL
curl -k -v https://localhost/tasks 2>&1 | findstr "SSL\|subject\|issuer"

# Vérifier que Nginx redirige bien vers Flask
docker-compose logs nginx | tail -10
```

---

## Étape 9 — Tester le monitoring cAdvisor

Ouvrir dans le navigateur :

```
http://localhost:8080
```

**Attendu :** Interface cAdvisor affichant les métriques de tous les conteneurs (CPU, mémoire, réseau, disque).

Ou via curl :

```bash
curl -s http://localhost:8080/api/v1.0/containers | findstr "name"
```

---

## Étape 10 — Tester la persistance des données (volume PostgreSQL)

```bash
# 1. Créer une tâche
curl -k -X POST https://localhost/tasks -H "Content-Type: application/json" -d "{\"title\": \"Persistance\"}"

# 2. Arrêter et relancer les services
docker-compose down
docker-compose up -d

# 3. Vérifier que la tâche existe toujours
curl -k https://localhost/tasks
# Attendu : la tâche "Persistance" est toujours là
```

> **Important :** `docker-compose down` préserve les volumes. Utilisez `docker-compose down -v` uniquement si vous voulez tout supprimer.

---

## Étape 11 — Tester les logs de chaque service

```bash
docker-compose logs app1      # Logs Flask
docker-compose logs db         # Logs PostgreSQL
docker-compose logs redis      # Logs Redis
docker-compose logs nginx      # Logs Nginx
docker-compose logs cadvisor   # Logs cAdvisor
```

---

## Étape 12 — Nettoyage complet

```bash
# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes (reset complet)
docker-compose down -v
```

---

## Résumé des tests

| #   | Composant          | Test                   | Commande principale                             |
| --- | ------------------ | ---------------------- | ----------------------------------------------- |
| 1   | SSL/Certificats    | Fichiers générés       | `ls certs/`                                     |
| 2   | Docker Compose     | Tous les services up   | `docker-compose ps`                             |
| 3   | PostgreSQL         | Table créée            | `docker-compose exec db psql -U admin -d tasks` |
| 4   | Redis              | Connectivité           | `docker-compose exec redis redis-cli PING`      |
| 5   | API GET            | Liste des tâches       | `curl -k https://localhost/tasks`               |
| 6   | API POST           | Créer une tâche        | `curl -k -X POST ... -d '{"title":"..."}'`      |
| 7   | API DELETE         | Supprimer une tâche    | `curl -k -X DELETE https://localhost/tasks/1`   |
| 8   | Validation         | POST sans titre        | `curl -k -X POST ... -d '{}'`                   |
| 9   | Nginx HTTP         | Accès port 5000        | `curl http://localhost:5000/tasks`              |
| 10  | Cache Redis        | FROM DB → FROM CACHE   | `docker-compose logs app1`                      |
| 11  | Cache invalidation | POST supprime le cache | `redis-cli GET tasks` → nil après POST          |
| 12  | cAdvisor           | Interface monitoring   | `http://localhost:8080`                         |
| 13  | Persistance        | Données après restart  | `docker-compose down` puis `up`                 |
