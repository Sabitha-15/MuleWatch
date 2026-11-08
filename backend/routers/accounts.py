from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from datetime import date

from backend.database import get_connection


router = APIRouter(
    prefix="/api/accounts",
    tags=["Accounts"],
)




class CreateCustomerRequest(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    status: str = "ACTIVE"


class CreateAccountRequest(BaseModel):
    customer_id: int
    account_number: str
    account_type: str = "SAVINGS"
    balance: float = 0
    status: str = "ACTIVE"


class UpdateCustomerStatusRequest(BaseModel):
    new_status: str
    change_reason: str | None = None


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

                cursor.execute(count_query, parameters)
                total_accounts = cursor.fetchone()[0]

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


@router.post("/customers")
def create_customer(payload: CreateCustomerRequest):
    """Create a customer record that can be linked to one or more accounts."""
    full_name = payload.full_name.strip()
    status = payload.status.strip().upper()

    if not full_name:
        raise HTTPException(status_code=400, detail="Customer name is required.")

    if status not in {"ACTIVE", "INACTIVE", "BLOCKED"}:
        raise HTTPException(
            status_code=400,
            detail="Customer status must be ACTIVE, INACTIVE, or BLOCKED.",
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO customer (
                        full_name, email, phone, date_of_birth, status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING customer_id, full_name, email, phone,
                              date_of_birth, created_at, status;
                    """,
                    (
                        full_name,
                        payload.email.strip() if payload.email else None,
                        payload.phone.strip() if payload.phone else None,
                        payload.date_of_birth,
                        status,
                    ),
                )
                row = cursor.fetchone()
                columns = [description.name for description in cursor.description]
                customer = dict(zip(columns, row))
                return {
                    "status": "success",
                    "message": "Customer created successfully.",
                    "customer": customer,
                }
    except HTTPException:
        raise
    except Exception as error:
        if getattr(error, "sqlstate", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="A customer with this email or phone already exists.",
            ) from error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create customer: {error}",
        ) from error


@router.get("/customers")
def list_customers():
    """
    Return customers that can be associated with a new account.
    """

    query = """
        SELECT
            customer_id,
            full_name,
            email,
            status
        FROM customer
        ORDER BY customer_id ASC;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                customers = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                return {
                    "status": "success",
                    "customers": customers,
                }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve customers."
        ) from error


@router.post("")
def create_account(payload: CreateAccountRequest):
    """
    Create a new account for an existing customer.
    """

    account_number = payload.account_number.strip().upper()
    account_type = payload.account_type.strip().upper()
    status = payload.status.strip().upper()

    if not account_number:
        raise HTTPException(
            status_code=400,
            detail="Account number is required."
        )

    if account_type not in {"SAVINGS", "CURRENT"}:
        raise HTTPException(
            status_code=400,
            detail="Account type must be SAVINGS or CURRENT."
        )

    if status not in {"ACTIVE", "BLOCKED", "CLOSED"}:
        raise HTTPException(
            status_code=400,
            detail="Account status must be ACTIVE, BLOCKED, or CLOSED."
        )

    if payload.balance < 0:
        raise HTTPException(
            status_code=400,
            detail="Opening balance cannot be negative."
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT customer_id
                    FROM customer
                    WHERE customer_id = %s;
                    """,
                    (payload.customer_id,),
                )

                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Customer {payload.customer_id} not found."
                    )

                cursor.execute(
                    """
                    SELECT account_id
                    FROM account
                    WHERE account_number = %s;
                    """,
                    (account_number,),
                )

                if cursor.fetchone() is not None:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Account number {account_number} already exists."
                    )

                cursor.execute(
                    """
                    INSERT INTO account (
                        customer_id,
                        account_number,
                        account_type,
                        balance,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING
                        account_id,
                        account_number,
                        account_type,
                        balance,
                        opened_at,
                        status;
                    """,
                    (
                        payload.customer_id,
                        account_number,
                        account_type,
                        payload.balance,
                        status,
                    ),
                )

                row = cursor.fetchone()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                account = dict(zip(columns, row))

                return {
                    "status": "success",
                    "message": "Account created successfully.",
                    "account": account,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to create account."
        ) from error


@router.get("/customers/{customer_id}/summary")
def get_customer_summary(customer_id: int):
    """Return the Phase 2 customer summary using the PostgreSQL function."""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM fn_phase2_customer_summary(%s);",
                    (customer_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Customer {customer_id} was not found.",
                    )
                columns = [description.name for description in cursor.description]
                return dict(zip(columns, row))
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve customer summary: {error}",
        ) from error


@router.get("/customers/{customer_id}/audit")
def get_customer_audit(customer_id: int):
    """Return recent customer changes recorded by the audit trigger."""
    query = """
        SELECT
            audit_id,
            customer_id,
            action_type,
            old_data,
            new_data,
            changed_at,
            change_reason
        FROM customer_audit_log
        WHERE customer_id = %s
        ORDER BY audit_id DESC
        LIMIT 20;
    """
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (customer_id,))
                rows = cursor.fetchall()
                columns = [description.name for description in cursor.description]
                return {
                    "customer_id": customer_id,
                    "audit_records": [
                        dict(zip(columns, row)) for row in rows
                    ],
                }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve customer audit history: {error}",
        ) from error


@router.patch("/customers/{customer_id}/status")
def update_customer_status(
    customer_id: int,
    payload: UpdateCustomerStatusRequest,
):
    """Change customer status through the Phase 2 stored procedure."""
    new_status = payload.new_status.strip().upper()
    if new_status not in {"ACTIVE", "INACTIVE", "BLOCKED"}:
        raise HTTPException(
            status_code=400,
            detail="Customer status must be ACTIVE, INACTIVE, or BLOCKED.",
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CALL sp_phase2_update_customer_status(%s, %s, %s);
                    """,
                    (
                        customer_id,
                        new_status,
                        payload.change_reason.strip()
                        if payload.change_reason
                        else None,
                    ),
                )
        return {
            "status": "success",
            "message": "Customer status procedure executed successfully.",
            "customer_id": customer_id,
            "new_status": new_status,
        }
    except Exception as error:
        message = str(error)
        if "does not exist" in message:
            raise HTTPException(status_code=404, detail=message) from error
        if "Invalid customer status" in message:
            raise HTTPException(status_code=400, detail=message) from error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update customer status: {message}",
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
