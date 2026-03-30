# Mini Projet Cloud — Gestion de Tâches

Application de gestion de tâches (CRUD) déployée avec Docker Compose dans une architecture microservices.

## Architecture

| Service      | Technologie         | Rôle                  |
| ------------ | ------------------- | --------------------- |
| **app1**     | Flask (Python 3.11) | API REST `/tasks`     |
| **db**       | PostgreSQL 14       | Base de données       |
| **redis**    | Redis 7             | Cache (TTL 60s)       |
| **nginx**    | Nginx               | Reverse proxy + SSL   |
| **cadvisor** | cAdvisor v0.47      | Monitoring conteneurs |

## Prérequis

- Docker & Docker Compose
- OpenSSL (pour les certificats)

## Démarrage rapide

```bash
# 1. Générer les certificats SSL
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/selfsigned.key -out certs/selfsigned.crt

# 2. Lancer les services
docker-compose up -d --build

# 3. Tester
curl -k https://localhost/tasks
curl -X POST https://localhost/tasks -H "Content-Type: application/json" -d '{"title": "Ma tâche"}'
curl -X DELETE https://localhost/tasks/1
```

## Endpoints API

| Méthode | URL           | Description                        |
| ------- | ------------- | ---------------------------------- |
| GET     | `/tasks`      | Liste toutes les tâches            |
| POST    | `/tasks`      | Créer une tâche `{"title": "..."}` |
| DELETE  | `/tasks/<id>` | Supprimer une tâche                |

## Ports

| Port | Service               |
| ---- | --------------------- |
| 443  | HTTPS (Nginx)         |
| 5000 | HTTP (Nginx → Flask)  |
| 8080 | cAdvisor (Monitoring) |

## CI/CD

Pipeline GitHub Actions : build et push automatique de l'image Docker vers Docker Hub sur chaque push sur `main`.


