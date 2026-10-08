"""Decide the mode (Azure or the offline safety net), run the preflight, and prepare ML + the explainer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from ..rag import mode
from ..rag.azure_client import azure_configured
from ..rag.config import get_settings
from ..rag.doctor import format_checks, ok, run_checks
from .cases import ROOT
from .ml_probe import ml_status


class PreflightFailed(RuntimeError):
    """Azure was required but is not working. The message is the full preflight output."""


@dataclass
class Session:
    banner: str
    azure_mode: bool
    ml_enabled: bool
    ml_reason: str | None  # why ML is off, shown in the report; None when ML is on
    notices: list[str] = field(default_factory=list)
    llm: object | None = None  # LLMClient in Azure mode


def start_session(offline: bool = False, require_azure: bool | None = None) -> Session:
    """`require_azure=None` means: required when the Azure env vars are set (and not --offline)."""
    os.chdir(ROOT)  # the model path is relative to the working directory
    if offline and require_azure:
        raise ValueError("--offline and --require-azure cannot be combined")
    notices: list[str] = []

    if offline:
        mode.force_offline()
    else:
        settings = get_settings()
        required = azure_configured(settings) if require_azure is None else require_azure
        if required:
            checks = run_checks(settings)
            failed = [c for c in checks if c.status == "FAIL"]
            if failed and all(c.name == "policy index" for c in failed):
                # Everything else works; only a stale index (e.g. built offline) is wrong. It is derived,
                # gitignored data, so rebuild it with the Azure embedder instead of stopping the demo.
                from ..rag.retriever import PolicyRetriever

                try:
                    PolicyRetriever(settings).ingest()
                except Exception as exc:  # noqa: BLE001
                    raise PreflightFailed(f"Azure OpenAI preflight FAILED: the policy index needs rebuilding "
                                          f"({failed[0].detail}) and the rebuild failed: {exc}") from exc
                notices.append(f"Rebuilt the policy index with the Azure embedder ({failed[0].detail}).")
                mode.reset_caches()
                checks = run_checks(settings)
            if not ok(checks):
                raise PreflightFailed(
                    "Azure OpenAI preflight FAILED, so nothing was run.\n\n" + format_checks(settings, checks)
                    + "\n\nFix the lines above, or run with --offline for the safety-net mode (no Azure).")
        else:
            notices.append("Azure OpenAI variables are not set: running in the offline safety-net mode.")
            mode.force_offline()

    settings = get_settings()
    azure = mode.is_azure_mode(settings)
    llm = None
    if azure:
        from ..orchestrator.llm_client import LLMClient

        llm = LLMClient(settings)
    usable, reason = ml_status()
    return Session(banner=mode.banner(settings), azure_mode=azure, ml_enabled=usable,
                   ml_reason=None if usable else reason, notices=notices, llm=llm)
