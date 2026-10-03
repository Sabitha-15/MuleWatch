from ml.risk_engine import predict_account_risk

from backend.database import get_connection


def create_risk_assessment(account_id: int):
    """
    Run the ML risk engine and persist the resulting
    risk assessment in PostgreSQL.
    """

    # ========================================================
    # 1. RUN ML RISK ENGINE
    # ========================================================

    assessment = predict_account_risk(account_id)

    risk_score = assessment["risk_score"]
    risk_level = assessment["risk_level"]
    model_version = assessment["model_version"]

    reasons = assessment["reasons"]

    reason_text = "; ".join(reasons)

    # ========================================================
    # 2. FIND THE MOST RECENT TRANSACTION FOR THE ACCOUNT
    # ========================================================

    transaction_query = """
        SELECT transaction_id
        FROM transaction
        WHERE sender_account_id = %s
           OR receiver_account_id = %s
        ORDER BY txn_time DESC
        LIMIT 1;
    """

    insert_query = """
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
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ------------------------------------------------
                # Find latest transaction
                # ------------------------------------------------

                cursor.execute(
                    transaction_query,
                    (account_id, account_id),
                )

                transaction_row = cursor.fetchone()

                transaction_id = (
                    transaction_row[0]
                    if transaction_row
                    else None
                )

                # ------------------------------------------------
                # Persist risk assessment
                # ------------------------------------------------

                cursor.execute(
                    insert_query,
                    (
                        account_id,
                        transaction_id,
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

                saved_assessment = dict(
                    zip(columns, row)
                )

            connection.commit()

    except Exception as error:
        raise RuntimeError(
            "Failed to persist risk assessment."
        ) from error

    return {
        "assessment": assessment,
        "database_record": saved_assessment,
    }