"""Stable WSGI entrypoint for CAX PƠNG DRANG AI CORE.

The implementation lives in :mod:`app_core`. After optional integrations are
mounted, ``app`` is aliased to that runtime module so legacy imports/patches and
production routes always reference the same state.
"""

import os
import sys

import app_core as _app_core
import core.service as _service_module
from adapters.vbee_tts import blueprint as vbee_blueprint
from adapters.readiness import blueprint as readiness_blueprint
from adapters.self_test import blueprint as self_test_blueprint
from adapters.demo_ai import blueprint as demo_ai_blueprint
from config import LOCAL_BIND_HOST
from core.current_knowledge import ensure_current_knowledge
from core.current_fallback import grounded_dynamic_fallback as current_grounded_fallback
from core.notebook_current_sources import ensure_notebook_current_sources
from core.notebook_retrieval import retrieve as notebook_retrieve
from core.source_guard import merge_verification


# app_core first loads the long-lived verified snapshots. The current overlay is
# always applied *after* them so superseded TTHC remain auditable but inactive.
_original_ensure_legal_db = _app_core.ensure_legal_db


def _ensure_legal_db_with_current_sources():
    _original_ensure_legal_db()
    ensure_current_knowledge()
    ensure_notebook_current_sources()


_app_core.ensure_legal_db = _ensure_legal_db_with_current_sources
# app_core already initialized once during import, therefore apply the overlays
# immediately for this process as well.
ensure_current_knowledge()
ensure_notebook_current_sources()

# Notebook-style routing extends the normal retriever with the exact source
# groups mirrored from the uploaded Gemini Notebook. Existing domains still use
# the legacy retriever underneath.
_service_module.retrieve = notebook_retrieve

# Dynamic and API-boundary fallbacks must use the same current-source overlay.
# This prevents a provider timeout from resurrecting superseded TTHC guidance.
_service_module.grounded_dynamic_fallback = current_grounded_fallback
_app_core.grounded_dynamic_fallback = current_grounded_fallback

# Add a second grounding gate around model output. The normal verifier handles
# legal claims/numbers; this guard catches operational details the model may
# improvise (physical addresses, office hours, invented integration examples,
# or internal source IDs) even when the core legal claim itself is correct.
_original_service_verify = _service_module.verify
_original_service_verify_dynamic = _service_module.verify_dynamic_text


def _verify_with_source_guard(draft, retrieved_units, question=""):
    result = _original_service_verify(draft, retrieved_units, question=question)
    return merge_verification(result, (draft or {}).get("answer", ""), retrieved_units)


def _verify_dynamic_with_source_guard(answer, retrieved_units, question=""):
    result = _original_service_verify_dynamic(answer, retrieved_units, question=question)
    return merge_verification(result, answer, retrieved_units)


_service_module.verify = _verify_with_source_guard
_service_module.verify_dynamic_text = _verify_dynamic_with_source_guard

if "vbee_tts" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(vbee_blueprint)
if "ai_core_readiness" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(readiness_blueprint)
if "ai_core_self_test" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(self_test_blueprint)
if "ai_core_demo_ai" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(demo_ai_blueprint)

# One module state only. This preserves ``from app import app`` and helpers such
# as split_zalo_messages while ensuring patch("app.X") changes the exact globals
# used by Flask route functions defined in app_core.
sys.modules[__name__] = _app_core


if __name__ == "__main__":
    _app_core.app.run(host=LOCAL_BIND_HOST, port=int(os.getenv("PORT", "10000")))
