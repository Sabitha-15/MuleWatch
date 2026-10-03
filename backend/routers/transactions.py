from fastapi import APIRouter, HTTPException, Query

from backend.database import get_connection


router = APIRouter(
    prefix="/api/accounts",
    tags=["Transactions"],
)


@router.get("/{account_id}/transactions")
def get_account_transactions(
    account_id: int,
    page: int = Query(
        1,
        ge=1,
        description="Page number"
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of transactions per page"
    ),
):
    """
    Retrieve paginated transaction history for an account.
    """

    offset = (page - 1) * page_size

    count_query = """
        SELECT COUNT(*)
        FROM transaction
        WHERE sender_account_id = %s
           OR receiver_account_id = %s;
    """

    transaction_query = """
        SELECT
            t.transaction_id,
            t.sender_account_id,
            sender.account_number AS sender_account_number,
            t.receiver_account_id,
            receiver.account_number AS receiver_account_number,
            t.beneficiary_id,
            t.amount,
            t.txn_time,
            t.transaction_type,
            t.channel,
            t.status,
            t.description

        FROM transaction t

        INNER JOIN account sender
            ON t.sender_account_id = sender.account_id

        INNER JOIN account receiver
            ON t.receiver_account_id = receiver.account_id

        WHERE t.sender_account_id = %s
           OR t.receiver_account_id = %s

        ORDER BY t.txn_time DESC

        LIMIT %s
        OFFSET %s;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ------------------------------------------------
                # Verify account exists
                # ------------------------------------------------

                cursor.execute(
                    """
                    SELECT 1
                    FROM account
                    WHERE account_id = %s;
                    """,
                    (account_id,),
                )

                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Account {account_id} not found."
                    )

                # ------------------------------------------------
                # Total transaction count
                # ------------------------------------------------

                cursor.execute(
                    count_query,
                    (account_id, account_id),
                )

                total_transactions = cursor.fetchone()[0]

                # ------------------------------------------------
                # Paginated transactions
                # ------------------------------------------------

                cursor.execute(
                    transaction_query,
                    (
                        account_id,
                        account_id,
                        page_size,
                        offset,
                    ),
                )

                rows = cursor.fetchall()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                transactions = [
                    dict(zip(columns, row))
                    for row in rows
                ]

                total_pages = (
                    (total_transactions + page_size - 1)
                    // page_size
                    if total_transactions > 0
                    else 0
                )

                return {
                    "account_id": account_id,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_transactions": total_transactions,
                        "total_pages": total_pages,
                    },
                    "transactions": transactions,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve transaction history."
        ) from error