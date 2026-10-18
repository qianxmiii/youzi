"""SQLite 一致性备份、校验及恢复副本；不导入应用，不启动同步任务。"""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3
import sys
import time
import uuid

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"
DEFAULT_BACKUP_DIR = DEFAULT_DATABASE.parent / "backups"


def open_readonly(path: Path) -> sqlite3.Connection:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"数据库文件不存在：{path}")
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)


def check_database(conn: sqlite3.Connection) -> int:
    results = conn.execute("PRAGMA integrity_check").fetchall()
    if results != [("ok",)]:
        raise ValueError("数据库完整性检查失败，请保留原文件，不要用于恢复")
    return int(conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchone()[0])


def copy_database(source: Path, destination: Path, *, timeout: float = 120) -> int:
    """使用 SQLite backup API 包含已提交 WAL 数据；目标必须为全新文件。"""
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()
    if source == destination:
        raise ValueError("源数据库和目标文件不能相同")
    if any(Path(str(destination) + suffix).exists() for suffix in ("", "-wal", "-shm", "-journal")):
        raise ValueError(f"目标或其 SQLite 附属文件已存在，拒绝覆盖：{destination}")
    with closing(open_readonly(source)) as src:
        check_database(src)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # 排他创建，防止并发调用覆盖目标。失败时保留文件供排查，不自动删除。
        with destination.open("xb"):
            pass
        deadline = time.monotonic() + timeout

        def progress(status: int, remaining: int, total: int) -> None:
            if time.monotonic() > deadline:
                raise TimeoutError("备份等待超时；目标可能不完整，请勿用于恢复")

        with closing(sqlite3.connect(str(destination))) as dst:
            src.backup(dst, pages=256, progress=progress, sleep=0.05)
            # 备份成独立文件，后续拷贝不依赖旁边的 WAL 文件。
            mode = dst.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
            if mode.lower() != "delete":
                raise ValueError("无法生成独立备份文件，请勿用于恢复")
            return check_database(dst)


def verify_restore(source: Path) -> int:
    """在内存中演练恢复，不接触正在使用的数据库。"""
    with closing(open_readonly(source)) as src, closing(sqlite3.connect(":memory:")) as restored:
        check_database(src)
        src.backup(restored)
        return check_database(restored)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup", help="生成新的时间戳备份")
    backup.add_argument("--source", type=Path, default=DEFAULT_DATABASE)
    backup.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    verify = commands.add_parser("verify", help="完整性校验，并在内存演练恢复")
    verify.add_argument("file", type=Path)
    restore = commands.add_parser("restore", help="从备份恢复到新文件，不替换运行中的数据库")
    restore.add_argument("file", type=Path)
    restore.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            name = f"youzi_v2-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}.db"
            output = args.backup_dir / name
            tables = copy_database(args.source, output)
            print(f"备份成功，完整性检查通过（{tables} 张业务表）：\n{output.resolve()}")
        elif args.command == "verify":
            tables = verify_restore(args.file)
            print(f"备份完整性检查及内存恢复通过（{tables} 张业务表），未替换现有数据库")
        else:
            tables = copy_database(args.file, args.output)
            print(f"恢复副本已生成并校验通过（{tables} 张业务表）：\n{args.output.resolve()}")
            print("现有数据库未替换。正式切换前须停止后端及同步脚本，并保留原数据库。")
        return 0
    except (OSError, sqlite3.Error, ValueError, TimeoutError) as exc:
        print(f"操作失败：{exc}\n若已生成目标文件，请视为未完成文件；源数据库不会被覆盖。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
