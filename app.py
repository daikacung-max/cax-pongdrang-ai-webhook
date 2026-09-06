"""Application entrypoint.

The existing AI/Zalo implementation lives unchanged in app_core.py. This thin
entrypoint only mounts optional integrations such as Vbee TTS.
"""

import os

from app_core import app
from adapters.vbee_tts import blueprint as vbee_blueprint
from config import LOCAL_BIND_HOST


app.register_blueprint(vbee_blueprint)


if __name__ == "__main__":
    app.run(host=LOCAL_BIND_HOST, port=int(os.getenv("PORT", "10000")))
