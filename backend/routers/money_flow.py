from fastapi import APIRouter, HTTPException, Query

from backend.database import get_connection


router = APIRouter(
    prefix="/api/money-flow",
    tags=["Money Flow"],
)


@router.get("/{account_id}")
def trace_money_flow(
    account_id: int,
    max_depth: int = Query(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of transfer hops to trace",
    ),
):
    """
    Trace outgoing money movement from an account
    across multiple transaction hops.
    """

    query = """
        WITH RECURSIVE money_flow AS (

            -- ------------------------------------------------
            -- First hop
            -- ------------------------------------------------

            SELECT
                t.transaction_id,
                t.sender_account_id AS source_account_id,
                t.receiver_account_id AS target_account_id,
                t.amount,
                t.txn_time,
                t.transaction_type,
                t.channel,
                t.status,
                1 AS depth,

                ARRAY[
                    t.sender_account_id,
                    t.receiver_account_id
                ] AS visited_accounts

            FROM transaction t

            WHERE t.sender_account_id = %s
              AND t.status = 'SUCCESS'


            UNION ALL


            -- ------------------------------------------------
            -- Follow subsequent money movement
            -- ------------------------------------------------

            SELECT
                t.transaction_id,
                t.sender_account_id AS source_account_id,
                t.receiver_account_id AS target_account_id,
                t.amount,
                t.txn_time,
                t.transaction_type,
                t.channel,
                t.status,
                mf.depth + 1,

                mf.visited_accounts || t.receiver_account_id

            FROM money_flow mf

            INNER JOIN transaction t
                ON t.sender_account_id = mf.target_account_id

            WHERE t.status = 'SUCCESS'

              -- The next hop must happen after the
              -- transaction that reached this account.
              AND t.txn_time > mf.txn_time

              -- Respect the requested tracing depth.
              AND mf.depth < %s

              -- Prevent cycles such as:
              -- 5 -> 7 -> 9 -> 5
              AND NOT (
                  t.receiver_account_id = ANY(
                      mf.visited_accounts
                  )
              )
        )

        SELECT
            mf.depth,
            mf.transaction_id,

            mf.source_account_id,
            source.account_number AS source_account_number,

            mf.target_account_id,
            target.account_number AS target_account_number,

            mf.amount,
            mf.txn_time,
            mf.transaction_type,
            mf.channel,
            mf.status

        FROM money_flow mf

        INNER JOIN account source
            ON source.account_id = mf.source_account_id

        INNER JOIN account target
            ON target.account_id = mf.target_account_id

        ORDER BY
            mf.depth,
            mf.txn_time;
    """

    account_query = """
        SELECT
            account_id,
            account_number,
            status
        FROM account
        WHERE account_id = %s;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # --------------------------------------------
                # Verify account exists
                # --------------------------------------------

                cursor.execute(
                    account_query,
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

                # --------------------------------------------
                # Trace money flow
                # --------------------------------------------

                cursor.execute(
                    query,
                    (
                        account_id,
                        max_depth,
                    ),
                )

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                flows = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                # --------------------------------------------
                # Summary
                # --------------------------------------------

                total_amount = sum(
                    float(flow["amount"])
                    for flow in flows
                )

                maximum_depth = max(
                    (flow["depth"] for flow in flows),
                    default=0,
                )

                return {
                    "account": account,
                    "trace": {
                        "max_depth_requested": max_depth,
                        "maximum_depth_reached": maximum_depth,
                        "transactions_found": len(flows),
                        "total_money_movement": total_amount,
                    },
                    "flows": flows,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to trace money flow.",
        ) from error