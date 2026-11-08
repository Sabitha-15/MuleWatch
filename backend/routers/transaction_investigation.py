from fastapi import APIRouter, HTTPException

from backend.database import get_connection


router = APIRouter(
    prefix="/api/investigation",
    tags=["Investigation"],
)


@router.get("/transaction/{transaction_id}")
def get_transaction_investigation(transaction_id: int):
    """
    Return complete investigation evidence for one transaction.

    Includes:
        - transaction
        - sender
        - receiver
        - risk assessments
        - fraud alerts
        - linked cases
        - case status history
        - investigator notes
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # ====================================================
                # 1. TRANSACTION + ACCOUNT DETAILS
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        t.transaction_id,
                        t.sender_account_id,
                        sender.account_number AS sender_account_number,
                        sender.customer_id AS sender_customer_id,

                        t.receiver_account_id,
                        receiver.account_number AS receiver_account_number,
                        receiver.customer_id AS receiver_customer_id,

                        t.beneficiary_id,
                        t.amount,
                        t.txn_time,
                        t.transaction_type,
                        t.channel,
                        t.status,
                        t.description,
                        t.idempotency_key

                    FROM transaction t

                    INNER JOIN account sender
                        ON t.sender_account_id = sender.account_id

                    INNER JOIN account receiver
                        ON t.receiver_account_id = receiver.account_id

                    WHERE t.transaction_id = %s;
                    """,
                    (transaction_id,),
                )

                transaction_row = cursor.fetchone()

                if transaction_row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            f"Transaction {transaction_id} "
                            "not found."
                        ),
                    )

                transaction_columns = [
                    description.name
                    for description in cursor.description
                ]

                transaction = dict(
                    zip(transaction_columns, transaction_row)
                )

                # ====================================================
                # 2. RISK ASSESSMENTS
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        risk_assessment_id,
                        account_id,
                        transaction_id,
                        risk_score,
                        risk_level,
                        model_version,
                        assessed_at,
                        reason
                    FROM risk_assessment
                    WHERE transaction_id = %s
                    ORDER BY assessed_at DESC;
                    """,
                    (transaction_id,),
                )

                risk_rows = cursor.fetchall()

                risk_columns = [
                    description.name
                    for description in cursor.description
                ]

                risk_assessments = [
                    dict(zip(risk_columns, row))
                    for row in risk_rows
                ]

                # ====================================================
                # 3. FRAUD ALERTS
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        fa.alert_id,
                        fa.assessment_id,
                        fa.alert_level,
                        fa.status,
                        fa.created_at
                    FROM fraud_alert fa
                    INNER JOIN risk_assessment ra
                        ON fa.assessment_id =
                           ra.risk_assessment_id
                    WHERE ra.transaction_id = %s
                    ORDER BY fa.created_at DESC;
                    """,
                    (transaction_id,),
                )

                alert_rows = cursor.fetchall()

                alert_columns = [
                    description.name
                    for description in cursor.description
                ]

                alerts = [
                    dict(zip(alert_columns, row))
                    for row in alert_rows
                ]

                # ====================================================
                # 4. FRAUD CASES
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        fc.case_id,
                        fc.alert_id,
                        fc.investigator_id,
                        fc.case_status,
                        fc.case_description,
                        fc.opened_at,
                        fc.closed_at
                    FROM fraud_case fc
                    INNER JOIN fraud_alert fa
                        ON fc.alert_id = fa.alert_id
                    INNER JOIN risk_assessment ra
                        ON fa.assessment_id =
                           ra.risk_assessment_id
                    WHERE ra.transaction_id = %s
                    ORDER BY fc.opened_at DESC;
                    """,
                    (transaction_id,),
                )

                case_rows = cursor.fetchall()

                case_columns = [
                    description.name
                    for description in cursor.description
                ]

                cases = [
                    dict(zip(case_columns, row))
                    for row in case_rows
                ]

                # ====================================================
                # 5. CASE STATUS HISTORY
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        csh.history_id,
                        csh.case_id,
                        csh.old_status,
                        csh.new_status,
                        csh.change_reason,
                        csh.changed_at

                    FROM case_status_history csh

                    INNER JOIN fraud_case fc
                        ON csh.case_id = fc.case_id

                    INNER JOIN fraud_alert fa
                        ON fc.alert_id = fa.alert_id

                    INNER JOIN risk_assessment ra
                        ON fa.assessment_id =
                           ra.risk_assessment_id

                    WHERE ra.transaction_id = %s

                    ORDER BY csh.changed_at DESC;
                    """,
                    (transaction_id,),
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

                # ====================================================
                # 6. INVESTIGATOR NOTES
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        cn.note_id,
                        cn.case_id,
                        cn.investigator_id,
                        cn.note_text,
                        cn.created_at

                    FROM case_note cn

                    INNER JOIN fraud_case fc
                        ON cn.case_id = fc.case_id

                    INNER JOIN fraud_alert fa
                        ON fc.alert_id = fa.alert_id

                    INNER JOIN risk_assessment ra
                        ON fa.assessment_id =
                           ra.risk_assessment_id

                    WHERE ra.transaction_id = %s

                    ORDER BY cn.created_at DESC;
                    """,
                    (transaction_id,),
                )

                note_rows = cursor.fetchall()

                note_columns = [
                    description.name
                    for description in cursor.description
                ]

                investigator_notes = [
                    dict(zip(note_columns, row))
                    for row in note_rows
                ]

                # ====================================================
                # 7. INVESTIGATION SUMMARY
                # ====================================================

                highest_risk = None

                if risk_assessments:
                    highest_risk = max(
                        risk_assessments,
                        key=lambda item: float(
                            item["risk_score"]
                        ),
                    )

                investigation_status = "NO_ALERT"

                if alerts:
                    investigation_status = "ALERTED"

                if cases:
                    open_cases = [
                        case
                        for case in cases
                        if case["case_status"] == "OPEN"
                    ]

                    if open_cases:
                        investigation_status = (
                            "UNDER_INVESTIGATION"
                        )
                    else:
                        investigation_status = "CASE_CLOSED"

                # ====================================================
                # 8. FINAL RESPONSE
                # ====================================================

                return {
                    "transaction": transaction,

                    "investigation_summary": {
                        "status": investigation_status,

                        "highest_risk_score": (
                            float(
                                highest_risk["risk_score"]
                            )
                            if highest_risk
                            else None
                        ),

                        "highest_risk_level": (
                            highest_risk["risk_level"]
                            if highest_risk
                            else None
                        ),

                        "risk_assessment_count": len(
                            risk_assessments
                        ),

                        "alert_count": len(alerts),

                        "case_count": len(cases),

                        "status_change_count": len(
                            status_history
                        ),

                        "investigator_note_count": len(
                            investigator_notes
                        ),
                    },

                    "risk_assessments": risk_assessments,

                    "alerts": alerts,

                    "cases": cases,

                    "status_history": status_history,

                    "investigator_notes": investigator_notes,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to retrieve transaction "
                "investigation."
            ),
        ) from error