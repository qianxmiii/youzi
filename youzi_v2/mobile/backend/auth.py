"""单账号认证：独立 SQLite、scrypt 密码哈希、可撤销的服务端会话。"""

from contextlib import contextmanager
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import sqlite3
import time

COOKIE_NAME = "youzi_mobile_session"
SESSION_SECONDS = 8 * 60 * 60
FAILURE_WINDOW = 15 * 60
MAX_FAILURES = 5


class AuthError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)


def validate_password(password: str) -> None:
    if not 12 <= len(password) <= 256 or not password.strip():
        raise AuthError(400, "密码须为 12–256 个字符，建议使用独有的长密码")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def transaction(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS owner (
                    id INTEGER PRIMARY KEY CHECK (id=1), username TEXT NOT NULL,
                    salt BLOB NOT NULL, password_hash BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, expires REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS failures (attempted REAL NOT NULL);
            """)
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        finally:
            if conn.in_transaction:
                conn.rollback()
            conn.close()

    def initialized(self) -> bool:
        if not self.path.exists():
            return False
        with self.transaction() as conn:
            return conn.execute("SELECT 1 FROM owner WHERE id=1").fetchone() is not None

    def setup(self, username: str, password: str) -> None:
        username = username.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,48}", username):
            raise AuthError(400, "账号须为 3–48 位英文字母、数字、下划线或连字符")
        validate_password(password)
        salt = secrets.token_bytes(16)
        digest = password_hash(password, salt)
        with self.transaction() as conn:
            if conn.execute("SELECT 1 FROM owner WHERE id=1").fetchone():
                raise AuthError(409, "个人账号已经初始化，请登录")
            conn.execute("INSERT INTO owner VALUES (1, ?, ?, ?)", (username, salt, digest))

    def login(self, username: str, password: str) -> tuple[str, str]:
        now = time.time()
        token = None
        name = ""
        with self.transaction() as conn:
            conn.execute("DELETE FROM failures WHERE attempted <= ?", (now - FAILURE_WINDOW,))
            if conn.execute("SELECT COUNT(*) FROM failures").fetchone()[0] >= MAX_FAILURES:
                raise AuthError(429, "登录失败次数过多，请 15 分钟后再试")
            owner = conn.execute("SELECT * FROM owner WHERE id=1").fetchone()
            salt = bytes(owner["salt"]) if owner else b"\0" * 16
            digest = password_hash(password, salt)
            matched = owner is not None and hmac.compare_digest(digest, bytes(owner["password_hash"]))
            if matched and hmac.compare_digest(username.strip().encode(), owner["username"].encode()):
                token = secrets.token_urlsafe(32)
                name = owner["username"]
                conn.execute("DELETE FROM sessions WHERE expires <= ?", (now,))
                conn.execute("INSERT INTO sessions VALUES (?, ?)", (token_hash(token), now + SESSION_SECONDS))
                conn.execute("DELETE FROM failures")
            else:
                # 先提交失败记录，再由调用方收到认证错误，避免回滚掉限速计数。
                conn.execute("INSERT INTO failures VALUES (?)", (now,))
        if token is None:
            raise AuthError(401, "账号或密码不正确")
        return name, token

    def session_user(self, token: str | None) -> str | None:
        if not token or len(token) > 128 or not self.path.exists():
            return None
        with self.transaction() as conn:
            conn.execute("DELETE FROM sessions WHERE expires <= ?", (time.time(),))
            row = conn.execute("SELECT username FROM owner WHERE id=1 AND EXISTS (SELECT 1 FROM sessions WHERE token_hash=?)", (token_hash(token),)).fetchone()
            return row["username"] if row else None

    def logout(self, token: str) -> None:
        with self.transaction() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))

    def change_password(self, token: str, current: str, new: str) -> None:
        validate_password(new)
        error = False
        now = time.time()
        with self.transaction() as conn:
            valid = conn.execute("SELECT 1 FROM sessions WHERE token_hash=? AND expires>?", (token_hash(token), now)).fetchone()
            if not valid:
                raise AuthError(401, "请重新登录")
            conn.execute("DELETE FROM failures WHERE attempted <= ?", (now - FAILURE_WINDOW,))
            if conn.execute("SELECT COUNT(*) FROM failures").fetchone()[0] >= MAX_FAILURES:
                raise AuthError(429, "验证失败次数过多，请 15 分钟后再试")
            owner = conn.execute("SELECT * FROM owner WHERE id=1").fetchone()
            if not hmac.compare_digest(password_hash(current, bytes(owner["salt"])), bytes(owner["password_hash"])):
                conn.execute("INSERT INTO failures VALUES (?)", (now,))
                error = True
            else:
                salt = secrets.token_bytes(16)
                conn.execute("UPDATE owner SET salt=?, password_hash=? WHERE id=1", (salt, password_hash(new, salt)))
                conn.execute("DELETE FROM sessions")
                conn.execute("DELETE FROM failures")
        if error:
            raise AuthError(401, "当前密码不正确")

    def reset_password_locally(self, new: str) -> None:
        """只供本机交互式恢复工具调用，不提供 HTTP 路由。"""
        validate_password(new)
        if not self.initialized():
            raise AuthError(400, "尚未初始化，请先打开本机页面设置账号")
        salt = secrets.token_bytes(16)
        with self.transaction() as conn:
            conn.execute("UPDATE owner SET salt=?, password_hash=? WHERE id=1", (salt, password_hash(new, salt)))
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM failures")
