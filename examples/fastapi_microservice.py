"""
Example FastAPI microservice querying PostgreSQL via prestd.

Run with:
    uvicorn examples.fastapi_microservice:app --reload --port 8000
"""

from typing import Any

from fastapi import Depends, FastAPI, Query, status
from pydantic import BaseModel, EmailStr, Field

from prestd import (
    AsyncPrestClient,
    PaginatedResponse,
    PrestNotFoundError,
    QueryBuilder,
    get_async_prest_client,
    setup_prest_exception_handlers,
)

# --- Pydantic Data Transfer Objects ---

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str | None = None
    role: str = "user"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None


class UserRead(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    role: str
    created_at: str | None = None


# --- FastAPI Application Setup ---

app = FastAPI(
    title="Users Microservice",
    description="Microservice demonstrating how to query and manipulate PostgreSQL through pREST using prestd.",
    version="1.0.0",
)

# Register automatic translation of PrestError into standard HTTP status codes (404, 409, 422, etc.)
setup_prest_exception_handlers(app)


# --- Endpoints ---

@app.get("/healthz", tags=["Health"])
async def health_check(client: AsyncPrestClient = Depends(get_async_prest_client)) -> dict[str, Any]:
    """Check connectivity to pREST and PostgreSQL."""
    h = await client.health()
    return {"status": h.status, "database_connected": h.database_connected}


@app.get("/users", response_model=PaginatedResponse[UserRead], tags=["Users"])
async def list_users(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    role: str | None = Query(default=None, description="Filter by user role"),
    search: str | None = Query(default=None, description="Search by username or full name"),
    client: AsyncPrestClient = Depends(get_async_prest_client),
) -> PaginatedResponse[UserRead]:
    """List users with filtering, searching, and pagination."""
    users_table = client.table("users")

    q = QueryBuilder()
    if role:
        q = q.filter_eq("role", role)
    if search:
        q = q.filter_ilike("username", f"%{search}%")

    q = q.order_by("id", descending=False)

    return await users_table.paginate(query=q, page=page, page_size=page_size, model=UserRead)


@app.get("/users/{user_id}", response_model=UserRead, tags=["Users"])
async def get_user(
    user_id: int,
    client: AsyncPrestClient = Depends(get_async_prest_client),
) -> UserRead:
    """Retrieve a single user by ID."""
    user = await client.table("users").get(user_id, model=UserRead)
    if not user:
        raise PrestNotFoundError(f"User with ID {user_id} not found")
    return user


@app.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED, tags=["Users"])
async def create_user(
    payload: UserCreate,
    client: AsyncPrestClient = Depends(get_async_prest_client),
) -> UserRead:
    """Create a new user."""
    return await client.table("users").insert(payload, model=UserRead)


@app.patch("/users/{user_id}", response_model=UserRead, tags=["Users"])
async def update_user(
    user_id: int,
    payload: UserUpdate,
    client: AsyncPrestClient = Depends(get_async_prest_client),
) -> UserRead:
    """Update user attributes."""
    users_table = client.table("users")
    existing = await users_table.get(user_id)
    if not existing:
        raise PrestNotFoundError(f"User with ID {user_id} not found")

    updated = await users_table.update_by_id(user_id, payload.model_dump(exclude_unset=True))
    return UserRead.model_validate(updated)


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
async def delete_user(
    user_id: int,
    client: AsyncPrestClient = Depends(get_async_prest_client),
) -> None:
    """Delete a user by ID."""
    users_table = client.table("users")
    existing = await users_table.get(user_id)
    if not existing:
        raise PrestNotFoundError(f"User with ID {user_id} not found")

    await users_table.delete_by_id(user_id)
