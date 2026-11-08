from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import (
    accounts,
    alerts,
    cases,
    dashboard,
    findings, 
    investigation,
    money_flow,
    network,
    risk,
    transaction_investigation,
    transactions,
    phase2,
)
app = FastAPI(
    title="MuleWatch API",
    description=(
        "AI-powered mule account detection and "
        "financial fraud investigation API."
    ),
    version="1.0.0",
)

# ============================================================
# ROUTERS
# ============================================================

app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(risk.router)
app.include_router(alerts.router)
app.include_router(cases.router)
app.include_router(money_flow.router)
app.include_router(dashboard.router)
app.include_router(investigation.router)
app.include_router(
    transaction_investigation.router
)
app.include_router(network.router)
app.include_router(findings.router)
app.include_router(phase2.router)

# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get(
    "/health",
    tags=["System"],
)
def health_check():
    """
    Verify that the MuleWatch API is running.
    """

    return {
        "status": "healthy",
        "service": "MuleWatch API",
        "version": "1.0.0",
    }