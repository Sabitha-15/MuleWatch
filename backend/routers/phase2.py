from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import get_connection

router = APIRouter(prefix="/api/phase2", tags=["Phase 2"])


class TransactionStatusUpdate(BaseModel):
    new_status: str
    change_reason: str


class GenerateReportRequest(BaseModel):
    investigator_id: Optional[int] = None


def _dict_rows(cursor):
    columns = [column.name for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


@router.get("/transactions")
def explore_transactions(
    search: Optional[str] = None,
    status: Optional[str] = None,
    transaction_type: Optional[str] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    conditions = []
    params = []
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append("(CAST(transaction_id AS TEXT) ILIKE %s OR sender_account_number ILIKE %s OR receiver_account_number ILIKE %s OR sender_customer_name ILIKE %s OR receiver_customer_name ILIKE %s)")
        params.extend([pattern] * 5)
    if status:
        conditions.append("status = %s")
        params.append(status.upper())
    if transaction_type:
        conditions.append("transaction_type = %s")
        params.append(transaction_type.upper())
    if min_amount is not None:
        conditions.append("amount >= %s")
        params.append(min_amount)
    if max_amount is not None:
        conditions.append("amount <= %s")
        params.append(max_amount)
    if date_from:
        conditions.append("txn_time >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("txn_time < (%s::date + INTERVAL '1 day')")
        params.append(date_to)
    if account_id is not None:
        conditions.append("(sender_account_id = %s OR receiver_account_id = %s)")
        params.extend([account_id, account_id])
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    offset = (page - 1) * page_size
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT COUNT(*) FROM vw_phase2_transaction_explorer {where}",
                    params,
                )
                total = cursor.fetchone()[0]
                cursor.execute(
                    f"SELECT * FROM vw_phase2_transaction_explorer {where} ORDER BY txn_time DESC, transaction_id DESC LIMIT %s OFFSET %s",
                    params + [page_size, offset],
                )
                rows = _dict_rows(cursor)
        return {
            "transactions": rows,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total else 0,
            },
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Transaction explorer failed: {error}") from error


@router.patch("/transactions/{transaction_id}/status")
def finalize_transaction(transaction_id: int, payload: TransactionStatusUpdate):
    target = payload.new_status.strip().upper()
    if target not in {"SUCCESS", "FAILED"}:
        raise HTTPException(status_code=400, detail="Final status must be SUCCESS or FAILED.")
    if not payload.change_reason.strip():
        raise HTTPException(status_code=400, detail="A change reason is required.")
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL sp_phase2_update_transaction_status(%s, %s, %s)",
                    (transaction_id, target, payload.change_reason.strip()),
                )
                cursor.execute(
                    "SELECT transaction_id, status FROM transaction WHERE transaction_id = %s",
                    (transaction_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Transaction not found.")
        return {"transaction_id": row[0], "status": row[1], "message": "Transaction status updated and audited."}
    except HTTPException:
        raise
    except Exception as error:
        message = str(error)
        code = 404 if "does not exist" in message else 400 if "Only PENDING" in message or "Invalid final" in message or "reason is required" in message else 500
        raise HTTPException(status_code=code, detail=message) from error


@router.get("/transactions/{transaction_id}/audit")
def transaction_status_audit(transaction_id: int):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT audit_id, transaction_id, old_status, new_status, changed_at, change_reason
                       FROM transaction_status_audit WHERE transaction_id = %s
                       ORDER BY changed_at DESC, audit_id DESC""",
                    (transaction_id,),
                )
                rows = _dict_rows(cursor)
        return {"transaction_id": transaction_id, "audit_records": rows}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to load transaction audit: {error}") from error


@router.get("/accounts/{account_id}/network")
def account_network(account_id: int, max_depth: int = Query(2, ge=1, le=5)):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM fn_phase2_account_network(%s, %s)",
                    (account_id, max_depth),
                )
                nodes = _dict_rows(cursor)
                node_ids = [node["account_id"] for node in nodes]
                cursor.execute(
                    """SELECT relationship_id, source_account_id, target_account_id,
                              relationship_type, confidence_score, notes
                       FROM account_relationship
                       WHERE source_account_id = ANY(%s)
                         AND target_account_id = ANY(%s)
                       ORDER BY relationship_id""",
                    (node_ids, node_ids),
                )
                edges = _dict_rows(cursor)
        return {"root_account_id": account_id, "max_depth": max_depth, "nodes": nodes, "edges": edges}
    except Exception as error:
        message = str(error)
        code = 404 if "does not exist" in message else 400 if "depth must" in message else 500
        raise HTTPException(status_code=code, detail=f"Account network query failed: {message}") from error


@router.post("/cases/{case_id}/reports")
def generate_case_report(case_id: int, payload: GenerateReportRequest):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL sp_phase2_generate_case_report(%s, %s, NULL)",
                    (case_id, payload.investigator_id),
                )
                result = cursor.fetchone()
                if not result or result[0] is None:
                    raise HTTPException(status_code=500, detail="Report procedure did not return a report ID.")
                report_id = result[0]
                cursor.execute("SELECT * FROM fn_phase2_get_case_report(%s)", (report_id,))
                report = _dict_rows(cursor)[0]
        return report
    except HTTPException:
        raise
    except Exception as error:
        message = str(error)
        code = 404 if "does not exist" in message else 400 if "Active investigator" in message else 500
        raise HTTPException(status_code=code, detail=f"Report generation failed: {message}") from error


@router.get("/cases/{case_id}/reports")
def list_case_reports(case_id: int):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT report_id, case_id, generated_by, generated_at
                       FROM case_investigation_report WHERE case_id = %s
                       ORDER BY generated_at DESC, report_id DESC""",
                    (case_id,),
                )
                rows = _dict_rows(cursor)
        return {"case_id": case_id, "reports": rows}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to list reports: {error}") from error


@router.get("/reports/{report_id}")
def get_case_report(report_id: int):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM fn_phase2_get_case_report(%s)", (report_id,))
                rows = _dict_rows(cursor)
        if not rows:
            raise HTTPException(status_code=404, detail="Report not found.")
        return rows[0]
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to retrieve report: {error}") from error
