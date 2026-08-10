"""
Example of a synchronous worker or CLI script querying multiple tables/databases with prestd.
"""

from pydantic import BaseModel

from prestd import PrestClient, QueryBuilder


class Product(BaseModel):
    id: int
    name: str
    price: float
    category: str
    in_stock: bool


def main() -> None:
    # Initialize synchronous client from environment variables (or explicit params)
    client = PrestClient.from_env()

    print("Checking pREST server status...")
    health = client.health()
    print(f"pREST Status: {health.status}, DB Connected: {health.database_connected}")

    # Access a table in the default database
    products = client.table("products")

    # 1. Insert a sample product
    print("\n--- Inserting product ---")
    new_product = products.insert({
        "name": "Mechanical Keyboard",
        "price": 129.99,
        "category": "electronics",
        "in_stock": True,
    })
    print(f"Inserted: {new_product}")

    # 2. Querying with filters and ordering
    print("\n--- Finding active electronic products over 50 EUR ---")
    q = (
        QueryBuilder()
        .select("id", "name", "price")
        .filter_eq("category", "electronics")
        .filter_gt("price", 50.0)
        .filter_eq("in_stock", True)
        .order_by("price", descending=True)
    )

    filtered_products = products.find(q)
    for p in filtered_products:
        print(f" - {p.get('name')} : {p.get('price')} EUR")

    # 3. Pagination with total count
    print("\n--- Paginated retrieval ---")
    page_1 = products.paginate(query=QueryBuilder().filter_eq("in_stock", True), page=1, page_size=5)
    print(f"Total in stock: {page_1.total_count}, Page {page_1.page}/{page_1.total_pages}, Has next: {page_1.has_next}")

    # 4. Multi-database access (e.g. querying analytics_db while default is app_db)
    print("\n--- Cross-database query ---")
    analytics_db = client.database("analytics_db")
    events_table = analytics_db.table("user_events", schema_name="public")
    event_count = events_table.count()
    print(f"Total events in analytics_db: {event_count}")

    client.close()


if __name__ == "__main__":
    main()
