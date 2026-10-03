from fastapi import APIRouter, HTTPException, Query

from backend.database import get_connection


router = APIRouter(
    prefix="/api/accounts",
    tags=["Accounts"],
)


@router.get("")
def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
):
    """
    Retrieve a paginated list of accounts for investigation.

    Supports:
    - Search by account number
    - Search by customer name
    - Search by customer email
    - Account status filtering
    - Latest risk assessment information
    """

    offset = (page - 1) * page_size

    where_conditions = []
    parameters = []

    if search:
        where_conditions.append(
            """
            (
                a.account_number ILIKE %s
                OR c.full_name ILIKE %s
                OR c.email ILIKE %s
            )
            """
        )

        search_pattern = f"%{search}%"

        parameters.extend(
            [
                search_pattern,
                search_pattern,
                search_pattern,
            ]
        )

    if status:
        where_conditions.append("a.status = %s")
        parameters.append(status.upper())

    where_clause = ""

    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    count_query = f"""
        SELECT COUNT(*)
        FROM account a
        INNER JOIN customer c
            ON a.customer_id = c.customer_id
        {where_clause};
    """

    query = f"""
        SELECT
            a.account_id,
            a.account_number,
            a.account_type,
            a.balance,
            a.opened_at,
            a.status AS account_status,

            c.customer_id,
            c.full_name AS customer_name,
            c.email,
            c.phone,
            c.status AS customer_status,

            latest_risk.risk_score,
            latest_risk.risk_level,
            latest_risk.assessed_at AS risk_assessed_at

        FROM account a

        INNER JOIN customer c
            ON a.customer_id = c.customer_id

        LEFT JOIN LATERAL (
            SELECT
                ra.risk_score,
                ra.risk_level,
                ra.assessed_at
            FROM risk_assessment ra
            WHERE ra.account_id = a.account_id
            ORDER BY ra.assessed_at DESC
            LIMIT 1
        ) latest_risk
            ON TRUE

        {where_clause}

        ORDER BY a.account_id ASC

        LIMIT %s
        OFFSET %s;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # -----------------------------------------
                # TOTAL COUNT
                # -----------------------------------------

                cursor.execute(count_query, parameters)
                total_accounts = cursor.fetchone()[0]

                # -----------------------------------------
                # ACCOUNT DATA
                # -----------------------------------------

                query_parameters = parameters + [
                    page_size,
                    offset,
                ]

                cursor.execute(query, query_parameters)

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                accounts = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                total_pages = (
                    (total_accounts + page_size - 1) // page_size
                    if total_accounts > 0
                    else 0
                )

                return {
                    "status": "success",
                    "accounts": accounts,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_accounts": total_accounts,
                        "total_pages": total_pages,
                    },
                }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve accounts."
        ) from error


@router.get("/{account_id}")
def get_account(account_id: int):
    """
    Retrieve detailed account, customer, and latest risk information
    for investigation.
    """

    query = """
        SELECT
            a.account_id,
            a.account_number,
            a.account_type,
            a.balance,
            a.opened_at,
            a.status AS account_status,

            c.customer_id,
            c.full_name AS customer_name,
            c.email,
            c.phone,
            c.date_of_birth,
            c.status AS customer_status,
            c.created_at AS customer_created_at,

            latest_risk.risk_score,
            latest_risk.risk_level,
            latest_risk.model_version,
            latest_risk.assessed_at AS risk_assessed_at,
            latest_risk.reason AS risk_reason

        FROM account a

        INNER JOIN customer c
            ON a.customer_id = c.customer_id

        LEFT JOIN LATERAL (
            SELECT
                ra.risk_score,
                ra.risk_level,
                ra.model_version,
                ra.assessed_at,
                ra.reason
            FROM risk_assessment ra
            WHERE ra.account_id = a.account_id
            ORDER BY ra.assessed_at DESC
            LIMIT 1
        ) latest_risk
            ON TRUE

        WHERE a.account_id = %s;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (account_id,))
                row = cursor.fetchone()

                if row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Account {account_id} not found."
                    )

                columns = [
                    description.name
                    for description in cursor.description
                ]

                return dict(zip(columns, row))

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve account information."
        ) from error