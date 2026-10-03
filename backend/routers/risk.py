from fastapi import APIRouter, HTTPException

from backend.services.risk_service import create_risk_assessment


router = APIRouter(
    prefix="/api/risk",
    tags=["Risk Assessment"],
)


@router.post("/{account_id}/assess")
def assess_account_risk(account_id: int):
    """
    Run the MuleWatch ML risk engine and persist
    the resulting assessment in PostgreSQL.
    """

    try:
        result = create_risk_assessment(account_id)

        return {
            "status": "success",
            **result,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail="Risk model or feature data is unavailable.",
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Risk assessment failed.",
        ) from error