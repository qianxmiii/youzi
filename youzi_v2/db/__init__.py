"""数据库入口：按表拆分模块，初始化时各自建表并写入必要种子数据。"""

from .connection import Database, get_database

__all__ = ["Database", "get_database"]
