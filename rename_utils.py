import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


TRACKING_NAME_PATTERN = re.compile(r"^[A-Za-z0-9]{8,}$")


def _parse_rename_data(rename_data_path: Path) -> Dict[str, Any]:
    """
    读取 rename.data 配置，支持两种格式：
    1) 高级 JSON（支持单号规则）:
       {
         "default": {"prefix": "", "suffix": ""},
         "rules": [
           {"match": "DPSECO260425075", "prefix": "A_"},
           {"prefix_match": "DPSECO", "suffix": "_SZ"},
           {"regex": "^AB\\d+$", "prefix": "AB_"}
         ]
       }
    2) 简单文本行: prefix=PRE_ / suffix=_SUF（支持 : 或 =）
    """
    if not rename_data_path.exists():
        raise FileNotFoundError(f"未找到配置文件: {rename_data_path}")

    raw = rename_data_path.read_text(encoding="utf-8").strip()
    if not raw:
        return {"default": {"prefix": "", "suffix": ""}, "rules": []}

    # 先尝试 JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # 高级格式：default + rules
            if "default" in data or "rules" in data:
                default_cfg = data.get("default", {})
                if not isinstance(default_cfg, dict):
                    default_cfg = {}
                rules = data.get("rules", [])
                if not isinstance(rules, list):
                    rules = []
                return {
                    "default": {
                        "prefix": str(default_cfg.get("prefix", "")),
                        "suffix": str(default_cfg.get("suffix", "")),
                    },
                    "rules": rules,
                }

            # 兼容旧 JSON：{"prefix":"", "suffix":""}
            return {
                "default": {
                    "prefix": str(data.get("prefix", "")),
                    "suffix": str(data.get("suffix", "")),
                },
                "rules": [],
            }
    except json.JSONDecodeError:
        pass

    # 再尝试 key=value 文本
    prefix = ""
    suffix = ""
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        key = key.strip().lower()
        value = value.strip()
        if key == "prefix":
            prefix = value
        elif key == "suffix":
            suffix = value

    return {"default": {"prefix": prefix, "suffix": suffix}, "rules": []}


def _resolve_prefix_suffix(stem: str, config: Dict[str, Any]) -> Tuple[str, str]:
    """
    根据单号匹配规则，返回该文件应使用的 prefix/suffix。
    仅使用精确匹配（rule.match == stem）。
    匹配顺序：rules 从上到下，命中第一条即返回；
    若没命中，回落到 default。
    """
    default_cfg = config.get("default", {})
    if not isinstance(default_cfg, dict):
        default_cfg = {}

    default_prefix = str(default_cfg.get("prefix", ""))
    default_suffix = str(default_cfg.get("suffix", ""))

    rules = config.get("rules", [])
    if not isinstance(rules, list):
        return default_prefix, default_suffix

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        matched = False

        exact = rule.get("match")
        if isinstance(exact, str) and exact == stem:
            matched = True

        if matched:
            prefix = str(rule.get("prefix", default_prefix))
            suffix = str(rule.get("suffix", default_suffix))
            return prefix, suffix

    return default_prefix, default_suffix


def _get_pdf_page_count(file_path: Path) -> Optional[int]:
    """
    获取 PDF 页数。优先使用 pypdf，不存在则尝试 PyPDF2。
    读取失败时返回 None，不阻断重命名流程。
    """
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return None

    try:
        reader = PdfReader(str(file_path))
        return len(reader.pages)
    except Exception:
        return None


def batch_rename_tracking_files(
    folder_path: str,
    rename_data_path: str = "rename.data",
    dry_run: bool = False,
) -> List[Dict[str, str]]:
    """
    批量重命名单号命名文件。

    规则：
    - 仅处理文件名主体（不含扩展名）匹配 TRACKING_NAME_PATTERN 的文件
      例如：DPSECO260425075、AB12345678
    - 包括子文件夹（递归处理）
    - 从 rename.data 读取 prefix/suffix
    - PDF 文件在新名称末尾追加页数，例如：PRE_DPSECO260425075_SUF_12P.pdf
    - 避免重名冲突（若冲突则跳过）

    返回：
    [
      {"old": "...", "new": "...", "status": "renamed|skipped|dry_run", "reason": "..."},
      ...
    ]
    """
    folder = Path(folder_path)
    rename_data = Path(rename_data_path)
    config = _parse_rename_data(rename_data)

    if not folder.exists() or not folder.is_dir():
        raise NotADirectoryError(f"目标目录无效: {folder}")

    results: List[Dict[str, str]] = []

    for file_path in folder.rglob("*"):
        if not file_path.is_file():
            continue

        stem = file_path.stem
        suffix_ext = file_path.suffix

        if not TRACKING_NAME_PATTERN.match(stem):
            continue

        prefix, suffix = _resolve_prefix_suffix(stem, config)
        new_stem = f"{prefix}{stem}{suffix}"
        if file_path.suffix.lower() == ".pdf":
            page_count = _get_pdf_page_count(file_path)
            if page_count is not None:
                new_stem = f"{new_stem}_{page_count}P"

        new_name = f"{new_stem}{suffix_ext}"
        new_path = file_path.with_name(new_name)

        if new_path == file_path:
            results.append(
                {
                    "old": str(file_path.name),
                    "new": str(new_name),
                    "status": "skipped",
                    "reason": "文件名未变化",
                }
            )
            continue

        if new_path.exists():
            results.append(
                {
                    "old": str(file_path.name),
                    "new": str(new_name),
                    "status": "skipped",
                    "reason": "目标文件已存在",
                }
            )
            continue

        if dry_run:
            results.append(
                {
                    "old": str(file_path.name),
                    "new": str(new_name),
                    "status": "dry_run",
                    "reason": "",
                }
            )
            continue

        file_path.rename(new_path)
        results.append(
            {
                "old": str(file_path.name),
                "new": str(new_name),
                "status": "renamed",
                "reason": "",
            }
        )

    return results


if __name__ == "__main__":
    # 示例：
    # 1) 简单格式：
    #    prefix=PRE_
    #    suffix=_ARCHIVE
    #
    # 2) 高级格式（不同单号精确匹配）：
    # {
    #   "default": {"prefix": "", "suffix": ""},
    #   "rules": [
    #     {"match": "DPSECO260425075", "prefix": "VIP_"},
    #     {"match": "DPSECO260425076", "suffix": "_CA空运_YYC4_126件"}
    #   ]
    # }
    changed = batch_rename_tracking_files(
        folder_path=r"C:\Users\qianx\Desktop\new",
        rename_data_path=r"C:\Users\qianx\Desktop\youzi\rename.data",
        dry_run=False,
    )
    for item in changed:
        print(item)
