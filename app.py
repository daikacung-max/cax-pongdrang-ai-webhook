"""Application entrypoint.

The AI/Zalo implementation lives in app_core.py. This module keeps the stable
WSGI entrypoint and re-exports the small public helpers used by tests/tools.
"""

import os

from app_core import app, ensure_legal_db, split_zalo_messages
from adapters.vbee_tts import blueprint as vbee_blueprint
from config import LOCAL_BIND_HOST


app.register_blueprint(vbee_blueprint)

# Backwards-compatible public surface for existing tests and operational tools.
__all__ = ["app", "ensure_legal_db", "split_zalo_messages"]


if __name__ == "__main__":
    app.run(host=LOCAL_BIND_HOST, port=int(os.getenv("PORT", "10000")))
