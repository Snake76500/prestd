"""
Guide pratique : Interroger et manipuler PostgreSQL avec prestd SANS AUCUN SCRIPT SQL.

pREST expose automatiquement toutes vos tables PostgreSQL en API REST.
Vous n'avez JAMAIS besoin d'écrire ou de déployer des fichiers SQL pour :
- Faire des SELECT, filtres, tris, pagination
- Faire des INSERT (simples ou batch)
- Faire des UPDATE (par ID ou par filtre)
- Faire des DELETE
- Faire des COUNT
- Faire des JOINTURES entre tables
"""

import asyncio

from pydantic import BaseModel, EmailStr

from prestd import AsyncPrestClient, QueryBuilder


class UserDTO(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str = "user"
    age: int = 18


async def main() -> None:
    # Initialisation du client (lit les variables PREST_* ou prend des paramètres explicites)
    async with AsyncPrestClient(base_url="http://localhost:3000", default_database="postgres") as client:

        # =========================================================================
        # 1. SELECT simple (Tous les utilisateurs) -> SANS SCRIPT
        # =========================================================================
        # Équivalent SQL: SELECT * FROM users;
        all_users = await client.find("users")
        print(f"Total utilisateurs trouvés : {len(all_users)}")

        # =========================================================================
        # 2. SELECT avec filtres complexes, tri et pagination -> SANS SCRIPT
        # =========================================================================
        # Équivalent SQL:
        #   SELECT id, name, email, role
        #   FROM users
        #   WHERE role = 'admin' AND age >= 21 AND name ILIKE '%alice%'
        #   ORDER BY name ASC
        #   LIMIT 10 OFFSET 0;
        query = (
            QueryBuilder()
            .select("id", "name", "email", "role")
            .filter_eq("role", "admin")
            .filter_gte("age", 21)
            .filter_ilike("name", "%alice%")
            .order_by("name")
            .paginate(page=1, page_size=10)
        )

        # Mapping direct vers des objets Pydantic typés
        admins = await client.table("users").find(query, model=UserDTO)
        for admin in admins:
            print(f"Admin: {admin.name} ({admin.email})")

        # =========================================================================
        # 3. SELECT par clé primaire (GET /users?id=$eq.1) -> SANS SCRIPT
        # =========================================================================
        # Équivalent SQL: SELECT * FROM users WHERE id = 1 LIMIT 1;
        user_1 = await client.get("users", 1, model=UserDTO)
        if user_1:
            print(f"Utilisateur trouvé : {user_1.name}")

        # =========================================================================
        # 4. INSERT (Ajout d'une nouvelle ligne) -> SANS SCRIPT
        # =========================================================================
        # Équivalent SQL: INSERT INTO users (name, email, role, age) VALUES ('Bob', 'bob@test.com', 'user', 25) RETURNING *;
        new_user = await client.insert(
            "users",
            {"name": "Bob Martin", "email": "bob@test.com", "role": "user", "age": 25},
            model=UserDTO,
        )
        print(f"Nouvel utilisateur créé avec ID={new_user.id}")

        # =========================================================================
        # 5. UPDATE (Modification par ID) -> SANS SCRIPT
        # =========================================================================
        # Équivalent SQL: UPDATE users SET role = 'editor' WHERE id = 1;
        await client.update("users", new_user.id, {"role": "editor"})
        print("Rôle mis à jour avec succès !")

        # =========================================================================
        # 6. COUNT (Comptage de lignes) -> SANS SCRIPT
        # =========================================================================
        # Équivalent SQL: SELECT count(*) FROM users WHERE role = 'editor';
        total_editors = await client.count("users", QueryBuilder().filter_eq("role", "editor"))
        print(f"Nombre d'éditeurs : {total_editors}")

        # =========================================================================
        # 7. JOINTURES (INNER JOIN, LEFT JOIN) -> SANS SCRIPT
        # =========================================================================
        # Équivalent SQL:
        #   SELECT * FROM orders
        #   INNER JOIN users ON orders.user_id = users.id;
        join_query = (
            QueryBuilder()
            .join("inner", "users", "id", "eq", "orders.user_id")
            .filter_gt("total_amount", 50.0)
        )
        orders_with_users = await client.table("orders").find(join_query)
        print(f"Commandes jointes récupérées : {len(orders_with_users)}")

        # =========================================================================
        # 8. DELETE (Suppression) -> SANS SCRIPT
        # =========================================================================
        # Équivalent SQL: DELETE FROM users WHERE id = 1;
        await client.delete("users", new_user.id)
        print("Utilisateur supprimé !")


if __name__ == "__main__":
    asyncio.run(main())
