from fastapi import APIRouter, HTTPException

from backend.database import get_connection


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary")
def get_dashboard_summary():
    """
    Return the main analytics required by the MuleWatch
    investigation dashboard.
    """

    summary_query = """
        SELECT
            (SELECT COUNT(*) FROM account) AS total_accounts,

            (SELECT COUNT(*) FROM transaction) AS total_transactions,

            (
                SELECT COALESCE(SUM(amount), 0)
                FROM transaction
                WHERE status = 'SUCCESS'
            ) AS total_transaction_amount,

            (
                SELECT COUNT(*)
                FROM fraud_alert
                WHERE alert_status = 'OPEN'
            ) AS open_alerts,

            (
                SELECT COUNT(*)
                FROM fraud_alert
                WHERE alert_level = 'CRITICAL'
                  AND alert_status = 'OPEN'
            ) AS critical_alerts,

            (
                SELECT COUNT(*)
                FROM fraud_case
                WHERE case_status <> 'CLOSED'
            ) AS open_cases,

            (
                SELECT COUNT(*)
                FROM account
                WHERE status = 'BLOCKED'
            ) AS blocked_accounts;
    """

    risk_distribution_query = """
        SELECT
            risk_level,
            COUNT(*) AS assessment_count
        FROM risk_assessment
        GROUP BY risk_level
        ORDER BY
            CASE risk_level
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
            END;
    """

    recent_alerts_query = """
        SELECT
            fa.alert_id,
            fa.account_id,
            a.account_number,
            fa.alert_level,
            fa.alert_status,
            fa.alert_message,
            fa.created_at,
            ra.risk_score,
            ra.risk_level
        FROM fraud_alert fa

        INNER JOIN account a
            ON fa.account_id = a.account_id

        INNER JOIN risk_assessment ra
            ON fa.risk_assessment_id = ra.risk_assessment_id

        ORDER BY fa.created_at DESC
        LIMIT 10;
    """

    recent_cases_query = """
        SELECT
            fc.case_id,
            fc.account_id,
            a.account_number,
            fc.case_title,
            fc.case_status,
            fc.priority,
            fc.opened_at,
            i.full_name AS investigator_name
        FROM fraud_case fc

        INNER JOIN account a
            ON fc.account_id = a.account_id

        LEFT JOIN investigator i
            ON fc.investigator_id = i.investigator_id

        ORDER BY fc.opened_at DESC
        LIMIT 10;
    """

    high_risk_accounts_query = """
        SELECT
            a.account_id,
            a.account_number,
            ra.risk_score,
            ra.risk_level,
            ra.assessed_at
        FROM account a

        INNER JOIN LATERAL (
            SELECT
                risk_score,
                risk_level,
                assessed_at
            FROM risk_assessment
            WHERE account_id = a.account_id
            ORDER BY assessed_at DESC
            LIMIT 1
        ) ra ON TRUE

        WHERE ra.risk_score >= 85

        ORDER BY
            ra.risk_score DESC,
            ra.assessed_at DESC

        LIMIT 10;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ------------------------------------------------
                # Main KPI summary
                # ------------------------------------------------

                cursor.execute(summary_query)

                summary_row = cursor.fetchone()

                summary_columns = [
                    description.name
                    for description in cursor.description
                ]

                summary = dict(
                    zip(summary_columns, summary_row)
                )

                # ------------------------------------------------
                # Risk distribution
                # ------------------------------------------------

                cursor.execute(risk_distribution_query)

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                risk_distribution = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                # ------------------------------------------------
                # Recent alerts
                # ------------------------------------------------

                cursor.execute(recent_alerts_query)

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                recent_alerts = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                # ------------------------------------------------
                # Recent fraud cases
                # ------------------------------------------------

                cursor.execute(recent_cases_query)

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                recent_cases = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                # ------------------------------------------------
                # High-risk accounts
                # ------------------------------------------------

                cursor.execute(high_risk_accounts_query)

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                high_risk_accounts = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                return {
                    "status": "success",
                    "summary": summary,
                    "risk_distribution": risk_distribution,
                    "high_risk_accounts": high_risk_accounts,
                    "recent_alerts": recent_alerts,
                    "recent_cases": recent_cases,
                }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard summary.",
        ) from error