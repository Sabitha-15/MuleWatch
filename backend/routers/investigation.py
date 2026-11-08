from fastapi import APIRouter, HTTPException

from backend.database import get_connection


router = APIRouter(
    prefix="/api/investigation",
    tags=["Investigation"],
)


# ============================================================
# ACCOUNT INVESTIGATION TIMELINE
# ============================================================

@router.get("/account/{account_id}/timeline")
def get_account_investigation_timeline(account_id: int):
    """
    Return a chronological investigation timeline for an account.

    Timeline combines:
        - transactions
        - risk assessments
        - fraud alerts
        - fraud cases
        - case status changes
        - investigator notes
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

                account = cursor.fetchone()

                if account is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Account {account_id} not found.",
                    )

                account_columns = [
                    description.name
                    for description in cursor.description
                ]

                account_data = dict(
                    zip(account_columns, account)
                )

                # ====================================================
                # 2. TRANSACTION EVENTS
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        t.transaction_id,
                        t.txn_time,
                        t.sender_account_id,
                        sender.account_number AS sender_account_number,
                        t.receiver_account_id,
                        receiver.account_number AS receiver_account_number,
                        t.amount,
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
                    ORDER BY t.txn_time DESC;
                    """,
                    (account_id, account_id),
                )

                transaction_rows = cursor.fetchall()

                transaction_columns = [
                    description.name
                    for description in cursor.description
                ]

                transactions = [
                    dict(zip(transaction_columns, row))
                    for row in transaction_rows
                ]

                # ====================================================
                # 3. RISK ASSESSMENT EVENTS
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        ra.risk_assessment_id,
                        ra.assessed_at,
                        ra.transaction_id,
                        ra.risk_score,
                        ra.risk_level,
                        ra.model_version,
                        ra.reason
                    FROM risk_assessment ra
                    WHERE ra.account_id = %s
                    ORDER BY ra.assessed_at DESC;
                    """,
                    (account_id,),
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
                # 4. FRAUD ALERT EVENTS
                # ====================================================

                cursor.execute(
                    """
                    SELECT
                        fa.alert_id,
                        fa.risk_assessment_id,
                        fa.alert_level,
                        fa.alert_status,
                        fa.created_at
                    FROM fraud_alert fa
                    INNER JOIN risk_assessment ra
                        ON fa.risk_assessment_id =
                           ra.risk_assessment_id
                    WHERE ra.account_id = %s
                    ORDER BY fa.created_at DESC;
                    """,
                    (account_id,),
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
                # 5. FRAUD CASE EVENTS
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
                        ON fa.risk_assessment_id =
                           ra.risk_assessment_id
                    WHERE ra.account_id = %s
                    ORDER BY fc.opened_at DESC;
                    """,
                    (account_id,),
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
                # 6. CASE STATUS HISTORY
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
                        ON fa.risk_assessment_id =
                           ra.risk_assessment_id
                    WHERE ra.account_id = %s
                    ORDER BY csh.changed_at DESC;
                    """,
                    (account_id,),
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
                # 7. INVESTIGATOR NOTES
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
                        ON fa.risk_assessment_id =
                           ra.risk_assessment_id
                    WHERE ra.account_id = %s
                    ORDER BY cn.created_at DESC;
                    """,
                    (account_id,),
                )

                note_rows = cursor.fetchall()

                note_columns = [
                    description.name
                    for description in cursor.description
                ]

                notes = [
                    dict(zip(note_columns, row))
                    for row in note_rows
                ]

                # ====================================================
                # 8. RETURN INVESTIGATION WORKSPACE DATA
                # ====================================================

                return {
                    "account": account_data,

                    "investigation_summary": {
                        "transaction_count": len(transactions),
                        "risk_assessment_count": len(
                            risk_assessments
                        ),
                        "alert_count": len(alerts),
                        "case_count": len(cases),
                        "status_change_count": len(
                            status_history
                        ),
                        "investigator_note_count": len(notes),
                    },

                    "transactions": transactions,

                    "risk_assessments": risk_assessments,

                    "alerts": alerts,

                    "cases": cases,

                    "status_history": status_history,

                    "investigator_notes": notes,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve investigation timeline.",
        ) from error


# ============================================================
# ACCOUNT NETWORK
# ============================================================

@router.get("/network/account/{account_id}")
def get_account_network(account_id: int, max_depth: int = 2):
    """Return connected accounts reachable through successful transactions."""
    max_depth = max(1, min(max_depth, 5))

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT account_id, account_number
                    FROM account
                    WHERE account_id = %s;
                    """,
                    (account_id,),
                )
                root = cursor.fetchone()

                if root is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Account {account_id} not found.",
                    )

                cursor.execute(
                    """
                    WITH RECURSIVE account_network AS (
                        SELECT
                            %s::BIGINT AS account_id,
                            0 AS depth,
                            ARRAY[%s::BIGINT] AS path

                        UNION ALL

                        SELECT
                            CASE
                                WHEN t.sender_account_id = an.account_id
                                    THEN t.receiver_account_id
                                ELSE t.sender_account_id
                            END AS account_id,
                            an.depth + 1,
                            an.path ||
                            CASE
                                WHEN t.sender_account_id = an.account_id
                                    THEN t.receiver_account_id
                                ELSE t.sender_account_id
                            END
                        FROM account_network an
                        INNER JOIN transaction t
                            ON (
                                t.sender_account_id = an.account_id
                                OR t.receiver_account_id = an.account_id
                            )
                        WHERE t.status = 'SUCCESS'
                          AND an.depth < %s
                          AND NOT (
                              CASE
                                  WHEN t.sender_account_id = an.account_id
                                      THEN t.receiver_account_id
                                  ELSE t.sender_account_id
                              END = ANY(an.path)
                          )
                    )
                    SELECT DISTINCT
                        an.account_id AS related_account_id,
                        a.account_number AS related_account_number,
                        an.depth
                    FROM account_network an
                    INNER JOIN account a
                        ON a.account_id = an.account_id
                    WHERE an.account_id <> %s
                    ORDER BY an.depth, an.account_id;
                    """,
                    (account_id, account_id, max_depth, account_id),
                )

                rows = cursor.fetchall()

                relationships = [
                    {
                        "source_account_id": account_id,
                        "source_account_number": root[1],
                        "related_account_id": row[0],
                        "related_account_number": row[1],
                        "depth": row[2],
                    }
                    for row in rows
                ]

                return {
                    "account_id": account_id,
                    "network_summary": {
                        "relationship_count": len(relationships),
                    },
                    "relationships": relationships,
                }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve account network.",
        ) from error


# ============================================================
# TRANSACTION EVIDENCE
# ============================================================

@router.get("/transaction/{transaction_id}")
def get_transaction_evidence(transaction_id: int):
    """Return investigation evidence associated with one transaction."""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        t.transaction_id,
                        t.txn_time,
                        t.sender_account_id,
                        sender.account_number AS sender_account_number,
                        t.receiver_account_id,
                        receiver.account_number AS receiver_account_number,
                        t.amount,
                        t.transaction_type,
                        t.channel,
                        t.status,
                        t.description
                    FROM transaction t
                    INNER JOIN account sender
                        ON t.sender_account_id = sender.account_id
                    INNER JOIN account receiver
                        ON t.receiver_account_id = receiver.account_id
                    WHERE t.transaction_id = %s;
                    """,
                    (transaction_id,),
                )
                row = cursor.fetchone()

                if row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Transaction {transaction_id} not found.",
                    )

                columns = [description.name for description in cursor.description]
                transaction = dict(zip(columns, row))

                cursor.execute(
                    """
                    SELECT
                        ra.risk_assessment_id,
                        ra.account_id,
                        ra.risk_score,
                        ra.risk_level,
                        ra.model_version,
                        ra.reason,
                        ra.assessed_at
                    FROM risk_assessment ra
                    WHERE ra.transaction_id = %s
                    ORDER BY ra.assessed_at DESC;
                    """,
                    (transaction_id,),
                )
                risk_rows = cursor.fetchall()
                risk_columns = [
                    description.name for description in cursor.description
                ]
                risk_assessments = [
                    dict(zip(risk_columns, row))
                    for row in risk_rows
                ]

                cursor.execute(
                    """
                    SELECT
                        fa.alert_id,
                        fa.risk_assessment_id,
                        fa.alert_level,
                        fa.alert_status,
                        fa.created_at
                    FROM fraud_alert fa
                    INNER JOIN risk_assessment ra
                        ON fa.risk_assessment_id = ra.risk_assessment_id
                    WHERE ra.transaction_id = %s
                    ORDER BY fa.created_at DESC;
                    """,
                    (transaction_id,),
                )
                alert_rows = cursor.fetchall()
                alert_columns = [
                    description.name for description in cursor.description
                ]
                alerts = [
                    dict(zip(alert_columns, row))
                    for row in alert_rows
                ]

                cursor.execute(
                    """
                    SELECT
                        fc.case_id,
                        fc.alert_id,
                        fc.case_status,
                        fc.opened_at,
                        fc.closed_at
                    FROM fraud_case fc
                    INNER JOIN fraud_alert fa
                        ON fc.alert_id = fa.alert_id
                    INNER JOIN risk_assessment ra
                        ON fa.risk_assessment_id = ra.risk_assessment_id
                    WHERE ra.transaction_id = %s
                    ORDER BY fc.opened_at DESC;
                    """,
                    (transaction_id,),
                )
                case_rows = cursor.fetchall()
                case_columns = [
                    description.name for description in cursor.description
                ]
                cases = [
                    dict(zip(case_columns, row))
                    for row in case_rows
                ]

                highest_risk = (
                    max(
                        (float(item["risk_score"]) for item in risk_assessments),
                        default=None,
                    )
                )

                return {
                    "transaction": transaction,
                    "risk_assessments": risk_assessments,
                    "alerts": alerts,
                    "cases": cases,
                    "investigation_summary": {
                        "status": transaction["status"],
                        "highest_risk_score": highest_risk,
                        "alert_count": len(alerts),
                        "case_count": len(cases),
                    },
                }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve transaction evidence.",
        ) from error


# ============================================================
# INVESTIGATION FINDING
# ============================================================

@router.post("/case/{case_id}/finding")
def save_investigation_finding(
    case_id: int,
    payload: dict,
):
    """Persist an investigation finding as a case note."""
    investigator_id = payload.get("investigator_id")
    finding_type = str(payload.get("finding_type", "INCONCLUSIVE")).upper()
    finding = str(payload.get("finding", "")).strip()

    if not investigator_id:
        raise HTTPException(
            status_code=400,
            detail="investigator_id is required.",
        )

    if not finding:
        raise HTTPException(
            status_code=400,
            detail="finding is required.",
        )

    if finding_type not in {"SUSPICIOUS", "LEGITIMATE", "INCONCLUSIVE"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid finding_type.",
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT case_id, case_status
                    FROM fraud_case
                    WHERE case_id = %s;
                    """,
                    (case_id,),
                )
                case = cursor.fetchone()

                if case is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Case {case_id} not found.",
                    )

                if case[1] == "CLOSED":
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot add a finding to a closed case.",
                    )

                cursor.execute(
                    """
                    INSERT INTO case_note (
                        case_id,
                        investigator_id,
                        note_text
                    )
                    VALUES (%s, %s, %s)
                    RETURNING note_id, case_id, investigator_id,
                              note_text, created_at;
                    """,
                    (
                        case_id,
                        investigator_id,
                        f"[{finding_type}] {finding}",
                    ),
                )

                row = cursor.fetchone()
                connection.commit()

                columns = [description.name for description in cursor.description]

                return {
                    "message": "Investigation finding recorded successfully.",
                    "finding": dict(zip(columns, row)),
                }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to record investigation finding.",
        ) from error


# ============================================================
# CASE DECISION AND CLOSURE
# ============================================================

@router.patch("/case/{case_id}/decision")
def record_case_decision(
    case_id: int,
    payload: dict,
):
    """Record the final finding, closure reason, and close the case."""
    investigator_id = payload.get("investigator_id")
    finding_type = str(payload.get("finding_type", "INCONCLUSIVE")).upper()
    finding = str(payload.get("finding", "")).strip()
    closure_reason = str(payload.get("closure_reason", "")).strip()

    if not investigator_id:
        raise HTTPException(
            status_code=400,
            detail="investigator_id is required.",
        )

    if not finding or not closure_reason:
        raise HTTPException(
            status_code=400,
            detail="finding and closure_reason are required.",
        )

    if finding_type not in {"SUSPICIOUS", "LEGITIMATE", "INCONCLUSIVE"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid finding_type.",
        )

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT case_id, case_status, case_description
                    FROM fraud_case
                    WHERE case_id = %s
                    FOR UPDATE;
                    """,
                    (case_id,),
                )
                case = cursor.fetchone()

                if case is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Case {case_id} not found.",
                    )

                if case[1] == "CLOSED":
                    raise HTTPException(
                        status_code=400,
                        detail="Case is already closed.",
                    )

                # Preserve the final finding in the case notes.
                cursor.execute(
                    """
                    INSERT INTO case_note (
                        case_id,
                        investigator_id,
                        note_text
                    )
                    VALUES (%s, %s, %s);
                    """,
                    (
                        case_id,
                        investigator_id,
                        f"[FINAL {finding_type}] {finding}",
                    ),
                )

                # The existing case-status trigger records the status change.
                # Keep the closure reason in the description for audit history.
                existing_description = case[2] or ""
                separator = "\n" if existing_description else ""
                updated_description = (
                    existing_description
                    + separator
                    + f"Final finding ({finding_type}): {finding}"
                    + f"\nClosure reason: {closure_reason}"
                )

                cursor.execute(
                    """
                    UPDATE fraud_case
                    SET
                        case_status = 'CLOSED',
                        case_description = %s,
                        closed_at = CURRENT_TIMESTAMP
                    WHERE case_id = %s
                    RETURNING case_id, case_status, closed_at;
                    """,
                    (updated_description, case_id),
                )

                row = cursor.fetchone()
                connection.commit()

                columns = [description.name for description in cursor.description]

                return {
                    "message": "Case decision recorded and case closed.",
                    "case": dict(zip(columns, row)),
                }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to record case decision.",
        ) from error
