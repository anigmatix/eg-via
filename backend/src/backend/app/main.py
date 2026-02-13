"""FastAPI application entrypoint for EG-VIA backend MVP."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.orchestrator import run_interpretation
from backend.app.schemas import HealthzResponse, InterpretRequest, InterpretResponse

app = FastAPI(title="EG-VIA Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", response_model=HealthzResponse)
def healthz() -> HealthzResponse:
    """Health check endpoint."""

    return HealthzResponse(status="ok")


@app.post("/v1/interpret", response_model=InterpretResponse)
def interpret(payload: InterpretRequest) -> InterpretResponse:
    """Interpretation endpoint using a deterministic stub orchestrator."""

    return run_interpretation(payload)

