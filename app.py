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
from core.artifact_planner import enrich_plan as enrich_artifact_plan
from core.current_knowledge import ensure_current_knowledge
from core.current_fallback import grounded_dynamic_fallback as current_grounded_fallback
from core.notebook_current_sources import ensure_notebook_current_sources
from core.notebook_retrieval import retrieve as notebook_retrieve
from core.source_guard import merge_verification


_original_ensure_legal_db = _app_core.ensure_legal_db


def _ensure_legal_db_with_current_sources():
    _original_ensure_legal_db()
    ensure_current_knowledge()
    ensure_notebook_current_sources()


_app_core.ensure_legal_db = _ensure_legal_db_with_current_sources
ensure_current_knowledge()
ensure_notebook_current_sources()

# Artifact-first planner: an input that belongs to one of the 19 sources can no
# longer be silently reclassified outside the user's work by an LLM planner.
_original_service_plan = _service_module.plan


def _artifact_first_plan(question, history, dynamic=False, safety_identifier=None):
    base = _original_service_plan(
        question,
        history,
        dynamic=dynamic,
        safety_identifier=safety_identifier,
    )
    return enrich_artifact_plan(question, base)


_service_module.plan = _artifact_first_plan

# Artifact-first retrieval. Current official documents are only support/update
# data behind the selected artifact source.
_service_module.retrieve = notebook_retrieve

# Dynamic and API-boundary fallbacks must use the current verification layer.
_service_module.grounded_dynamic_fallback = current_grounded_fallback
_app_core.grounded_dynamic_fallback = current_grounded_fallback

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

sys.modules[__name__] = _app_core


if __name__ == "__main__":
    _app_core.app.run(host=LOCAL_BIND_HOST, port=int(os.getenv("PORT", "10000")))
