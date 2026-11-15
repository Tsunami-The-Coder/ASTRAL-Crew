"""Bounded, temporary and isolated sessions for the public synthetic demo.

No accounts or personal recordings are accepted. Session databases are intentionally
stored outside the repository and disappear on expiry, restart, or redeploy.
"""
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
import secrets
import shutil
import tempfile
import threading
import time

from backend.demo_engine import DemoEngine


SESSION_SECONDS = 30 * 60
MAX_SESSIONS = 12
MAX_WRITES_PER_MINUTE = 15


class SessionCapacityError(Exception):
    """This small public demonstration is temporarily at capacity."""


@dataclass
class PublicSession:
    token: str
    engine: DemoEngine
    last_seen: float
    writes: deque = field(default_factory=deque)

    def allow_write(self):
        now = time.monotonic()
        while self.writes and now - self.writes[0] >= 60:
            self.writes.popleft()
        if len(self.writes) >= MAX_WRITES_PER_MINUTE:
            return False
        self.writes.append(now)
        return True


class PublicSessions:
    def __init__(self, model_path: Path):
        self.model_path = Path(model_path)
        self.directory = tempfile.TemporaryDirectory(prefix='astral-visitor-')
        self.sessions = {}
        self.prepared = None
        self.lock = threading.RLock()

    def _expire(self, now):
        expired = [token for token, session in self.sessions.items()
                   if now - session.last_seen >= SESSION_SECONDS]
        for token in expired:
            del self.sessions[token]
            shutil.rmtree(Path(self.directory.name) / token, ignore_errors=True)

    def get(self, token):
        with self.lock:
            now = time.monotonic()
            self._expire(now)
            session = self.sessions.get(token)
            if session:
                session.last_seen = now
            return session

    def create(self):
        with self.lock:
            now = time.monotonic()
            self._expire(now)
            if len(self.sessions) >= MAX_SESSIONS:
                raise SessionCapacityError()
            token = secrets.token_urlsafe(32)
            folder = Path(self.directory.name) / token
            folder.mkdir(mode=0o700)
            try:
                engine = DemoEngine(folder / 'demo.sqlite3', self.model_path, prepared=self.prepared)
                engine.run('baseline')
            except Exception:
                shutil.rmtree(folder, ignore_errors=True)
                raise
            session = PublicSession(token, engine, time.monotonic())
            if self.prepared is None:
                self.prepared = engine
            self.sessions[token] = session
            return session

    def close(self):
        with self.lock:
            self.sessions.clear()
            self.prepared = None
            self.directory.cleanup()
