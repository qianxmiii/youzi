"""兼容：内部轨迹表已迁至 internal_tracking_logs。"""

from .internal_tracking_logs_table import TABLE_NAME, ensure_schema

__all__ = ["TABLE_NAME", "ensure_schema"]
