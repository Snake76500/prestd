"""
Fluent Query builder for constructing pREST filtering, ordering, pagination, and join parameters.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Sequence
from copy import deepcopy
from typing import Any


class QueryBuilder:
    """
    Fluent and chainable query builder for pREST API queries.
    
    Examples:
        >>> q = (
        ...     QueryBuilder()
        ...     .select("id", "name", "email")
        ...     .filter_eq("status", "active")
        ...     .filter_gt("age", 21)
        ...     .filter_ilike("name", "%alice%")
        ...     .filter_in("role", ["admin", "editor"])
        ...     .order_by("created_at", descending=True)
        ...     .paginate(page=1, page_size=25)
        ... )
        >>> q.to_params()
        {
            '_select': 'id,name,email',
            'status': '$eq.active',
            'age': '$gt.21',
            'name': '$ilike.%alice%',
            'role': '$in.admin,editor',
            '_order': '-created_at',
            '_page': '1',
            '_page_size': '25'
        }
    """

    def __init__(self) -> None:
        self._select_fields: list[str] = []
        self._filters: list[tuple[str, str]] = []  # (field, expression)
        self._or_clauses: list[str] = []
        self._order_by: list[str] = []
        self._page: int | None = None
        self._page_size: int | None = None
        self._offset: int | None = None
        self._limit: int | None = None
        self._count_field: str | None = None
        self._joins: list[str] = []
        self._group_by: list[str] = []
        self._custom_params: dict[str, Any] = {}

    def _clone(self) -> QueryBuilder:
        """Create an immutable deep copy of this query builder for clean method chaining."""
        clone = QueryBuilder()
        clone._select_fields = list(self._select_fields)
        clone._filters = list(self._filters)
        clone._or_clauses = list(self._or_clauses)
        clone._order_by = list(self._order_by)
        clone._page = self._page
        clone._page_size = self._page_size
        clone._offset = self._offset
        clone._limit = self._limit
        clone._count_field = self._count_field
        clone._joins = list(self._joins)
        clone._group_by = list(self._group_by)
        clone._custom_params = deepcopy(self._custom_params)
        return clone

    def select(self, *fields: str | Sequence[str]) -> QueryBuilder:
        """Specify which columns to return (_select=col1,col2)."""
        new_q = self._clone()
        for f in fields:
            if isinstance(f, (list, tuple, set)):
                new_q._select_fields.extend(str(item).strip() for item in f if str(item).strip())
            elif isinstance(f, str) and "," in f:
                new_q._select_fields.extend(part.strip() for part in f.split(",") if part.strip())
            elif isinstance(f, str) and f.strip():
                new_q._select_fields.append(f.strip())
        return new_q

    def filter(self, field: str, operator: str | None = None, value: Any = None) -> QueryBuilder:
        """
        Generic filter method.
        
        Args:
            field: Column name.
            operator: Optional operator (e.g. '$eq', '$gt', '$gte', '$lt', '$lte', '$like', '$ilike', '$in', '$ne').
            value: Filter value. If operator is None, default equality is used.
        """
        new_q = self._clone()
        if operator is None:
            new_q._filters.append((field, str(value)))
        else:
            op = operator if operator.startswith("$") else f"${operator}"
            if value is None:
                new_q._filters.append((field, op))
            else:
                new_q._filters.append((field, f"{op}.{value}"))
        return new_q

    def filter_eq(self, field: str, value: Any) -> QueryBuilder:
        """Filter by equality (field=$eq.value)."""
        return self.filter(field, "$eq", value)

    def filter_ne(self, field: str, value: Any) -> QueryBuilder:
        """Filter by inequality (field=$ne.value)."""
        return self.filter(field, "$ne", value)

    def filter_gt(self, field: str, value: Any) -> QueryBuilder:
        """Filter by greater than (field=$gt.value)."""
        return self.filter(field, "$gt", value)

    def filter_gte(self, field: str, value: Any) -> QueryBuilder:
        """Filter by greater than or equal (field=$gte.value)."""
        return self.filter(field, "$gte", value)

    def filter_lt(self, field: str, value: Any) -> QueryBuilder:
        """Filter by less than (field=$lt.value)."""
        return self.filter(field, "$lt", value)

    def filter_lte(self, field: str, value: Any) -> QueryBuilder:
        """Filter by less than or equal (field=$lte.value)."""
        return self.filter(field, "$lte", value)

    def filter_like(self, field: str, pattern: str) -> QueryBuilder:
        """Case-sensitive pattern matching (field=$like.pattern)."""
        return self.filter(field, "$like", pattern)

    def filter_ilike(self, field: str, pattern: str) -> QueryBuilder:
        """Case-insensitive pattern matching (field=$ilike.pattern)."""
        return self.filter(field, "$ilike", pattern)

    def filter_in(self, field: str, values: Sequence[Any]) -> QueryBuilder:
        """Filter by inclusion in list (field=$in.val1,val2)."""
        joined = ",".join(str(v) for v in values)
        return self.filter(field, "$in", joined)

    def filter_nin(self, field: str, values: Sequence[Any]) -> QueryBuilder:
        """Filter by exclusion from list (field=$nin.val1,val2)."""
        joined = ",".join(str(v) for v in values)
        return self.filter(field, "$nin", joined)

    def filter_null(self, field: str) -> QueryBuilder:
        """Filter by IS NULL (field=$null)."""
        return self.filter(field, "$null", None)

    def filter_not_null(self, field: str) -> QueryBuilder:
        """Filter by IS NOT NULL (field=$notnull)."""
        return self.filter(field, "$notnull", None)

    def filter_is(self, field: str, value: str = "null") -> QueryBuilder:
        """Filter using IS operator (field=$is.null, field=$is.true, etc.)."""
        return self.filter(field, f"$is.{value}", None)

    def filter_fts(self, field: str, term: str) -> QueryBuilder:
        """Full-Text Search filtering using PostgreSQL tsvector (field=$wfts.term)."""
        return self.filter(field, "$wfts", term)

    def filter_or(self, *clauses: str) -> QueryBuilder:
        """
        Add logical OR conditions (_or=cond1||cond2).
        
        Example:
            >>> q.filter_or("status=$eq.active", "role=$eq.admin")
        """
        new_q = self._clone()
        for clause in clauses:
            if clause and clause.strip():
                new_q._or_clauses.append(clause.strip())
        return new_q

    def order_by(self, field: str, descending: bool = False) -> QueryBuilder:
        """
        Add an ordering field.
        
        Args:
            field: Field name. If prefixed with '-', descending is automatically enabled.
            descending: If True, prefixes field with '-'.
        """
        new_q = self._clone()
        clean_field = field.strip()
        if clean_field.startswith("-"):
            new_q._order_by.append(clean_field)
        elif descending:
            new_q._order_by.append(f"-{clean_field}")
        else:
            new_q._order_by.append(clean_field)
        return new_q

    def paginate(self, page: int = 1, page_size: int = 10) -> QueryBuilder:
        """Set pagination page and page_size."""
        new_q = self._clone()
        new_q._page = max(1, page)
        new_q._page_size = max(1, page_size)
        return new_q

    def limit(self, limit: int) -> QueryBuilder:
        """Set limit for query results."""
        new_q = self._clone()
        new_q._limit = max(0, limit)
        return new_q

    def offset(self, offset: int) -> QueryBuilder:
        """Set offset for query results."""
        new_q = self._clone()
        new_q._offset = max(0, offset)
        return new_q

    def count(self, field: str = "*") -> QueryBuilder:
        """Request record count (_count=field)."""
        new_q = self._clone()
        new_q._count_field = field
        return new_q

    def group_by(self, *fields: str) -> QueryBuilder:
        """Specify group by columns (_groupby=col1,col2)."""
        new_q = self._clone()
        for f in fields:
            if f and f.strip():
                new_q._group_by.append(f.strip())
        return new_q

    def join(
        self,
        join_type: str,
        target_table: str,
        target_field: str,
        operator: str,
        source_field: str,
    ) -> QueryBuilder:
        """
        Add a table join.
        
        Format: _join={TYPE}:{TABLE}:{FIELD}:{OPERATOR}:{TABLE.FIELD}
        Example:
            >>> q.join("inner", "orders", "user_id", "eq", "users.id")
            # Result: _join=inner:orders:user_id:eq:users.id
        """
        new_q = self._clone()
        join_clause = f"{join_type}:{target_table}:{target_field}:{operator}:{source_field}"
        new_q._joins.append(join_clause)
        return new_q

    def param(self, key: str, value: Any) -> QueryBuilder:
        """Add an arbitrary query parameter."""
        new_q = self._clone()
        new_q._custom_params[key] = value
        return new_q

    def to_params(self) -> dict[str, Any]:
        """Convert query builder state into a dictionary of query parameters for HTTP requests."""
        params: dict[str, Any] = {}

        if self._select_fields:
            params["_select"] = ",".join(self._select_fields)

        for field, expr in self._filters:
            if field in params:
                existing = params[field]
                if isinstance(existing, list):
                    existing.append(expr)
                else:
                    params[field] = [existing, expr]
            else:
                params[field] = expr

        if self._or_clauses:
            params["_or"] = "||".join(self._or_clauses)

        if self._order_by:
            params["_order"] = ",".join(self._order_by)

        if self._page is not None:
            params["_page"] = str(self._page)
        if self._page_size is not None:
            params["_page_size"] = str(self._page_size)

        if self._limit is not None:
            params["_limit"] = str(self._limit)
        if self._offset is not None:
            params["_offset"] = str(self._offset)

        if self._count_field is not None:
            params["_count"] = self._count_field

        if self._group_by:
            params["_groupby"] = ",".join(self._group_by)

        if self._joins:
            if len(self._joins) == 1:
                params["_join"] = self._joins[0]
            else:
                params["_join"] = self._joins

        for k, v in self._custom_params.items():
            params[k] = v

        return params

    def to_query_string(self) -> str:
        """Serialize parameters into a URL query string without leading '?'."""
        params = self.to_params()
        return urllib.parse.urlencode(params, doseq=True)

    def __repr__(self) -> str:
        return f"<QueryBuilder params={self.to_params()}>"
