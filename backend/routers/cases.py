from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.database import get_connection


router = APIRouter(
    prefix="/api/cases",
    tags=["Fraud Cases"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class OpenCaseRequest(BaseModel):
    alert_id: int = Field(..., gt=0)
    investigator_id: int = Field(..., gt=0)
    case_title: str = Field(..., min_length=3, max_length=200)
    case_description: str | None = None
    priority: str = Field(default="MEDIUM")


class CloseCaseRequest(BaseModel):
    investigator_id: int = Field(..., gt=0)
    closure_reason: str = Field(..., min_length=3)

class AddCaseNoteRequest(BaseModel):
    investigator_id: int = Field(..., gt=0)
    note_text: str = Field(..., min_length=1, max_length=5000)
# ============================================================
# GET ALL CASES
# ============================================================

@router.get("")
def get_cases(
    status: str | None = Query(
        default=None,
        description="Filter by case status: OPEN, UNDER_REVIEW, ESCALATED, CLOSED",
    ),
    priority: str | None = Query(
        default=None,
        description="Filter by priority: LOW, MEDIUM, HIGH, CRITICAL",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of cases per page",
    ),
):
    """
    Retrieve fraud cases with optional filtering and pagination.
    """

    offset = (page - 1) * page_size

    where_conditions = []
    parameters = []

    if status:
        where_conditions.append("fc.case_status = %s")
        parameters.append(status.upper())

    if priority:
        where_conditions.append("fc.priority = %s")
        parameters.append(priority.upper())

    where_clause = ""

    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    count_query = f"""
        SELECT COUNT(*)
        FROM fraud_case fc
        {where_clause};
    """

    cases_query = f"""
        SELECT
            fc.case_id,
            fc.alert_id,
            fc.account_id,
            a.account_number,

            fc.investigator_id,
            i.full_name AS investigator_name,

            fc.case_title,
            fc.case_description,
            fc.case_status,
            fc.priority,

            fc.opened_at,
            fc.closed_at,

            COUNT(ct.transaction_id) AS linked_transaction_count,
            COALESCE(SUM(t.amount), 0) AS suspicious_amount

        FROM fraud_case fc

        INNER JOIN account a
            ON fc.account_id = a.account_id

        LEFT JOIN investigator i
            ON fc.investigator_id = i.investigator_id

        LEFT JOIN case_transaction ct
            ON fc.case_id = ct.case_id

        LEFT JOIN transaction t
            ON ct.transaction_id = t.transaction_id

        {where_clause}

        GROUP BY
            fc.case_id,
            fc.alert_id,
            fc.account_id,
            a.account_number,
            fc.investigator_id,
            i.full_name,
            fc.case_title,
            fc.case_description,
            fc.case_status,
            fc.priority,
            fc.opened_at,
            fc.closed_at

        ORDER BY
            CASE
                WHEN fc.case_status = 'OPEN' THEN 1
                WHEN fc.case_status = 'UNDER_REVIEW' THEN 2
                WHEN fc.case_status = 'ESCALATED' THEN 3
                ELSE 4
            END,
            fc.opened_at DESC

        LIMIT %s
        OFFSET %s;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    count_query,
                    parameters,
                )

                total_cases = cursor.fetchone()[0]

                cursor.execute(
                    cases_query,
                    parameters + [page_size, offset],
                )

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                cases = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                total_pages = (
                    (total_cases + page_size - 1) // page_size
                    if total_cases > 0
                    else 0
                )

                return {
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_cases": total_cases,
                        "total_pages": total_pages,
                    },
                    "filters": {
                        "status": status.upper() if status else None,
                        "priority": (
                            priority.upper()
                            if priority
                            else None
                        ),
                    },
                    "cases": cases,
                }




    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve fraud cases.",
        ) from error


# ============================================================
# GET SINGLE CASE
# ============================================================

@router.get("/{case_id}")
def get_case(case_id: int):
    """
    Retrieve detailed information about a specific fraud case.
    """

    case_query = """
        SELECT
            fc.case_id,
            fc.alert_id,
            fc.account_id,
            a.account_number,

            fc.investigator_id,
            i.full_name AS investigator_name,

            fc.case_title,
            fc.case_description,
            fc.case_status,
            fc.priority,

            fc.opened_at,
            fc.closed_at,

            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM case_transaction ct
                    WHERE ct.case_id = fc.case_id
                ),
                0
            ) AS linked_transaction_count,

            COALESCE(
                (
                    SELECT SUM(t.amount)
                    FROM case_transaction ct
                    JOIN transaction t
                        ON ct.transaction_id = t.transaction_id
                    WHERE ct.case_id = fc.case_id
                ),
                0
            ) AS suspicious_amount

        FROM fraud_case fc

        INNER JOIN account a
            ON fc.account_id = a.account_id

        LEFT JOIN investigator i
            ON fc.investigator_id = i.investigator_id

        WHERE fc.case_id = %s;
    """

    transactions_query = """
        SELECT
            t.transaction_id,
            t.sender_account_id,
            t.receiver_account_id,
            t.amount,
            t.txn_time,
            t.transaction_type,
            t.channel,
            t.status,
            ct.linked_at,
            ct.link_reason

        FROM case_transaction ct

        INNER JOIN transaction t
            ON ct.transaction_id = t.transaction_id

        WHERE ct.case_id = %s

        ORDER BY t.txn_time DESC;
    """

    notes_query = """
        SELECT
            cn.note_id,
            cn.investigator_id,
            i.full_name AS investigator_name,
            cn.note_text,
            cn.created_at

        FROM case_note cn

        LEFT JOIN investigator i
            ON cn.investigator_id = i.investigator_id

        WHERE cn.case_id = %s

        ORDER BY cn.created_at DESC;
    """

    history_query = """
        SELECT
            csh.history_id,
            csh.old_status,
            csh.new_status,
            csh.changed_by,
            i.full_name AS investigator_name,
            csh.changed_at,
            csh.change_reason

        FROM case_status_history csh

        LEFT JOIN investigator i
            ON csh.changed_by = i.investigator_id

        WHERE csh.case_id = %s

        ORDER BY csh.changed_at DESC;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ------------------------------------------------
                # Case information
                # ------------------------------------------------

                cursor.execute(
                    case_query,
                    (case_id,),
                )

                row = cursor.fetchone()

                if row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Fraud case {case_id} not found.",
                    )

                columns = [
                    description.name
                    for description in cursor.description
                ]

                case = dict(zip(columns, row))

                # ------------------------------------------------
                # Linked transactions
                # ------------------------------------------------

                cursor.execute(
                    transactions_query,
                    (case_id,),
                )

                transaction_rows = cursor.fetchall()

                transaction_columns = [
                    description.name
                    for description in cursor.description
                ]

                transactions = [
                    dict(zip(transaction_columns, row))
                    for row in transaction_rows
                ]

                # ------------------------------------------------
                # Case notes
                # ------------------------------------------------

                cursor.execute(
                    notes_query,
                    (case_id,),
                )

                note_rows = cursor.fetchall()

                note_columns = [
                    description.name
                    for description in cursor.description
                ]

                notes = [
                    dict(zip(note_columns, row))
                    for row in note_rows
                ]

                # ------------------------------------------------
                # Status history
                # ------------------------------------------------

                cursor.execute(
                    history_query,
                    (case_id,),
                )

                history_rows = cursor.fetchall()

                history_columns = [
                    description.name
                    for description in cursor.description
                ]

                status_history = [
                    dict(zip(history_columns, row))
                    for row in history_rows
                ]

                return {
                    "case": case,
                    "transactions": transactions,
                    "notes": notes,
                    "status_history": status_history,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve fraud case.",
        ) from error

# ============================================================
# ADD CASE NOTE
# ============================================================

@router.post("/{case_id}/notes")
def add_case_note(
    case_id: int,
    request: AddCaseNoteRequest,
):
    """
    Add an investigator note to an existing fraud case.
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # Check whether the case exists
                cursor.execute(
                    """
                    SELECT case_id
                    FROM fraud_case
                    WHERE case_id = %s;
                    """,
                    (case_id,),
                )

                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Fraud case {case_id} not found.",
                    )

                # Check whether the investigator exists and is active
                cursor.execute(
                    """
                    SELECT investigator_id, full_name, status
                    FROM investigator
                    WHERE investigator_id = %s;
                    """,
                    (request.investigator_id,),
                )

                investigator = cursor.fetchone()

                if investigator is None:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            f"Investigator "
                            f"{request.investigator_id} not found."
                        ),
                    )

                if investigator[2] != "ACTIVE":
                    raise HTTPException(
                        status_code=400,
                        detail="Investigator is not active.",
                    )

                # Insert the investigation note
                cursor.execute(
                    """
                    INSERT INTO case_note (
                        case_id,
                        investigator_id,
                        note_text
                    )
                    VALUES (%s, %s, %s)
                    RETURNING note_id, created_at;
                    """,
                    (
                        case_id,
                        request.investigator_id,
                        request.note_text.strip(),
                    ),
                )

                note = cursor.fetchone()

            connection.commit()

        return {
            "status": "success",
            "message": "Case note added successfully.",
            "note_id": note[0],
            "case_id": case_id,
            "investigator_id": request.investigator_id,
            "created_at": note[1],
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to add case note.",
        ) from error

# ============================================================
# OPEN CASE
# ============================================================

@router.post("")
def open_case(request: OpenCaseRequest):
    """
    Open a new fraud investigation case using the
    PostgreSQL sp_open_fraud_case procedure.
    """

    allowed_priorities = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }

    priority = request.priority.upper()

    if priority not in allowed_priorities:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid priority. Allowed values: "
                "LOW, MEDIUM, HIGH, CRITICAL."
            ),
        )

    call_query = """
        CALL sp_open_fraud_case(
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        );
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    call_query,
                    (
                        request.alert_id,
                        request.investigator_id,
                        request.case_title,
                        request.case_description,
                        priority,
                        None,
                    ),
                )

                result = cursor.fetchone()

            connection.commit()

        case_id = result[0] if result else None

        if case_id is None:
            raise RuntimeError(
                "The database procedure did not return a case ID."
            )

        return {
            "status": "success",
            "message": "Fraud case opened successfully.",
            "case_id": case_id,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to open fraud case.",
        ) from error


# ============================================================
# CLOSE CASE
# ============================================================

@router.patch("/{case_id}/close")
def close_case(
    case_id: int,
    request: CloseCaseRequest,
):
    """
    Close an existing fraud case using the
    PostgreSQL sp_close_fraud_case procedure.
    """

    call_query = """
        CALL sp_close_fraud_case(
            %s,
            %s,
            %s
        );
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    call_query,
                    (
                        case_id,
                        request.investigator_id,
                        request.closure_reason,
                    ),
                )

            connection.commit()

        return {
            "status": "success",
            "message": "Fraud case closed successfully.",
            "case_id": case_id,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to close fraud case.",
        ) from error