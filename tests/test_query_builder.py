"""
Tests for QueryBuilder parameter generation and method chaining.
"""

from prestd.query import QueryBuilder


def test_select_columns():
    q = QueryBuilder().select("id", "name", "email")
    assert q.to_params() == {"_select": "id,name,email"}

    q2 = QueryBuilder().select(["id", "name"], "role, status")
    assert q2.to_params() == {"_select": "id,name,role,status"}


def test_equality_and_comparison_filters():
    q = (
        QueryBuilder()
        .filter_eq("status", "active")
        .filter_ne("role", "guest")
        .filter_gt("age", 18)
        .filter_gte("score", 75)
        .filter_lt("created_year", 2026)
        .filter_lte("price", 99.99)
    )
    params = q.to_params()
    assert params["status"] == "$eq.active"
    assert params["role"] == "$ne.guest"
    assert params["age"] == "$gt.18"
    assert params["score"] == "$gte.75"
    assert params["created_year"] == "$lt.2026"
    assert params["price"] == "$lte.99.99"


def test_pattern_matching_and_in_filters():
    q = (
        QueryBuilder()
        .filter_like("code", "ABC%")
        .filter_ilike("email", "%@company.com")
        .filter_in("category", ["electronics", "appliances"])
        .filter_nin("status", ["deleted", "banned"])
        .filter_fts("document_tsv", "postgresql")
    )
    params = q.to_params()
    assert params["code"] == "$like.ABC%"
    assert params["email"] == "$ilike.%@company.com"
    assert params["category"] == "$in.electronics,appliances"
    assert params["status"] == "$nin.deleted,banned"
    assert params["document_tsv"] == "$wfts.postgresql"


def test_null_and_is_filters():
    q = (
        QueryBuilder()
        .filter_null("deleted_at")
        .filter_not_null("confirmed_at")
        .filter_is("verified", "true")
    )
    params = q.to_params()
    assert params["deleted_at"] == "$null"
    assert params["confirmed_at"] == "$notnull"
    assert params["verified"] == "$is.true"


def test_or_and_group_by():
    q = (
        QueryBuilder()
        .filter_or("status=$eq.active", "role=$eq.admin")
        .group_by("department", "role")
    )
    params = q.to_params()
    assert params["_or"] == "status=$eq.active||role=$eq.admin"
    assert params["_groupby"] == "department,role"


def test_ordering_and_pagination():
    q = (
        QueryBuilder()
        .order_by("name")
        .order_by("created_at", descending=True)
        .order_by("-updated_at")
        .paginate(page=2, page_size=50)
    )
    params = q.to_params()
    assert params["_order"] == "name,-created_at,-updated_at"
    assert params["_page"] == "2"
    assert params["_page_size"] == "50"


def test_joins_and_count():
    q = (
        QueryBuilder()
        .count("id")
        .join("inner", "orders", "user_id", "eq", "users.id")
        .join("left", "profiles", "user_id", "eq", "users.id")
    )
    params = q.to_params()
    assert params["_count"] == "id"
    assert params["_join"] == [
        "inner:orders:user_id:eq:users.id",
        "left:profiles:user_id:eq:users.id",
    ]


def test_immutability():
    q1 = QueryBuilder().filter_eq("status", "active")
    q2 = q1.filter_gt("age", 25)
    assert "age" not in q1.to_params()
    assert "age" in q2.to_params()
    assert q1.to_params()["status"] == "$eq.active"


def test_query_string_serialization():
    q = QueryBuilder().filter_eq("name", "Alice").paginate(1, 10)
    qs = q.to_query_string()
    assert "name=%24eq.Alice" in qs
    assert "_page=1" in qs
    assert "_page_size=10" in qs
