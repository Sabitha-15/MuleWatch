from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.database import get_connection
from backend.services.risk_service import create_risk_assessment


router = APIRouter(
    prefix="/api/accounts",
    tags=["Transactions"],
)


# ============================================================
# TRANSACTION INGESTION
# ============================================================

class TransactionIngestRequest(BaseModel):
    idempotency_key: str = Field(
        ...,
        min_length=5,
        max_length=100,
    )

    sender_account_id: int = Field(
        ...,
        gt=0,
    )

    receiver_account_id: int = Field(
        ...,
        gt=0,
    )

    beneficiary_id: int | None = Field(
        default=None,
        gt=0,
    )

    amount: Decimal = Field(
        ...,
        gt=0,
    )

    transaction_type: str = Field(
        default="TRANSFER",
        min_length=1,
        max_length=50,
    )

    channel: str = Field(
        default="ONLINE",
        min_length=1,
        max_length=50,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )


@router.post("/transactions/ingest")
def ingest_transaction(request: TransactionIngestRequest):
    """
    Ingest a new transaction and automatically run the
    MuleWatch risk pipeline.

    Pipeline:
        validation
        -> duplicate protection
        -> transaction insert
        -> ML risk assessment
        -> database alert trigger
    """

    if (
        request.sender_account_id
        == request.receiver_account_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Sender and receiver accounts cannot be the same.",
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ====================================================
                # 1. IDEMPOTENCY CHECK
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        transaction_id,
                        status
                    FROM transaction
                    WHERE idempotency_key = %s;
                    """,
                    (request.idempotency_key,),
                )

                existing_transaction = cursor.fetchone()

                if existing_transaction:

                    return {
                        "status": "DUPLICATE",
                        "message": (
                            "Transaction with this idempotency "
                            "key already exists."
                        ),
                        "transaction_id": existing_transaction[0],
                        "transaction_status": existing_transaction[1],
                    }

                # ====================================================
                # 2. VALIDATE SENDER
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        account_id,
                        status
                    FROM account
                    WHERE account_id = %s;
                    """,
                    (request.sender_account_id,),
                )

                sender = cursor.fetchone()

                if sender is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Sender account not found.",
                    )

                if sender[1] != "ACTIVE":
                    raise HTTPException(
                        status_code=400,
                        detail="Sender account is not active.",
                    )

                # ====================================================
                # 3. VALIDATE RECEIVER
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        account_id,
                        status
                    FROM account
                    WHERE account_id = %s;
                    """,
                    (request.receiver_account_id,),
                )

                receiver = cursor.fetchone()

                if receiver is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Receiver account not found.",
                    )

                if receiver[1] != "ACTIVE":
                    raise HTTPException(
                        status_code=400,
                        detail="Receiver account is not active.",
                    )

                # ====================================================
                # 4. VALIDATE BENEFICIARY IF PROVIDED
                # ====================================================

                if request.beneficiary_id is not None:

                    cursor.execute(
                        """
                        SELECT 1
                        FROM beneficiary
                        WHERE beneficiary_id = %s;
                        """,
                        (request.beneficiary_id,),
                    )

                    if cursor.fetchone() is None:
                        raise HTTPException(
                            status_code=404,
                            detail="Beneficiary not found.",
                        )

                # ====================================================
                # 5. INSERT TRANSACTION
                # ====================================================

                cursor.execute(
                    """
                    INSERT INTO transaction (
                        sender_account_id,
                        receiver_account_id,
                        beneficiary_id,
                        amount,
                        txn_time,
                        transaction_type,
                        channel,
                        status,
                        description,
                        idempotency_key
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        CURRENT_TIMESTAMP,
                        %s,
                        %s,
                        'SUCCESS',
                        %s,
                        %s
                    )
                    RETURNING
                        transaction_id,
                        sender_account_id,
                        receiver_account_id,
                        beneficiary_id,
                        amount,
                        txn_time,
                        transaction_type,
                        channel,
                        status,
                        description,
                        idempotency_key;
                    """,
                    (
                        request.sender_account_id,
                        request.receiver_account_id,
                        request.beneficiary_id,
                        request.amount,
                        request.transaction_type,
                        request.channel,
                        request.description,
                        request.idempotency_key,
                    ),
                )

                row = cursor.fetchone()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                transaction = dict(
                    zip(columns, row)
                )

            # ========================================================
            # COMMIT TRANSACTION BEFORE ML
            # ========================================================

            connection.commit()

        # ============================================================
        # 6. RUN ML RISK ASSESSMENT
        # ============================================================

        risk_result = create_risk_assessment(
            account_id=request.sender_account_id,
            transaction_id=transaction["transaction_id"],
        )

        # ============================================================
        # 7. CHECK WHETHER DATABASE TRIGGER CREATED ALERT
        # ============================================================

        risk_record = risk_result["database_record"]

        alert = None

        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        alert_id,
                        risk_assessment_id,
                        alert_level,
                        alert_status,
                        created_at
                    FROM fraud_alert
                    WHERE risk_assessment_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1;
                    """,
                    (risk_record["risk_assessment_id"],),
                )

                alert_row = cursor.fetchone()

                if alert_row:
                    columns = [
                        description.name
                        for description in cursor.description
                    ]

                    alert = dict(
                        zip(columns, alert_row)
                    )

                # ============================================================
        # 8. BUILD INVESTIGATION-READY RESPONSE
        # ============================================================

        risk_level = risk_record["risk_level"]

        if risk_level == "CRITICAL":
            investigation_priority = "IMMEDIATE_REVIEW"
        elif risk_level == "HIGH":
            investigation_priority = "PRIORITY_REVIEW"
        elif risk_level == "MEDIUM":
            investigation_priority = "MONITOR"
        else:
            investigation_priority = "NORMAL"

        return {
            "status": "PROCESSED",

            "transaction": {
                "transaction_id": transaction["transaction_id"],
                "sender_account_id": transaction["sender_account_id"],
                "receiver_account_id": transaction["receiver_account_id"],
                "beneficiary_id": transaction["beneficiary_id"],
                "amount": transaction["amount"],
                "txn_time": transaction["txn_time"],
                "transaction_type": transaction["transaction_type"],
                "channel": transaction["channel"],
                "status": transaction["status"],
                "description": transaction["description"],
            },

            "risk_assessment": {
                "assessment_id": risk_record[
                    "risk_assessment_id"
                ],
                "risk_score": float(
                    risk_record["risk_score"]
                ),
                "risk_level": risk_level,
                "model_version": risk_record["model_version"],
                "reason": risk_record["reason"],
                "assessed_at": risk_record["assessed_at"],
            },

            "investigation": {
                "priority": investigation_priority,
                "requires_review": risk_level in {
                    "HIGH",
                    "CRITICAL",
                },
            },

            "alert": alert,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Transaction ingestion failed: {error}",
        ) from error


# ============================================================
# EXISTING ACCOUNT TRANSACTION HISTORY
# ============================================================

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

                cursor.execute(
                    count_query,
                    (account_id, account_id),
                )

                total_transactions = cursor.fetchone()[0]

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