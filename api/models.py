"""Dashboard API request/response models: docs/08 section 3 shapes, one class per named type."""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Page[T](BaseModel):
    items: list[T]
    total: int


class Health(BaseModel):
    status: Literal["ok"]
    db: Literal["ok", "down"]


class Agent(BaseModel):
    agent_id: str
    name: str
    mode: str
    entrypoint: str
    model_config_: dict[str, Any] = Field(alias="model_config", serialization_alias="model_config")
    description: str | None

    # The column is called model_config, which clashes with pydantic's own attribute name.
    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())


class TaskSummary(BaseModel):
    task_id: str
    category: str
    prompt: str
    grader_type: str | None
    faults_allowed: list[str]
    validated: bool
    weak: bool | None


class Scenario(BaseModel):
    id: str
    group: Literal["baseline", "provider", "tool", "instruction", "environment"]
    layer: Literal["none", "proxy", "agent_env", "runner"]
    description: str


class BenchmarkConfig(BaseModel):
    """Launch request (08 section 3.3). Unknown keys, incl. the P2 `models`, are rejected (422)."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    agent_ids: list[str] = Field(min_length=1)
    task_ids: list[str] = Field(min_length=1)
    scenarios: list[str] = Field(default_factory=lambda: ["baseline"], min_length=1)
    n_runs: int = Field(ge=1, le=10)
    spend_cap_usd: float = Field(gt=0)


class Progress(BaseModel):
    total: int
    queued: int
    running: int
    done: int
    infra_error: int
    excluded: int


class Benchmark(BaseModel):
    benchmark_id: str
    name: str
    state: Literal["queued", "running", "completed", "halted_spend_cap", "failed"]
    config: dict[str, Any]
    progress: Progress
    spend_usd: float
    error: str | None
    created_at: dt.datetime
    started_at: dt.datetime | None
    finished_at: dt.datetime | None


class Run(BaseModel):
    run_id: str
    benchmark_id: str | None
    agent_id: str
    task_id: str
    scenario: str
    repeat_index: int
    attempt: int
    state: Literal["queued", "running", "done"]
    status: Literal["PASS", "FAIL", "INFRA_ERROR"] | None
    passed: bool | None
    model: str | None
    tokens_in: int | None
    tokens_out: int | None
    cost: float | None
    cost_confidence: Literal["verified", "estimated"] | None
    duration: float | None
    steps: int | None
    tool_calls: int | None
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    error: str | None


class RunDetail(Run):
    env_fingerprint: dict[str, Any] | None
    grader_result: dict[str, Any] | None
    workspace_diff: str | None


class Event(BaseModel):
    id: int
    run_id: str
    ts: dt.datetime
    # agent_started / grader_result: orchestrator lifecycle events (db migration 002).
    type: Literal["agent_started", "llm_call", "tool_call", "grader_result", "command",
                  "file_write", "net_attempt", "fault_injected"]
    agent_role: str | None
    payload: dict[str, Any]
    latency: int | None
    error: str | None


class PassRate(BaseModel):
    passed: int
    n: int
    value: float | None
    ci_low: float | None
    ci_high: float | None


class Stat(BaseModel):
    n: int
    mean: float | None
    median: float | None
    std: float | None
    ci_low: float | None
    ci_high: float | None


class CostConfidence(BaseModel):
    verified: int
    estimated: int


class ResultRow(BaseModel):
    agent_id: str
    task_id: str | None
    scenario: str
    runs_counted: int
    infra_excluded: int
    pass_rate: PassRate
    cost: Stat
    steps: Stat
    tool_calls: Stat
    duration: Stat
    cost_confidence: CostConfidence


class Results(BaseModel):
    items: list[ResultRow]
    benchmark_id: str
    generated_at: dt.datetime


class ResilienceRow(BaseModel):
    agent_id: str
    scenario: str
    baseline_pass_rate: PassRate
    scenario_pass_rate: PassRate
    resilience_score: float | None


class Resilience(BaseModel):
    items: list[ResilienceRow]


class ErrorBody(BaseModel):
    code: Literal["NOT_FOUND", "VALIDATION_ERROR", "CONFLICT", "INTERNAL"]
    message: str
    details: dict[str, Any] | None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
