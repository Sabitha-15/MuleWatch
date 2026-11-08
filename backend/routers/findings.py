from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.database import get_connection


router = APIRouter(
    prefix="/api/investigation",
    tags=["Investigation Findings"],
)


class InvestigationFindingRequest(BaseModel):
    investigator_id: int = Field(..., gt=0)

    finding_type: str = Field(
        ...,
        min_length=1,
        max_length=30,
    )

    finding: str = Field(
        ...,
        min_length=10,
        max_length=5000,
    )


class CaseDecisionRequest(BaseModel):
    investigator_id: int = Field(..., gt=0)

    finding_type: str = Field(
        ...,
        min_length=1,
        max_length=30,
    )

    finding: str = Field(
        ...,
        min_length=10,
        max_length=5000,
    )

    closure_reason: str = Field(
        ...,
        min_length=10,
        max_length=2000,
    )


ALLOWED_FINDINGS = {
    "SUSPICIOUS",
    "LEGITIMATE",
    "INCONCLUSIVE",
}


@router.post("/case/{case_id}/finding")
def record_investigation_finding(
    case_id: int,
    request: InvestigationFindingRequest,
):
    finding_type = request.finding_type.upper()

    if finding_type not in ALLOWED_FINDINGS:
        raise HTTPException(
            status_code=400,
            detail=(
                "finding_type must be SUSPICIOUS, "
                "LEGITIMATE or INCONCLUSIVE."
            ),
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

                case_row = cursor.fetchone()

                if case_row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Fraud case {case_id} not found.",
                    )

                if case_row[1] == "CLOSED":
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot modify a closed case.",
                    )

                cursor.execute(
                    """
                    SELECT investigator_id
                    FROM investigator
                    WHERE investigator_id = %s
                      AND status = 'ACTIVE';
                    """,
                    (request.investigator_id,),
                )

                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Active investigator not found.",
                    )

                cursor.execute(
                    """
                    UPDATE fraud_case
                    SET
                        investigation_finding = %s,
                        finding_type = %s,
                        finding_recorded_at =
                            CURRENT_TIMESTAMP
                    WHERE case_id = %s
                    RETURNING
                        case_id,
                        case_status,
                        investigation_finding,
                        finding_type,
                        finding_recorded_at;
                    """,
                    (
                        request.finding.strip(),
                        finding_type,
                        case_id,
                    ),
                )

                row = cursor.fetchone()

                columns = [
                    description.name
                    for description in cursor.description
                ]

                finding_record = dict(
                    zip(columns, row)
                )

                cursor.execute(
                    """
                    INSERT INTO case_note (
                        case_id,
                        investigator_id,
                        note_text,
                        created_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        CURRENT_TIMESTAMP
                    )
                    RETURNING
                        note_id,
                        case_id,
                        investigator_id,
                        note_text,
                        created_at;
                    """,
                    (
                        case_id,
                        request.investigator_id,
                        (
                            f"Finding [{finding_type}]: "
                            f"{request.finding.strip()}"
                        ),
                    ),
                )

                note_row = cursor.fetchone()

                note_columns = [
                    description.name
                    for description in cursor.description
                ]

                note = dict(
                    zip(note_columns, note_row)
                )

                connection.commit()

                return {
                    "status": "RECORDED",
                    "finding": finding_record,
                    "case_note": note,
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to record investigation finding.",
        ) from error


# ============================================================
# FINAL CASE DECISION
# ============================================================

@router.patch("/case/{case_id}/decision")
def record_case_decision(
    case_id: int,
    request: CaseDecisionRequest,
):
    finding_type = request.finding_type.upper()

    if finding_type not in ALLOWED_FINDINGS:
        raise HTTPException(
            status_code=400,
            detail=(
                "finding_type must be SUSPICIOUS, "
                "LEGITIMATE or INCONCLUSIVE."
            ),
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

                case_row = cursor.fetchone()

                if case_row is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Fraud case {case_id} not found.",
                    )

                if case_row[1] == "CLOSED":
                    raise HTTPException(
                        status_code=400,
                        detail="Case is already closed.",
                    )

                cursor.execute(
                    """
                    SELECT investigator_id
                    FROM investigator
                    WHERE investigator_id = %s
                      AND status = 'ACTIVE';
                    """,
                    (request.investigator_id,),
                )

                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Active investigator not found.",
                    )

                # ----------------------------------------------------
                # Store final finding
                # ----------------------------------------------------

                cursor.execute(
                    """
                    UPDATE fraud_case
                    SET
                        investigation_finding = %s,
                        finding_type = %s,
                        finding_recorded_at =
                            CURRENT_TIMESTAMP
                    WHERE case_id = %s;
                    """,
                    (
                        request.finding.strip(),
                        finding_type,
                        case_id,
                    ),
                )

                # ----------------------------------------------------
                # Preserve evidence in case notes
                # ----------------------------------------------------

                cursor.execute(
                    """
                    INSERT INTO case_note (
                        case_id,
                        investigator_id,
                        note_text,
                        created_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        CURRENT_TIMESTAMP
                    );
                    """,
                    (
                        case_id,
                        request.investigator_id,
                        (
                            f"Final decision [{finding_type}]: "
                            f"{request.finding.strip()}"
                        ),
                    ),
                )

                # ----------------------------------------------------
                # Close through existing stored procedure
                # ----------------------------------------------------

                cursor.execute(
                    """
                    CALL sp_close_fraud_case(
                        %s,
                        %s,
                        %s
                    );
                    """,
                    (
                        case_id,
                        request.investigator_id,
                        request.closure_reason.strip(),
                    ),
                )

                connection.commit()

                return {
                    "status": "CLOSED",
                    "case_id": case_id,
                    "finding_type": finding_type,
                    "message": (
                        "Investigation finding recorded and "
                        "case closed successfully."
                    ),
                }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to record case decision.",
        ) from error