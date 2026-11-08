from fastapi import APIRouter, HTTPException, Query

from backend.database import get_connection


router = APIRouter(
    prefix="/api/money-flow",
    tags=["Money Flow"],
)


@router.get("/{account_id}")
def get_money_flow(
    account_id: int,
    max_depth: int = Query(
        3,
        ge=1,
        le=5,
        description="Maximum number of transaction hops",
    ),
):
    """
    Trace money movement starting from an account.

    The recursive CTE follows successful transactions from the
    root account through connected receiver accounts.
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ====================================================
                # 1. VERIFY ROOT ACCOUNT
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

                root_account = dict(
                    zip(account_columns, account_row)
                )

                # ====================================================
                # 2. TRACE MONEY FLOW
                # ====================================================

                cursor.execute(
                    """
                    WITH RECURSIVE money_flow AS (

                        SELECT
                            t.transaction_id,
                            t.sender_account_id,
                            t.receiver_account_id,
                            t.amount,
                            t.txn_time,
                            t.transaction_type,
                            t.channel,
                            1 AS depth,
                            ARRAY[
                                t.sender_account_id,
                                t.receiver_account_id
                            ] AS path

                        FROM transaction t

                        WHERE t.sender_account_id = %s
                          AND t.status = 'SUCCESS'

                        UNION ALL

                        SELECT
                            t.transaction_id,
                            t.sender_account_id,
                            t.receiver_account_id,
                            t.amount,
                            t.txn_time,
                            t.transaction_type,
                            t.channel,
                            mf.depth + 1,
                            mf.path || t.receiver_account_id

                        FROM transaction t

                        INNER JOIN money_flow mf
                            ON t.sender_account_id =
                               mf.receiver_account_id

                        WHERE t.status = 'SUCCESS'

                          AND mf.depth < %s

                          AND NOT (
                              t.receiver_account_id =
                              ANY(mf.path)
                          )
                    ),

                    -- A transaction can be reached through multiple
                    -- account paths. Keep its shortest discovered depth.
                    unique_money_flow AS (
                        SELECT DISTINCT ON (transaction_id) *
                        FROM money_flow
                        ORDER BY transaction_id, depth, txn_time
                    )

                    SELECT
                        mf.transaction_id,

                        mf.sender_account_id,
                        sender.account_number
                            AS sender_account_number,

                        mf.receiver_account_id,
                        receiver.account_number
                            AS receiver_account_number,

                        mf.amount,
                        mf.txn_time,
                        mf.transaction_type,
                        mf.channel,
                        mf.depth

                    FROM unique_money_flow mf

                    INNER JOIN account sender
                        ON mf.sender_account_id =
                           sender.account_id

                    INNER JOIN account receiver
                        ON mf.receiver_account_id =
                           receiver.account_id

                    ORDER BY
                        mf.depth,
                        mf.txn_time;
                    """,
                    (account_id, max_depth),
                )

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                flow = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                # ====================================================
                # 3. FLOW SUMMARY
                # ====================================================

                total_amount = sum(
                    float(item["amount"])
                    for item in flow
                )

                unique_accounts = {
                    account_id
                }

                for item in flow:
                    unique_accounts.add(
                        item["sender_account_id"]
                    )
                    unique_accounts.add(
                        item["receiver_account_id"]
                    )

                # ====================================================
                # 4. RETURN INVESTIGATION DATA
                # ====================================================

                return {
                    "root_account": root_account,

                    "flow_summary": {
                        "max_depth": max_depth,
                        "transaction_count": len(flow),
                        "unique_accounts_involved": len(
                            unique_accounts
                        ),
                        "total_amount_moved": total_amount,
                    },

                    "money_flow": flow,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to trace money flow.",
        ) from error

@router.get("/{account_id}/investigation")
def get_money_flow_investigation(
    account_id: int,
    max_depth: int = Query(
        3,
        ge=1,
        le=5,
    ),
):
    """
    Return money-flow evidence together with risk information
    for investigation purposes.
    """

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
                # 2. MONEY FLOW
                # ====================================================

                cursor.execute(
                    """
                    WITH RECURSIVE flow AS (

                        SELECT
                            t.transaction_id,
                            t.sender_account_id,
                            t.receiver_account_id,
                            t.amount,
                            t.txn_time,
                            1 AS depth,
                            ARRAY[
                                t.sender_account_id,
                                t.receiver_account_id
                            ] AS path

                        FROM transaction t

                        WHERE t.sender_account_id = %s
                          AND t.status = 'SUCCESS'

                        UNION ALL

                        SELECT
                            t.transaction_id,
                            t.sender_account_id,
                            t.receiver_account_id,
                            t.amount,
                            t.txn_time,
                            f.depth + 1,
                            f.path || t.receiver_account_id

                        FROM transaction t

                        INNER JOIN flow f
                            ON t.sender_account_id =
                               f.receiver_account_id

                        WHERE t.status = 'SUCCESS'
                          AND f.depth < %s
                          AND NOT (
                              t.receiver_account_id =
                              ANY(f.path)
                          )
                    ),

                    -- De-duplicate transaction evidence reached through
                    -- multiple paths, retaining the shortest depth.
                    unique_flow AS (
                        SELECT DISTINCT ON (transaction_id) *
                        FROM flow
                        ORDER BY transaction_id, depth, txn_time
                    )

                    SELECT
                        f.transaction_id,

                        f.sender_account_id,
                        sender.account_number
                            AS sender_account_number,

                        f.receiver_account_id,
                        receiver.account_number
                            AS receiver_account_number,

                        f.amount,
                        f.txn_time,
                        f.depth

                    FROM unique_flow f

                    INNER JOIN account sender
                        ON f.sender_account_id =
                           sender.account_id

                    INNER JOIN account receiver
                        ON f.receiver_account_id =
                           receiver.account_id

                    ORDER BY f.depth, f.txn_time;
                    """,
                    (account_id, max_depth),
                )

                flow_rows = cursor.fetchall()

                flow_columns = [
                    description.name
                    for description in cursor.description
                ]

                money_flow = [
                    dict(zip(flow_columns, row))
                    for row in flow_rows
                ]

                # ====================================================
                # 3. RISK INFORMATION FOR ACCOUNTS IN FLOW
                # ====================================================

                cursor.execute(
                    """
                    WITH RECURSIVE flow_accounts AS (

                        SELECT
                            %s::BIGINT AS account_id,
                            0 AS depth,
                            ARRAY[%s::BIGINT] AS path

                        UNION ALL

                        SELECT
                            t.receiver_account_id,
                            fa.depth + 1,
                            fa.path || t.receiver_account_id

                        FROM transaction t

                        INNER JOIN flow_accounts fa
                            ON t.sender_account_id = fa.account_id

                        WHERE t.status = 'SUCCESS'
                          AND fa.depth < %s
                          AND NOT (
                              t.receiver_account_id =
                              ANY(fa.path)
                          )
                    ),

                    latest_risk AS (

                        SELECT DISTINCT ON (ra.account_id)
                            ra.account_id,
                            ra.risk_score,
                            ra.risk_level,
                            ra.model_version,
                            ra.assessed_at,
                            ra.reason

                        FROM risk_assessment ra

                        WHERE ra.account_id IN (
                            SELECT account_id
                            FROM flow_accounts
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
                        lr.model_version,
                        lr.assessed_at,
                        lr.reason

                    FROM latest_risk lr

                    INNER JOIN account a
                        ON lr.account_id =
                           a.account_id

                    ORDER BY lr.risk_score DESC;
                    """,
                    (
                        account_id,
                        account_id,
                        max_depth,
                    ),
                )

                risk_rows = cursor.fetchall()

                risk_columns = [
                    description.name
                    for description in cursor.description
                ]

                risk_accounts = [
                    dict(zip(risk_columns, row))
                    for row in risk_rows
                ]

                # ====================================================
                # 4. INVESTIGATION SUMMARY
                # ====================================================

                high_risk_accounts = [
                    item
                    for item in risk_accounts
                    if item["risk_level"] in {
                        "HIGH",
                        "CRITICAL",
                    }
                ]

                return {
                    "account": account,

                    "investigation_summary": {
                        "max_depth": max_depth,
                        "transaction_count": len(
                            money_flow
                        ),
                        "total_amount_moved": sum(
                            float(item["amount"])
                            for item in money_flow
                        ),
                        "accounts_with_risk_assessments":
                            len(risk_accounts),
                        "high_risk_accounts":
                            len(high_risk_accounts),
                    },

                    "money_flow": money_flow,

                    "risk_accounts": risk_accounts,

                    "high_risk_accounts":
                        high_risk_accounts,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to retrieve money-flow "
                "investigation data."
            ),
        ) from error