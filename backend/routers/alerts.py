from fastapi import APIRouter, HTTPException, Query

from pydantic import BaseModel

from backend.database import get_connection



router = APIRouter(
    prefix="/api/alerts",
    tags=["Fraud Alerts"],
)


@router.get("")
def get_alerts(
    status: str | None = Query(
        default=None,
        description="Filter by alert status: OPEN, UNDER_REVIEW, RESOLVED, DISMISSED",
    ),
    alert_level: str | None = Query(
        default=None,
        description="Filter by alert level: HIGH or CRITICAL",
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
        description="Number of alerts per page",
    ),
):
    """
    Retrieve fraud alerts with optional status/level filtering
    and pagination.
    """

    offset = (page - 1) * page_size

    where_conditions = []
    parameters = []

    if status:
        where_conditions.append("fa.alert_status = %s")
        parameters.append(status.upper())

    if alert_level:
        where_conditions.append("fa.alert_level = %s")
        parameters.append(alert_level.upper())

    where_clause = ""

    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    count_query = f"""
        SELECT COUNT(*)
        FROM fraud_alert fa
        {where_clause};
    """

    alerts_query = f"""
        SELECT
            fa.alert_id,
            fa.risk_assessment_id,
            fa.account_id,
            a.account_number,

            fa.alert_level,
            fa.alert_status,
            fa.alert_message,

            fa.created_at,
            fa.resolved_at,

            ra.risk_score,
            ra.risk_level,
            ra.model_version,
            ra.assessed_at

        FROM fraud_alert fa

        INNER JOIN account a
            ON fa.account_id = a.account_id

        INNER JOIN risk_assessment ra
            ON fa.risk_assessment_id = ra.risk_assessment_id

        {where_clause}

        ORDER BY
            CASE
                WHEN fa.alert_status = 'OPEN' THEN 1
                WHEN fa.alert_status = 'UNDER_REVIEW' THEN 2
                ELSE 3
            END,
            fa.created_at DESC

        LIMIT %s
        OFFSET %s;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ------------------------------------------------
                # Total matching alerts
                # ------------------------------------------------

                cursor.execute(
                    count_query,
                    parameters,
                )

                total_alerts = cursor.fetchone()[0]

                # ------------------------------------------------
                # Paginated alerts
                # ------------------------------------------------

                cursor.execute(
                    alerts_query,
                    parameters + [page_size, offset],
                )

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                alerts = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                total_pages = (
                    (total_alerts + page_size - 1)
                    // page_size
                    if total_alerts > 0
                    else 0
                )

                return {
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_alerts": total_alerts,
                        "total_pages": total_pages,
                    },
                    "filters": {
                        "status": status.upper() if status else None,
                        "alert_level": (
                            alert_level.upper()
                            if alert_level
                            else None
                        ),
                    },
                    "alerts": alerts,
                }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve fraud alerts.",
        ) from error


@router.get("/{alert_id}")
def get_alert(alert_id: int):
    """
    Retrieve detailed information about a specific fraud alert.
    """

    query = """
        SELECT
            fa.alert_id,
            fa.risk_assessment_id,
            fa.account_id,
            a.account_number,

            fa.alert_level,
            fa.alert_status,
            fa.alert_message,

            fa.created_at,
            fa.resolved_at,

            ra.risk_score,
            ra.risk_level,
            ra.model_version,
            ra.assessed_at,
            ra.reason

        FROM fraud_alert fa

        INNER JOIN account a
            ON fa.account_id = a.account_id

        INNER JOIN risk_assessment ra
            ON fa.risk_assessment_id = ra.risk_assessment_id

        WHERE fa.alert_id = %s;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(query, (alert_id,))

                row = cursor.fetchone()

                if row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Fraud alert {alert_id} not found.",
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
            detail="Failed to retrieve fraud alert.",
        ) from error



class AlertStatusUpdate(BaseModel):
    status: str


@router.patch("/{alert_id}/status")
def update_alert_status(
    alert_id: int,
    request: AlertStatusUpdate,
):
    """
    Update the investigation status of a fraud alert.
    """

    allowed_statuses = {
        "OPEN",
        "UNDER_REVIEW",
        "RESOLVED",
        "DISMISSED",
    }

    new_status = request.status.upper()

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid alert status. "
                "Allowed values: OPEN, UNDER_REVIEW, "
                "RESOLVED, DISMISSED."
            ),
        )

    query = """
        UPDATE fraud_alert
        SET
            alert_status = %s,
            resolved_at = CASE
                WHEN %s IN ('RESOLVED', 'DISMISSED')
                    THEN CURRENT_TIMESTAMP
                ELSE NULL
            END
        WHERE alert_id = %s
        RETURNING
            alert_id,
            risk_assessment_id,
            account_id,
            alert_level,
            alert_status,
            alert_message,
            created_at,
            resolved_at;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    query,
                    (
                        new_status,
                        new_status,
                        alert_id,
                    ),
                )

                row = cursor.fetchone()

                if row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Fraud alert {alert_id} not found.",
                    )

                columns = [
                    description.name
                    for description in cursor.description
                ]

                updated_alert = dict(
                    zip(columns, row)
                )

            connection.commit()

            return {
                "status": "success",
                "message": "Fraud alert status updated.",
                "alert": updated_alert,
            }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to update fraud alert status.",
        ) from error