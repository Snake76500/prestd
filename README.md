# prestd - Python Library for pREST (prestd) & Microservices

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-ready-009688.svg)](https://fastapi.tiangolo.com)
[![pREST](https://img.shields.io/badge/pREST-v2-orange.svg)](https://prestd.com)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-e92063.svg)](https://docs.pydantic.dev)

**`prestd`** est une librairie Python moderne, performante et typée conçue pour interagir en toute simplicité avec [**pREST (prestd)**](https://prestd.com), la passerelle RESTful haute performance pour PostgreSQL.

Cette librairie est spécialement optimisée pour être intégrée au sein de vos **microservices** (FastAPI, Flask, Celery, scripts et workers asynchrones) afin d'interroger, filtrer et manipuler leurs bases de données respectives sans écrire de code SQL répétitif.

---

## Sommaire

- [Fonctionnalités clés](#fonctionnalités-clés)
- [Installation](#installation)
- [Configuration 12-Factor pour Microservices](#configuration-12-factor-pour-microservices)
- [Guide d'utilisation](#guide-dutilisation)
  - [1. Client Asynchrone (`AsyncPrestClient`)](#1-client-asynchrone-asyncprestclient)
  - [2. Client Synchrone (`PrestClient`)](#2-client-synchrone-prestclient)
  - [3. Query Builder fluide et puissant](#3-query-builder-fluide-et-puissant)
  - [4. Opérations CRUD & Mapping Pydantic](#4-opérations-crud--mapping-pydantic)
  - [5. Support Multi-Bases et Multi-Schémas](#5-support-multi-bases-et-multi-schémas)
  - [6. Exécution de scripts SQL personnalisés (`/_QUERIES`)](#6-exécution-de-scripts-sql-personnalisés-_queries)
  - [7. Gestion des Erreurs et Exceptions](#7-gestion-des-erreurs-et-exceptions)
- [Intégration Clé-en-Main dans FastAPI](#intégration-clé-en-main-dans-fastapi)
- [Tests et Qualité](#tests-et-qualité)

---

## Fonctionnalités clés

- ⚡ **Double interface Asynchrone / Synchrone** : Support complet de `asyncio` (`AsyncPrestClient`) pour FastAPI/Starlette et interface synchrone (`PrestClient`) pour Flask, Celery, scripts et CLI.
- 🎯 **Conçu pour les microservices** :
  - Chargement automatique des paramètres depuis l'environnement (`PREST_BASE_URL`, `PREST_DEFAULT_DATABASE`, etc.).
  - Dépendances d'injection FastAPI prêtes à l'emploi (`Depends(get_async_prest_client)`).
  - Gestionnaires d'erreurs automatiques traduisant les exceptions pREST en codes HTTP appropriés (404, 409, 422, 500).
- 🔍 **Query Builder fluide et exhaustif** : Tous les opérateurs pREST pris en charge (`$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$like`, `$ilike`, `$in`, `$nin`, `$null`, `$notnull`, `$wfts`, `_order`, `_page`, `_page_size`, `_join`, `_or`, `_groupby`, `_select`).
- 🛡️ **Typage fort & Pydantic v2** : Sérialisation et désérialisation directe vers vos modèles métier (`table.find(model=UserModel)` -> `list[UserModel]`).
- 🏢 **Multi-Bases & Multi-Schémas** : Accédez facilement à différentes bases PostgreSQL depuis une même instance (`client.database("analytics").schema("public").table("events")`).
- 📜 **Requêtes SQL personnalisées** : Exécution directe des scripts SQL pREST (`client.sql.get("reports", "monthly")`).

---

## Installation

```bash
# Installation de base
pip install prestd

# Avec le support optionnel FastAPI
pip install "prestd[fastapi]"

# Avec toutes les dépendances de développement et tests
pip install "prestd[all]"
```

---

## Configuration 12-Factor pour Microservices

Pour configurer automatiquement la librairie dans vos microservices via des variables d'environnement ou un fichier `.env` :

```env
# URL du serveur pREST
PREST_BASE_URL=http://localhost:3000

# Base de données et schéma par défaut
PREST_DEFAULT_DATABASE=ecommerce_db
PREST_DEFAULT_SCHEMA=public

# Authentification (JWT / API Key)
PREST_API_KEY=votre_jeton_jwt_ou_cle_api
PREST_TOKEN_HEADER=Authorization
PREST_TOKEN_PREFIX=Bearer 

# Réseau et délais d'attente
PREST_TIMEOUT=30.0
PREST_MAX_RETRIES=3
```

Instanciez ensuite le client sans argument :

```python
from prestd import AsyncPrestClient, PrestClient

# Lit automatiquement les variables PREST_* de l'environnement
client = PrestClient.from_env()
async_client = AsyncPrestClient.from_env()
```

---

## Guide d'utilisation

### 1. Client Asynchrone (`AsyncPrestClient`)

Idéal pour les frameworks asynchrones modernes (FastAPI, Litestar, Tornado) :

```python
import asyncio
from prestd import AsyncPrestClient, QueryBuilder

async def main():
    async with AsyncPrestClient(
        base_url="http://localhost:3000",
        default_database="ecommerce_db"
    ) as client:
        # Vérification de santé
        health = await client.health()
        print("Status pREST :", health.status)

        # Accès à une table
        orders_table = client.table("orders")

        # Recherche avec filtres
        q = (
            QueryBuilder()
            .filter_eq("status", "shipped")
            .filter_gt("total_amount", 100.0)
            .order_by("created_at", descending=True)
            .paginate(page=1, page_size=10)
        )
        orders = await orders_table.find(q)
        print(f"Commandes trouvées : {len(orders)}")

asyncio.run(main())
```

### 2. Client Synchrone (`PrestClient`)

Idéal pour les scripts, CLI, workers Celery ou applications Flask :

```python
from prestd import PrestClient, QueryBuilder

with PrestClient(base_url="http://localhost:3000", default_database="ecommerce_db") as client:
    users_table = client.table("users")
    
    # Récupérer un utilisateur par son ID
    user = users_table.get(42)
    print(user)
```

### 3. Query Builder fluide et puissant

Le `QueryBuilder` permet de générer des requêtes pREST de façon lisible, sécurisée et immuable :

```python
from prestd import QueryBuilder

q = (
    QueryBuilder()
    # Sélection de colonnes spécifiques (_select=id,name,email)
    .select("id", "name", "email")
    
    # Filtres d'égalité et de comparaison
    .filter_eq("is_active", True)
    .filter_gt("age", 21)
    .filter_lte("risk_score", 5)
    
    # Recherche textuelle (LIKE / ILIKE) et Full-Text Search PostgreSQL
    .filter_ilike("name", "%alice%")
    .filter_fts("search_vector", "developer")
    
    # Listes et exclusion ($in, $nin)
    .filter_in("role", ["admin", "editor"])
    
    # Gestion des NULL ($null, $notnull)
    .filter_not_null("confirmed_at")
    
    # Condition logique OU (_or=cond1||cond2)
    .filter_or("status=$eq.active", "role=$eq.superadmin")
    
    # Tri & Pagination
    .order_by("role")
    .order_by("created_at", descending=True)
    .paginate(page=1, page_size=20)
    
    # Jointure de tables
    .join("inner", "profiles", "user_id", "eq", "users.id")
)
```

### 4. Opérations CRUD & Mapping Pydantic

Vous pouvez utiliser des dictionnaires classiques ou vos propres modèles Pydantic pour bénéficier de la validation et du typage statique :

```python
from pydantic import BaseModel, EmailStr
from prestd import AsyncPrestClient

class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str = "user"

async def manage_users(client: AsyncPrestClient):
    users = client.table("users")

    # 1. Insertion typée
    new_user = await users.insert(
        {"name": "Alice Dupont", "email": "alice@example.com", "role": "admin"},
        model=User
    )
    print("Utilisateur créé :", new_user.name, new_user.id)

    # 2. Recherche avec modèle Pydantic
    all_admins: list[User] = await users.find(
        users.query().filter_eq("role", "admin"),
        model=User
    )

    # 3. Récupération par clé primaire
    user: User | None = await users.get(new_user.id, model=User)

    # 4. Mise à jour
    await users.update_by_id(new_user.id, {"role": "superadmin"})

    # 5. Pagination avec métadonnées
    paged = await users.paginate(page=1, page_size=10, model=User)
    print(f"Total: {paged.total_count}, Pages: {paged.total_pages}, Suivant: {paged.has_next}")

    # 6. Suppression
    await users.delete_by_id(new_user.id)
```

### 5. Support Multi-Bases et Multi-Schémas

Si votre architecture comprend plusieurs bases PostgreSQL ou plusieurs schémas gérés par pREST :

```python
# Accéder directement à une autre base de données
billing_db = client.database("billing_db")
invoices = billing_db.schema("public").table("invoices")
all_invoices = invoices.find()

# Raccourci direct
analytics_events = client.table("events", database="analytics_db", schema="events_schema")
```

### 6. Exécution de scripts SQL personnalisés (`/_QUERIES`)

pREST permet d'exécuter des requêtes SQL pré-écrites stockées dans des dossiers SQL :

```python
# Exécute la requête stockée dans queries/reports/revenue.sql
monthly_revenue = await client.sql.get(
    folder="reports",
    script="revenue",
    params={"year": 2026, "month": 8}
)
```

### 7. Gestion des Erreurs et Exceptions

Toutes les exceptions héritent de `PrestError` :

| Exception | Code HTTP | Description |
|---|---|---|
| `PrestNotFoundError` | 404 | Table, schéma, base ou enregistrement introuvable |
| `PrestAuthenticationError` | 401 / 403 | Jeton invalide ou permissions insuffisantes |
| `PrestValidationError` | 400 / 422 | Syntaxe de filtre ou payload invalide |
| `PrestConflictError` | 409 | Violation de contrainte d'unicité |
| `PrestTimeoutError` | 504 / Timeout | Délai de requête expiré |
| `PrestConnectionError` | 503 / Network | Impossible de joindre le serveur pREST |
| `PrestServerError` | 500 | Erreur interne de PostgreSQL ou pREST |

---

## Intégration Clé-en-Main dans FastAPI

Voici comment construire un microservice FastAPI complet en quelques lignes :

```python
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel, EmailStr
from prestd import (
    AsyncPrestClient,
    PaginatedResponse,
    PrestNotFoundError,
    QueryBuilder,
    get_async_prest_client,
    setup_prest_exception_handlers,
)

class UserDTO(BaseModel):
    id: int
    username: str
    email: EmailStr

app = FastAPI(title="Users Microservice")

# 1. Enregistre les gestionnaires d'exceptions pREST (traduit PrestNotFoundError en 404, etc.)
setup_prest_exception_handlers(app)

# 2. Endpoint avec injection de dépendance et pagination
@app.get("/users", response_model=PaginatedResponse[UserDTO])
async def list_users(
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    client: AsyncPrestClient = Depends(get_async_prest_client),
):
    q = QueryBuilder()
    if search:
        q = q.filter_ilike("username", f"%{search}%")
    
    return await client.table("users").paginate(
        query=q,
        page=page,
        page_size=page_size,
        model=UserDTO,
    )

@app.get("/users/{user_id}", response_model=UserDTO)
async def get_user(
    user_id: int,
    client: AsyncPrestClient = Depends(get_async_prest_client),
):
    user = await client.table("users").get(user_id, model=UserDTO)
    if not user:
        raise PrestNotFoundError(f"Utilisateur {user_id} introuvable")
    return user
```

---

## Tests et Qualité

La librairie inclut une suite complète de tests unitaires et d'intégration mockés (sans dépendance externe requise) :

```bash
# Lancer les tests
pytest -v

# Vérifier le formatage et le linting
ruff check .
```

---

## Licence

Distribué sous licence **MIT**.
