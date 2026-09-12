"""Stable WSGI entrypoint for CAX PƠNG DRANG AI CORE.

The implementation lives in :mod:`app_core`.  This module intentionally keeps
backwards compatibility with existing tests/operational tools that import or
patch selected ``app.*`` globals.
"""

import os
import sys
import types

import app_core as _app_core
from adapters.vbee_tts import blueprint as vbee_blueprint
from config import LOCAL_BIND_HOST


app = _app_core.app
ensure_legal_db = _app_core.ensure_legal_db
split_zalo_messages = _app_core.split_zalo_messages

# Existing tests and small operational scripts historically patched these names
# on ``app``. Route functions now live in app_core, so assignments must be
# mirrored there as well or the patch would look successful while doing nothing.
_FORWARD_NAMES = {
    "OFFICER_API_TOKEN",
    "ENABLE_DEMO_CONSOLE",
    "ZALO_WEBHOOK_ENABLED",
    "ZALO_WEBHOOK_SIGNATURE_REQUIRED",
    "ZALO_APP_ID",
    "ZALO_OA_SECRET_KEY",
    "ZALO_DIRECT_REPLY_ENABLED",
    "core",
    "pending",
}
for _name in _FORWARD_NAMES:
    globals()[_name] = getattr(_app_core, _name)


class _CompatModule(types.ModuleType):
    def __setattr__(self, name, value):
        if name in _FORWARD_NAMES:
            setattr(_app_core, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _CompatModule

# Register optional integrations only at the stable entrypoint.
if "vbee_tts" not in app.blueprints:
    app.register_blueprint(vbee_blueprint)

__all__ = ["app", "ensure_legal_db", "split_zalo_messages"] + sorted(_FORWARD_NAMES)


if __name__ == "__main__":
    app.run(host=LOCAL_BIND_HOST, port=int(os.getenv("PORT", "10000")))
