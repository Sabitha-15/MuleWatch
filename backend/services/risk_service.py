from ml.risk_engine import predict_account_risk

from backend.database import get_connection


def create_risk_assessment(
    account_id: int,
    transaction_id: int | None = None,
):
    """
    Run the MuleWatch ML risk engine and persist the resulting
    risk assessment.

    When transaction_id is supplied, the assessment is explicitly
    associated with that transaction.
    """

    # ============================================================
    # 1. RUN ML MODEL
    # ============================================================

    assessment = predict_account_risk(account_id)

    risk_score = float(assessment["risk_score"])
    risk_level = assessment["risk_level"]
    model_version = assessment["model_version"]
    reasons = assessment.get("reasons", [])

    reason_text = "; ".join(reasons)

    # ============================================================
    # 2. VALIDATE / RESOLVE TRANSACTION
    # ============================================================

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                if transaction_id is not None:

                    cursor.execute(
                        """
                        SELECT
                            transaction_id,
                            sender_account_id,
                            receiver_account_id
                        FROM transaction
                        WHERE transaction_id = %s;
                        """,
                        (transaction_id,),
                    )

                    transaction_row = cursor.fetchone()

                    if transaction_row is None:
                        raise ValueError(
                            f"Transaction {transaction_id} not found."
                        )

                    if account_id not in (
                        transaction_row[1],
                        transaction_row[2],
                    ):
                        raise ValueError(
                            "Transaction does not belong to "
                            "the assessed account."
                        )

                    linked_transaction_id = transaction_row[0]

                else:

                    cursor.execute(
                        """
                        SELECT transaction_id
                        FROM transaction
                        WHERE sender_account_id = %s
                           OR receiver_account_id = %s
                        ORDER BY txn_time DESC
                        LIMIT 1;
                        """,
                        (
                            account_id,
                            account_id,
                        ),
                    )

                    transaction_row = cursor.fetchone()

                    linked_transaction_id = (
                        transaction_row[0]
                        if transaction_row
                        else None
                    )

                # ====================================================
                # 3. STORE RISK ASSESSMENT
                # ====================================================

                cursor.execute(
                    """
                    INSERT INTO risk_assessment (
                        account_id,
                        transaction_id,
                        risk_score,
                        risk_level,
                        model_version,
                        reason
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    RETURNING
                        risk_assessment_id,
                        account_id,
                        transaction_id,
                        risk_score,
                        risk_level,
                        model_version,
                        assessed_at,
                        reason;
                    """,
                    (
                        account_id,
                        linked_transaction_id,
                        risk_score,
                        risk_level,
                        model_version,
                        reason_text,
                    ),
                )

                row = cursor.fetchone()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                database_record = dict(
                    zip(columns, row)
                )

            connection.commit()

    except Exception as error:
        raise RuntimeError(
            "Failed to persist risk assessment."
        ) from error

    # ============================================================
    # 4. RETURN INVESTIGATION-READY RESULT
    # ============================================================

    return {
        "assessment": {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "model_version": model_version,
            "reasons": reasons,
        },
        "database_record": database_record,
    }