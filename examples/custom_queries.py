"""
Example executing pREST custom SQL scripts (/_QUERIES/{folder}/{script}).
"""

import asyncio

from pydantic import BaseModel

from prestd import AsyncPrestClient


class SalesReport(BaseModel):
    category: str
    total_sales: float
    order_count: int


async def main() -> None:
    async with AsyncPrestClient.from_env() as client:
        print("Executing custom SQL query: /_QUERIES/reports/monthly_sales...")

        # GET request with query params mapped to typed Pydantic model
        reports = await client.sql.get(
            folder="reports",
            script="monthly_sales",
            params={"year": 2026, "month": 8},
            model=SalesReport,
        )

        for report in reports:
            print(f"Category: {report.category} | Sales: ${report.total_sales:,.2f} | Orders: {report.order_count}")


if __name__ == "__main__":
    asyncio.run(main())
