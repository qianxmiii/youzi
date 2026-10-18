"""手机模块配置。路径相对仓库根目录解析，不受启动位置影响。"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_path(value: str, root: Path = REPO_ROOT) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


@dataclass(frozen=True)
class MobileSettings:
    database_path: Path
    config_path: Path
    port: int = 3002
    auth_database_path: Path = REPO_ROOT / "youzi_v2/data/mobile/auth.db"
    lan_ip: str | None = None
    tls_cert: Path | None = None
    tls_key: Path | None = None

    @property
    def host(self) -> str:
        return self.lan_ip or "127.0.0.1"

    @property
    def allowed_hosts(self) -> list[str]:
        return ["127.0.0.1", "localhost", "[::1]"] + ([self.lan_ip] if self.lan_ip else [])

    def validate_files(self) -> None:
        for label, path in (("业务数据库", self.database_path), ("业务配置", self.config_path)):
            if not path.is_file():
                raise ValueError(f"{label}不存在：{path}；拒绝创建空数据库或空配置")
        if not 1024 <= self.port <= 65535:
            raise ValueError("手机模块端口必须在 1024–65535 之间")
        if self.auth_database_path.resolve() in (self.database_path.resolve(), self.config_path.resolve()):
            raise ValueError("认证数据库必须与业务数据库和业务配置分开")
        if bool(self.tls_cert) != bool(self.tls_key):
            raise ValueError("TLS 证书和私钥必须同时指定")
        if self.lan_ip:
            from .tls import private_ipv4
            private_ipv4(self.lan_ip)
            if not self.tls_cert or not self.tls_key:
                raise ValueError("局域网模式必须启用 HTTPS，拒绝明文监听")
            from .auth import AuthStore
            if not AuthStore(self.auth_database_path).initialized():
                raise ValueError("请先在本机初始化个人账号，随后再开放局域网")
        if self.tls_cert and self.tls_key:
            from .tls import validate_tls
            validate_tls(self.tls_cert, self.tls_key, self.lan_ip)


def load_settings(env: Mapping[str, str] | None = None, *, port: int | None = None) -> MobileSettings:
    values = os.environ if env is None else env
    database = (
        values.get("YOUZI_MOBILE_DB_PATH", "").strip()
        or values.get("YOUZI_DB_PATH", "").strip()
        or "youzi_v2/data/youzi_v2.db"
    )
    config = values.get("YOUZI_MOBILE_CONFIG_PATH", "").strip() or "config/config.json"
    try:
        resolved_port = port if port is not None else int(values.get("YOUZI_MOBILE_PORT", "3002"))
    except ValueError as exc:
        raise ValueError("YOUZI_MOBILE_PORT 必须为整数") from exc
    auth = values.get("YOUZI_MOBILE_AUTH_DB_PATH", "").strip() or "youzi_v2/data/mobile/auth.db"
    return MobileSettings(resolve_path(database), resolve_path(config), resolved_port, resolve_path(auth))
