from fastapi import APIRouter, HTTPException

from backend.database import get_connection


router = APIRouter(
    prefix="/api/network",
    tags=["Account Network"],
)


@router.get("/account/{account_id}")
def get_account_network(
    account_id: int,
    max_depth: int = 2,
):
    """
    Return the suspicious-account network around an account.

    Uses ACCOUNT_RELATIONSHIP to identify connected accounts
    and a recursive CTE to traverse the network.
    """

    if max_depth < 1 or max_depth > 5:
        raise HTTPException(
            status_code=400,
            detail="max_depth must be between 1 and 5.",
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ====================================================
                # 1. VERIFY ACCOUNT
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        account_id,
                        account_number,
                        account_type,
                        status
                    FROM account
                    WHERE account_id = %s;
                    """,
                    (account_id,),
                )

                account_row = cursor.fetchone()

                if account_row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Account {account_id} not found.",
                    )

                account_columns = [
                    description.name
                    for description in cursor.description
                ]

                account = dict(
                    zip(account_columns, account_row)
                )

                # ====================================================
                # 2. RECURSIVE NETWORK TRAVERSAL
                # ====================================================

                cursor.execute(
                    """
                    WITH RECURSIVE account_network AS (

                        SELECT
                            ar.account_id,
                            ar.related_account_id,
                            ar.relationship_type,
                            ar.strength,
                            1 AS depth,
                            ARRAY[
                                ar.account_id,
                                ar.related_account_id
                            ] AS path

                        FROM account_relationship ar

                        WHERE ar.account_id = %s

                        UNION ALL

                        SELECT
                            ar.account_id,
                            ar.related_account_id,
                            ar.relationship_type,
                            ar.strength,
                            an.depth + 1,
                            an.path || ar.related_account_id

                        FROM account_relationship ar

                        INNER JOIN account_network an
                            ON ar.account_id =
                               an.related_account_id

                        WHERE an.depth < %s

                          AND NOT (
                              ar.related_account_id =
                              ANY(an.path)
                          )
                    )

                    SELECT DISTINCT
                        an.account_id,
                        source.account_number
                            AS source_account_number,

                        an.related_account_id,
                        target.account_number
                            AS related_account_number,

                        an.relationship_type,
                        an.strength,
                        an.depth

                    FROM account_network an

                    INNER JOIN account source
                        ON an.account_id =
                           source.account_id

                    INNER JOIN account target
                        ON an.related_account_id =
                           target.account_id

                    ORDER BY
                        an.depth,
                        an.strength DESC;
                    """,
                    (account_id, max_depth),
                )

                network_rows = cursor.fetchall()

                network_columns = [
                    description.name
                    for description in cursor.description
                ]

                relationships = [
                    dict(zip(network_columns, row))
                    for row in network_rows
                ]

                # ====================================================
                # 3. NETWORK TRANSACTION ACTIVITY
                # ====================================================

                cursor.execute(
                    """
                    WITH connected_accounts AS (

                        SELECT DISTINCT
                            related_account_id AS account_id

                        FROM account_relationship

                        WHERE account_id = %s

                        UNION

                        SELECT DISTINCT
                            account_id

                        FROM account_relationship

                        WHERE related_account_id = %s
                    )

                    SELECT
                        COUNT(*) AS transaction_count,
                        COALESCE(
                            SUM(t.amount),
                            0
                        ) AS total_amount

                    FROM transaction t

                    WHERE t.sender_account_id IN (
                        SELECT account_id
                        FROM connected_accounts
                    )

                    OR t.receiver_account_id IN (
                        SELECT account_id
                        FROM connected_accounts
                    );
                    """,
                    (account_id, account_id),
                )

                activity_row = cursor.fetchone()

                network_activity = {
                    "transaction_count": activity_row[0],
                    "total_amount": activity_row[1],
                }

                # ====================================================
                # 4. IDENTIFY HIGH-RISK CONNECTED ACCOUNTS
                # ====================================================

                cursor.execute(
                    """
                    WITH connected_accounts AS (

                        SELECT DISTINCT
                            related_account_id AS account_id

                        FROM account_relationship

                        WHERE account_id = %s

                        UNION

                        SELECT DISTINCT
                            account_id

                        FROM account_relationship

                        WHERE related_account_id = %s
                    ),

                    latest_risk AS (

                        SELECT DISTINCT ON (ra.account_id)
                            ra.account_id,
                            ra.risk_score,
                            ra.risk_level,
                            ra.assessed_at

                        FROM risk_assessment ra

                        WHERE ra.account_id IN (
                            SELECT account_id
                            FROM connected_accounts
                        )

                        ORDER BY
                            ra.account_id,
                            ra.assessed_at DESC
                    )

                    SELECT
                        lr.account_id,
                        a.account_number,
                        lr.risk_score,
                        lr.risk_level,
                        lr.assessed_at

                    FROM latest_risk lr

                    INNER JOIN account a
                        ON lr.account_id =
                           a.account_id

                    WHERE lr.risk_level IN (
                        'HIGH',
                        'CRITICAL'
                    )

                    ORDER BY
                        lr.risk_score DESC;
                    """,
                    (account_id, account_id),
                )

                high_risk_rows = cursor.fetchall()

                high_risk_columns = [
                    description.name
                    for description in cursor.description
                ]

                high_risk_accounts = [
                    dict(zip(high_risk_columns, row))
                    for row in high_risk_rows
                ]

                # ====================================================
                # 5. NETWORK SUMMARY
                # ====================================================

                return {
                    "root_account": account,

                    "network_summary": {
                        "max_depth": max_depth,
                        "relationship_count": len(
                            relationships
                        ),
                        "high_risk_connected_accounts": len(
                            high_risk_accounts
                        ),
                        "network_transaction_count":
                            network_activity[
                                "transaction_count"
                            ],
                        "network_transaction_amount":
                            network_activity[
                                "total_amount"
                            ],
                    },

                    "relationships": relationships,

                    "high_risk_accounts":
                        high_risk_accounts,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve account network.",
        ) from error